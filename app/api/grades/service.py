# Added current_app
from flask import current_app
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from marshmallow import ValidationError

# Import eager loading strategy if needed
from sqlalchemy.orm import joinedload

# Import DB instance and models
from app import db

# Import related models needed for checks and context
# User is the base, Student, Teacher, Parent inherit from it.
from app.models import Note, Student, Module, Teacher, Parent, User

# Import shared utilities
from app.utils import (
    err_resp,
    message,
    internal_err_resp,
    validation_error,
)

# Import serialization/deserialization utilities from local utils.py
from .utils import dump_data, load_data

# Specific Enum for Note's type (cc, exam1, exam2)
try:
    from app.models.Note import NoteType as NoteModelTypeEnum
except ImportError:
    current_app.logger.critical("CRITICAL: app.models.Note.NoteType (for cc, exam1, exam2) not found! Note creation will fail.")
    import enum
    class NoteModelTypeEnum(enum.Enum): # Dummy if missing
        CC = "cc"; EXAM1 = "exam1"; EXAM2 = "exam2"

# Imports for Notifications
try:
    from app.services.notification_trigger_service import NotificationTriggerService
    from app.models import NotificationType as AppNotificationType
except ImportError:
    NotificationTriggerService = None
    AppNotificationType = None
    current_app.logger.warning("NotificationTriggerService or AppNotificationType not found. Note notifications will be skipped.")


class NoteService:

    @staticmethod
    def _validate_foreign_keys(data: dict):
        errors = {}
        student_id_val = data.get("student_id") # This is User.id for the student
        module_id_val = data.get("module_id")   # This is Module.id

        if student_id_val is not None:
            try:
                student_id_int = int(student_id_val)
                # Check if a Student record exists with this ID (which is also User.id)
                student = Student.query.get(student_id_int)
                if not student:
                    errors["student_id"] = f"Student with ID {student_id_int} not found."
                # Student model inherits 'archived' from User
                elif student.archived:
                     errors["student_id"] = f"Student with ID {student_id_int} is archived and cannot receive notes."
            except (ValueError, TypeError):
                errors["student_id"] = f"Invalid student_id format: '{student_id_val}'."
        else:
            errors["student_id"] = "student_id is required." # This ID will be User.id

        if module_id_val is not None:
            try:
                module_id_int = int(module_id_val)
                if not Module.query.get(module_id_int):
                    errors["module_id"] = f"Module with ID {module_id_int} not found."
            except (ValueError, TypeError):
                errors["module_id"] = f"Invalid module_id format: '{module_id_val}'."
        else:
            errors["module_id"] = "module_id is required."
        return errors

    @staticmethod
    def get_note_data(note_id: int, current_user_id: int, current_user_role: str):
        # current_user_id is User.id from JWT
        note = Note.query.options(
            joinedload(Note.student).joinedload(Student.parent),
            joinedload(Note.module),
            joinedload(Note.teacher),
        ).get(note_id)

        if not note:
            return err_resp("Note not found!", "note_404", 404)

        can_access = False
        actor_user_id = int(current_user_id) # User.id from JWT

        if current_user_role == "admin":
            can_access = True
        elif current_user_role == "teacher":
            # Note.teacher_id stores the Teacher's User.id (which is Teacher.id)
            if note.teacher_id == actor_user_id:
                can_access = True
        elif current_user_role == "student":
            # Note.student_id stores the Student's User.id (which is Student.id)
            if note.student_id == actor_user_id:
                can_access = True
        elif current_user_role == "parent":
            # Parent is authorized if their User.id matches the parent of the student in the note
            # Student.parent_id stores the Parent's User.id (which is Parent.id)
            if note.student and note.student.parent_id == actor_user_id:
                can_access = True

        if not can_access:
            return err_resp("Forbidden: You do not have permission to access this note.", "record_access_denied", 403)

        try:
            note_data = dump_data(note)
            if note.student: # Student object inherits first_name, last_name from User
                note_data["student_name"] = f"{note.student.first_name or ''} {note.student.last_name or ''}".strip()
            if note.module:
                note_data["module_name"] = note.module.name
            if note.teacher: # Teacher object inherits first_name, last_name from User
                note_data["teacher_name"] = f"{note.teacher.first_name or ''} {note.teacher.last_name or ''}".strip()
            resp = message(True, "Note data sent successfully.")
            resp["note"] = note_data
            return resp, 200
        except Exception as e:
            current_app.logger.error(f"Error serializing note {note_id} for get_note_data: {e}", exc_info=True)
            return internal_err_resp()

    @staticmethod
    def get_all_notes(
        student_id=None, module_id=None, teacher_id=None, group_id=None,
        type=None, page=None, per_page=None,
        current_user_id=None, current_user_role=None,
    ):
        page = page or 1
        per_page = per_page or 10
        actor_user_id = int(current_user_id) # This is User.id

        try:
            query = Note.query.options(
                joinedload(Note.student).joinedload(Student.parent), # Student.parent_id -> Parent.id (which is User.id)
                joinedload(Note.module),
                joinedload(Note.teacher), # Note.teacher_id -> Teacher.id (which is User.id)
            )

            if current_user_role == "student":
                # Student sees their own notes. Note.student_id is their User.id.
                query = query.filter(Note.student_id == actor_user_id)
            elif current_user_role == "parent":
                # Parent sees notes of their children.
                # We need to find students whose parent_id (which is User.id of parent) matches actor_user_id.
                # This requires joining Student with Note.
                parent_children_query = db.session.query(Student.id).filter(Student.parent_id == actor_user_id)
                if hasattr(Student, 'archived'): # Check if Student has archived before filtering
                    parent_children_query = parent_children_query.filter(Student.archived == False)

                child_student_ids = [s_id[0] for s_id in parent_children_query.all()]

                if not child_student_ids:
                    return message(True, "No active students for parent.") | {"notes": [], "total": 0, "pages": page, "per_page": per_page}, 200
                query = query.filter(Note.student_id.in_(child_student_ids))

                if student_id is not None and int(student_id) not in child_student_ids:
                    return err_resp("Forbidden: Can only filter by own children.", "parent_filter_denied", 403)

            elif current_user_role == "teacher":
                # Teacher sees notes they created. Note.teacher_id is their User.id.
                query = query.filter(Note.teacher_id == actor_user_id)

            # Standard filters
            if student_id is not None: # student_id here is a User.id for a student
                if current_user_role not in ['parent', 'student']: # Avoid re-filtering if already scoped
                     query = query.filter(Note.student_id == int(student_id))
            if module_id is not None:
                query = query.filter(Note.module_id == int(module_id))
            if teacher_id is not None and current_user_role == "admin": # teacher_id here is User.id for a teacher
                query = query.filter(Note.teacher_id == int(teacher_id))
            if group_id is not None: # Assuming Student.group_id exists
                query = query.join(Note.student).filter(Student.group_id == int(group_id))
            if type is not None:
                try:
                    note_type_enum_val = NoteModelTypeEnum(str(type).lower())
                    query = query.filter(Note.type == note_type_enum_val)
                except ValueError:
                    valid_types = [e.value for e in NoteModelTypeEnum]
                    return err_resp(f"Invalid note type filter '{type}'. Must be one of: {valid_types}.", "invalid_note_type_filter", 400)

            query = query.order_by(Note.created_at.desc())
            paginated_notes = query.paginate(page=page, per_page=per_page, error_out=False)

            notes_list_data = []
            for note_obj in paginated_notes.items:
                item_data = dump_data(note_obj)
                if note_obj.student: # Student object has first_name, last_name
                    item_data["student_name"] = f"{note_obj.student.first_name or ''} {note_obj.student.last_name or ''}".strip()
                if note_obj.module:
                    item_data["module_name"] = note_obj.module.name
                if note_obj.teacher: # Teacher object has first_name, last_name
                    item_data["teacher_name"] = f"{note_obj.teacher.first_name or ''} {note_obj.teacher.last_name or ''}".strip()
                notes_list_data.append(item_data)

            resp = message(True, "Notes list retrieved successfully")
            resp.update({
                "notes": notes_list_data, "total": paginated_notes.total, "pages": paginated_notes.pages,
                "current_page": paginated_notes.page, "per_page": paginated_notes.per_page,
                "has_next": paginated_notes.has_next, "has_prev": paginated_notes.has_prev
            })
            return resp, 200
        except Exception as error:
            current_app.logger.error(f"Error getting notes list (role: {current_user_role}, user: {current_user_id}): {error}", exc_info=True)
            return internal_err_resp()

    @staticmethod
    def create_note(data: dict, current_user_id: int, current_user_role: str):
        # current_user_id is User.id from JWT
        try:
            current_app.logger.info(f"--- Attempting to create note by User {current_user_id} (Role: {current_user_role}) ---")
            current_app.logger.info(f"Raw input data: {data}")

            fk_errors = NoteService._validate_foreign_keys(data)
            if fk_errors: return validation_error(False, fk_errors), 400

            actor_user_id = int(current_user_id)
            teacher_id_for_note = None # This will be User.id of the teacher

            if current_user_role == "teacher":
                # Check if the current user (User.id) exists as a Teacher
                if not Teacher.query.get(actor_user_id):
                    return err_resp(f"Teacher profile not found for current user (ID: {actor_user_id}).", "teacher_profile_missing_for_create", 403)
                teacher_id_for_note = actor_user_id
            elif current_user_role == "admin":
                # Admin creating a note. Check if the admin's User.id also corresponds to a Teacher record.
                if not Teacher.query.get(actor_user_id):
                    return err_resp("Admin user must also have a Teacher profile to create notes.", "admin_not_teacher_for_create", 400)
                teacher_id_for_note = actor_user_id

            if teacher_id_for_note is None:
                return internal_err_resp(message="Could not assign a teacher to the note based on user role.")

            raw_grade_value = data.get("value")
            if raw_grade_value is None: return err_resp("Grade 'value' is required.", "missing_grade_value", 400)
            try: grade_value_float = float(raw_grade_value)
            except ValueError: return err_resp("Grade 'value' must be a valid number.", "invalid_grade_value_format", 400)
            MIN_GRADE, MAX_GRADE = 0.0, 20.0
            if not (MIN_GRADE <= grade_value_float <= MAX_GRADE):
                return err_resp(f"Grade value must be between {MIN_GRADE} and {MAX_GRADE}.", "invalid_grade_range", 400)

            raw_note_type_input = data.get("type")
            if not raw_note_type_input: return err_resp("Note 'type' is required.", "missing_note_type", 400)
            try: note_type_enum_for_db = NoteModelTypeEnum(str(raw_note_type_input).lower())
            except ValueError:
                valid_types = [e.value for e in NoteModelTypeEnum]
                return err_resp(f"Invalid note type '{raw_note_type_input}'. Must be one of: {valid_types}.", "invalid_note_type_value", 400)

            student_id_for_check = int(data["student_id"]) # This is User.id of student
            module_id_for_check = int(data["module_id"])   # This is Module.id

            current_app.logger.info(f"DUPLICATE CHECK PARAMS: student_id={student_id_for_check}, module_id={module_id_for_check}, type={repr(note_type_enum_for_db)}")
            existing_note = Note.query.filter(
                Note.student_id == student_id_for_check,
                Note.module_id == module_id_for_check,
                Note.type == note_type_enum_for_db
            ).first()

            if existing_note:
                current_app.logger.warning(f"DUPLICATE NOTE FOUND: ID={existing_note.id} for input.")
                return err_resp(f"A '{raw_note_type_input}' note already exists for this student in this module.", "duplicate_note_type", 409)
            current_app.logger.info("DUPLICATE CHECK: No existing note found.")

            new_note = Note(
                student_id=student_id_for_check, # Storing User.id of student
                module_id=module_id_for_check,
                teacher_id=teacher_id_for_note,  # Storing User.id of teacher
                value=grade_value_float,
                type=note_type_enum_for_db,
                comment=data.get("comment"),
            )
            db.session.add(new_note)
            db.session.commit()
            current_app.logger.info(f"Note created: ID={new_note.id}, Student={new_note.student_id}, Module={new_note.module_id}, Type='{new_note.type.value}'")

            if NotificationTriggerService and AppNotificationType:
                try:
                    student_obj = Student.query.get(new_note.student_id) # Student.id is User.id
                    module_obj = Module.query.get(new_note.module_id)
                    if student_obj and module_obj:
                        student_name_for_msg = f"{student_obj.first_name or ''} {student_obj.last_name or ''}".strip() or "the student"

                        student_notify_recipient_id = student_obj.id # Student's User.id

                        student_message = f"You received a new grade of {new_note.value} ({new_note.type.value}) in {module_obj.name}."
                        NotificationTriggerService.trigger_notification(
                            recipient_type="student", recipient_id=student_notify_recipient_id,
                            message=student_message, notification_type_value=(AppNotificationType.GRADE.value if hasattr(AppNotificationType, "GRADE") else "grade"),
                            link=f"/grades/student/{student_obj.id}" # Link to student's grades page
                        )

                        if student_obj.parent_id: # parent_id on Student is Parent's User.id
                            parent_obj = Parent.query.get(student_obj.parent_id) # Parent.id is User.id
                            if parent_obj and not parent_obj.archived:
                                parent_notify_recipient_id = parent_obj.id # Parent's User.id

                                parent_message = f"Your child, {student_name_for_msg}, received a new grade of {new_note.value} ({new_note.type.value}) in {module_obj.name}."
                                NotificationTriggerService.trigger_notification(
                                    recipient_type="parent", recipient_id=parent_notify_recipient_id,
                                    message=parent_message, notification_type_value=(AppNotificationType.GRADE.value if hasattr(AppNotificationType, "GRADE") else "grade"),
                                    link=f"/grades/student/{student_obj.id}"
                                )
                except Exception as e_notif:
                    current_app.logger.error(f"Error during notification for note {new_note.id}: {e_notif}", exc_info=True)

            note_resp_data = dump_data(new_note)
            student_for_resp = Student.query.get(new_note.student_id)
            module_for_resp = Module.query.get(new_note.module_id)
            teacher_for_resp = Teacher.query.get(new_note.teacher_id)
            if student_for_resp: note_resp_data["student_name"] = f"{student_for_resp.first_name or ''} {student_for_resp.last_name or ''}".strip()
            if module_for_resp: note_resp_data["module_name"] = module_for_resp.name
            if teacher_for_resp: note_resp_data["teacher_name"] = f"{teacher_for_resp.first_name or ''} {teacher_for_resp.last_name or ''}".strip()

            resp = message(True, "Note created successfully.")
            resp["note"] = note_resp_data
            return resp, 201

        except ValidationError as err:
            db.session.rollback(); return validation_error(False, err.messages), 400
        except IntegrityError as error:
            db.session.rollback(); current_app.logger.error(f"DB Integrity error creating note: {error}", exc_info=True)
            return internal_err_resp(message="Database integrity error. This note might already exist (unique constraint).")
        except Exception as error:
            db.session.rollback(); current_app.logger.error(f"Unexpected error creating note: {error}", exc_info=True)
            return internal_err_resp()

    @staticmethod
    def update_note(note_id: int, data: dict, current_user_id: int, current_user_role: str):
        # current_user_id is User.id
        note = Note.query.get(note_id)
        if not note: return err_resp("Note not found!", "note_404", 404)

        actor_user_id = int(current_user_id)
        can_update = False
        if current_user_role == "admin":
            can_update = True
        elif current_user_role == "teacher":
            # Note.teacher_id is User.id of the teacher who created the note
            if note.teacher_id == actor_user_id:
                can_update = True

        if not can_update: return err_resp("Forbidden: You cannot update this note.", "update_forbidden", 403)
        if not data: return err_resp("Request body cannot be empty for update.", "empty_update_data", 400)

        try:
            updated_any_field = False
            if "value" in data:
                raw_val = data["value"]
                if raw_val is None: return err_resp("Grade 'value' cannot be null.", "null_update_val", 400)
                try: val_float = float(raw_val)
                except ValueError: return err_resp("Grade 'value' not a valid number.", "invalid_update_val_fmt", 400)
                MIN_G, MAX_G = 0.0, 20.0
                if not (MIN_G <= val_float <= MAX_G): return err_resp(f"Grade must be {MIN_G}-{MAX_G}.", "invalid_update_val_rng", 400)
                note.value = val_float
                updated_any_field = True

            if "type" in data:
                raw_type = data.get("type")
                if not raw_type: return err_resp("Note 'type' cannot be null.", "null_update_type", 400)
                try: type_enum = NoteModelTypeEnum(str(raw_type).lower())
                except ValueError: return err_resp(f"Invalid note type '{raw_type}'.", "invalid_update_type_val", 400)

                if note.type != type_enum:
                    existing_check = Note.query.filter(
                        Note.student_id == note.student_id, Note.module_id == note.module_id,
                        Note.type == type_enum, Note.id != note_id
                    ).first()
                    if existing_check: return err_resp(f"A '{raw_type}' note already exists.", "dup_note_type_update", 409)
                note.type = type_enum
                updated_any_field = True

            if "comment" in data:
                note.comment = data.get("comment")
                updated_any_field = True

            if not updated_any_field: return err_resp("No valid fields to update.", "no_fields_to_update", 400)

            db.session.commit()
            note_resp_data = dump_data(note)
            s = Student.query.get(note.student_id); m = Module.query.get(note.module_id); t = Teacher.query.get(note.teacher_id)
            if s: note_resp_data["student_name"] = f"{s.first_name or ''} {s.last_name or ''}".strip()
            if m: note_resp_data["module_name"] = m.name
            if t: note_resp_data["teacher_name"] = f"{t.first_name or ''} {t.last_name or ''}".strip()

            resp = message(True, "Note updated successfully.")
            resp["note"] = note_resp_data
            return resp, 200
        except Exception as e:
            db.session.rollback(); current_app.logger.error(f"Error updating note {note_id}: {e}", exc_info=True)
            return internal_err_resp()

    @staticmethod
    def delete_note(note_id: int, current_user_id: int, current_user_role: str):
        # current_user_id is User.id
        note = Note.query.get(note_id)
        if not note: return err_resp("Note not found!", "note_404", 404)

        actor_user_id = int(current_user_id)
        can_delete = False
        if current_user_role == "admin":
            can_delete = True
        elif current_user_role == "teacher":
            # Note.teacher_id is User.id of the teacher
            if note.teacher_id == actor_user_id:
                can_delete = True

        if not can_delete: return err_resp("Forbidden: You cannot delete this note.", "delete_forbidden", 403)

        try:
            db.session.delete(note)
            db.session.commit()
            return None, 204
        except IntegrityError:
            db.session.rollback()
            current_app.logger.warning(f"Attempt to delete note {note_id} failed due to FK constraint.")
            return err_resp("Cannot delete this note as it might be referenced elsewhere.", "delete_conflict_note_fk", 409)
        except Exception as e:
            db.session.rollback(); current_app.logger.error(f"Error deleting note {note_id}: {e}", exc_info=True)
            return internal_err_resp()

