from flask import current_app
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from marshmallow import ValidationError
from sqlalchemy.orm import joinedload

from app import db
from app.models import Note, Student, Module, Teacher, Parent
# Import the NotificationTriggerService and NotificationType Enum
from app.services.notification_trigger_service import NotificationTriggerService
try:
    from app.models import NotificationType # Your Enum for notification types
except ImportError:
    NotificationType = None
    current_app.logger.warning("NotificationType enum not found. Notification types will be strings.")


from app.utils import (
    err_resp,
    message,
    internal_err_resp,
    validation_error,
)
from .utils import dump_data, load_data


class NoteService:

    @staticmethod
    def _validate_foreign_keys(data: dict):
        errors = {}
        student_id_val = data.get("student_id")
        if student_id_val is not None:
            student = Student.query.get(student_id_val)
            if not student:
                errors["student_id"] = f"Student with ID {student_id_val} not found."
            elif student.archived: # Prevent notes for archived students
                 errors["student_id"] = f"Student with ID {student_id_val} is archived and cannot receive notes."

        if data.get("module_id") is not None:
            if not Module.query.get(data["module_id"]):
                errors["module_id"] = f"Module with ID {data['module_id']} not found."
        return errors

    @staticmethod
    def get_note_data(note_id: int, current_user_id: int, current_user_role: str):
        note = Note.query.options(
            joinedload(Note.student).joinedload(Student.parent),
            joinedload(Note.module),
            joinedload(Note.teacher).joinedload(Teacher.user) # Assuming teacher name is on User model
        ).get(note_id)

        if not note:
            return err_resp("Note not found!", "note_404", 404)

        can_access = False
        if current_user_role == "admin": can_access = True
        elif current_user_role == "teacher" and note.teacher_id == int(current_user_id): can_access = True
        elif current_user_role == "student" and note.student_id == int(current_user_id): can_access = True
        elif current_user_role == "parent" and note.student and note.student.parent_id == int(current_user_id): can_access = True

        if not can_access:
            return err_resp("Forbidden: You do not have permission to access this note.", "record_access_denied", 403)

        try:
            note_data = dump_data(note)
            if note.student:
                student_user = getattr(note.student, 'user', None) # Assuming Student has a 'user' relationship for name parts
                first_name = getattr(student_user or note.student, 'first_name', '')
                last_name = getattr(student_user or note.student, 'last_name', '')
                note_data["student_name"] = f"{first_name} {last_name}".strip()
            if note.module:
                note_data["module_name"] = note.module.name
            if note.teacher and hasattr(note.teacher, 'user') and note.teacher.user: # Check if teacher.user exists
                note_data["teacher_name"] = f"{note.teacher.user.first_name} {note.teacher.user.last_name}".strip()
            elif note.teacher: # Fallback if teacher name parts are directly on Teacher model
                 note_data["teacher_name"] = f"{note.teacher.first_name} {note.teacher.last_name}".strip()


            resp = message(True, "Note data sent successfully")
            resp["note"] = note_data
            return resp, 200
        except Exception as error:
            current_app.logger.error(f"Error serializing note data for ID {note_id}: {error}", exc_info=True)
            return internal_err_resp()

    @staticmethod
    def get_all_notes(
        student_id=None, module_id=None, teacher_id=None, group_id=None,
        type=None, # 'type' is the filter key from DTO
        page=None, per_page=None,
        current_user_id=None, current_user_role=None,
    ):
        page = page or 1
        per_page = per_page or 10
        try:
            query = Note.query.options(
                joinedload(Note.student).joinedload(Student.parent),
                joinedload(Note.module),
                joinedload(Note.teacher).joinedload(Teacher.user) # Assuming teacher name is on User model
            )

            if current_user_role == "student":
                query = query.filter(Note.student_id == int(current_user_id))
            elif current_user_role == "parent":
                parent = Parent.query.get(current_user_id)
                if not parent: return message(True, "Parent profile not found.") | {"notes": [], "total": 0, "pages": 0, "current_page": page, "per_page": per_page, "has_next": False, "has_prev": False}, 200
                child_ids = [s.id for s in parent.students if not s.archived]
                if not child_ids: return message(True, "No active students for parent.") | {"notes": [], "total": 0, "pages": 0, "current_page": page, "per_page": per_page, "has_next": False, "has_prev": False}, 200
                if student_id is not None and int(student_id) not in child_ids:
                    return err_resp("Forbidden: Can only filter by your own active children.", "parent_filter_denied", 403)
                query = query.filter(Note.student_id.in_(child_ids))
                if student_id is not None: query = query.filter(Note.student_id == int(student_id))

            elif current_user_role == "teacher":
                query = query.filter(Note.teacher_id == int(current_user_id))

            # Standard filters (apply if not overridden by role logic or if admin)
            if student_id is not None and current_user_role not in ["student", "parent"]: # Parent handled above
                query = query.filter(Note.student_id == student_id)
            if module_id is not None:
                query = query.filter(Note.module_id == module_id)
            if teacher_id is not None and current_user_role == "admin": # Only admin can use teacher_id filter freely
                query = query.filter(Note.teacher_id == teacher_id)
            if group_id is not None: # Ensure student is loaded for this join
                query = query.join(Note.student).filter(Student.group_id == group_id)

            if type is not None: # 'type' is the filter key from DTO
                try:
                    from app.models.Note import NoteType as NoteModelTypeEnum # Specific import for enum
                    note_type_enum_val = NoteModelTypeEnum(type.lower())
                    query = query.filter(Note.type == note_type_enum_val)
                except ValueError:
                    return err_resp("Invalid note type filter. Must be one of: cc, exam1, exam2.", "invalid_note_type_filter", 400)
                except ImportError:
                     current_app.logger.warning("NoteType enum for filtering not found in app.models.Note.")


            query = query.order_by(Note.created_at.desc())
            paginated_notes = query.paginate(page=page, per_page=per_page, error_out=False)

            notes_list_data = []
            for note_obj in paginated_notes.items:
                item_data = dump_data(note_obj)
                if note_obj.student:
                    student_user = getattr(note_obj.student, 'user', None)
                    first_name = getattr(student_user or note_obj.student, 'first_name', '')
                    last_name = getattr(student_user or note_obj.student, 'last_name', '')
                    item_data["student_name"] = f"{first_name} {last_name}".strip()
                if note_obj.module:
                    item_data["module_name"] = note_obj.module.name
                if note_obj.teacher and hasattr(note_obj.teacher, 'user') and note_obj.teacher.user:
                    item_data["teacher_name"] = f"{note_obj.teacher.user.first_name} {note_obj.teacher.user.last_name}".strip()
                elif note_obj.teacher:
                     item_data["teacher_name"] = f"{note_obj.teacher.first_name} {note_obj.teacher.last_name}".strip()
                notes_list_data.append(item_data)

            resp = message(True, "Notes list retrieved successfully")
            resp.update({
                "notes": notes_list_data, "total": paginated_notes.total, "pages": paginated_notes.pages,
                "current_page": paginated_notes.page, "per_page": paginated_notes.per_page,
                "has_next": paginated_notes.has_next, "has_prev": paginated_notes.has_prev
            })
            return resp, 200
        except Exception as error:
            current_app.logger.error(f"Error getting notes list (role: {current_user_role}): {error}", exc_info=True)
            return internal_err_resp()

    @staticmethod
    def create_note(data: dict, current_user_id: int, current_user_role: str):
        try:
            fk_errors = NoteService._validate_foreign_keys(data)
            if fk_errors:
                return validation_error(False, fk_errors), 400

            teacher_id_to_assign = None
            if current_user_role == "teacher":
                teacher_id_to_assign = current_user_id
            elif current_user_role == "admin": # Admin creating a note needs to be a teacher
                admin_as_teacher = Teacher.query.get(current_user_id)
                if not admin_as_teacher:
                    return err_resp("Admin creating note must also have a Teacher profile.", "admin_not_teacher_for_note", 403)
                teacher_id_to_assign = current_user_id

            if teacher_id_to_assign is None:
                 return err_resp("Could not determine teacher for note.", "teacher_determination_failed", 500)


            grade_value = data["value"]
            MIN_GRADE, MAX_GRADE = 0, 20 # Define or get from config
            if not (MIN_GRADE <= grade_value <= MAX_GRADE):
                return err_resp(f"Invalid grade value. Must be between {MIN_GRADE} and {MAX_GRADE}.", "invalid_grade_value", 400)

            try:
                from app.models.Note import NoteType as NoteModelTypeEnum # Specific import
                note_type_enum_val = NoteModelTypeEnum(data["type"].lower())
            except ValueError:
                return err_resp("Invalid note type. Must be one of: cc, exam1, exam2.", "invalid_note_type_create", 400)
            except ImportError:
                current_app.logger.error("NoteType enum for creation not found in app.models.Note.")
                return internal_err_resp(message="Server configuration error for note types.")


            # Check for existing note (student_id, module_id, type)
            existing_note = Note.query.filter_by(
                student_id=data["student_id"],
                module_id=data["module_id"],
                type=note_type_enum_val # Use the enum value for query
            ).first()
            if existing_note:
                return err_resp(f"A '{data['type']}' note already exists for this student in this module.", "duplicate_note_type", 409)


            new_note = Note(
                student_id=data["student_id"],
                module_id=data["module_id"],
                teacher_id=teacher_id_to_assign,
                value=grade_value,
                type=note_type_enum_val, # Store the enum member
                comment=data.get("comment")
            )

            db.session.add(new_note)
            db.session.commit()
            current_app.logger.info(f"Note (ID: {new_note.id}) created by {current_user_role} {current_user_id}")

            # --- Trigger Notifications ---
            student_obj = Student.query.options(joinedload(Student.user), joinedload(Student.parent)).get(new_note.student_id)
            module_obj = Module.query.get(new_note.module_id)

            if student_obj and module_obj:
                student_name = f"{getattr(student_obj.user, 'first_name', '')} {getattr(student_obj.user, 'last_name', '')}".strip() or "the student"
                module_name_str = module_obj.name
                note_value_str = str(new_note.value)
                note_type_str = new_note.type.value # Get string value from enum

                common_link = f"/grades/student/{student_obj.id}" # Example link

                # Notification for Student
                student_message = f"You received a new grade of {note_value_str} ({note_type_str}) in {module_name_str}."
                NotificationTriggerService.trigger_notification(
                    recipient_type="student",
                    recipient_id=student_obj.id, # student_obj.id is the student's own primary key
                    message=student_message,
                    notification_type_value=NotificationType.GRADE.value if NotificationType else "grade",
                    link=common_link
                )

                # Notification for Parent (if exists and not archived)
                if student_obj.parent and not student_obj.parent.archived:
                    parent_message = f"Your child, {student_name}, received a new grade of {note_value_str} ({note_type_str}) in {module_name_str}."
                    NotificationTriggerService.trigger_notification(
                        recipient_type="parent",
                        recipient_id=student_obj.parent_id,
                        message=parent_message,
                        notification_type_value=NotificationType.GRADE.value if NotificationType else "grade",
                        link=common_link # Or a parent-specific link
                    )
            # --- End Trigger Notifications ---

            # For the API response, reload the note with all necessary joins for consistent output
            # This is important if the schema methods rely on these relationships.
            db.session.refresh(new_note) # Refresh to ensure all attributes are up-to-date
            # Or, query again with all joins if schema needs them:
            response_note = Note.query.options(
                joinedload(Note.student).joinedload(Student.user),
                joinedload(Note.student).joinedload(Student.parent),
                joinedload(Note.module),
                joinedload(Note.teacher).joinedload(Teacher.user)
            ).get(new_note.id)

            note_resp_data = dump_data(response_note if response_note else new_note)
            # Manually add names if schema doesn't do it or if joins weren't perfect for dump_data context
            if response_note:
                if response_note.student:
                    s_user = getattr(response_note.student, 'user', None)
                    s_fn = getattr(s_user or response_note.student, 'first_name', '')
                    s_ln = getattr(s_user or response_note.student, 'last_name', '')
                    note_resp_data["student_name"] = f"{s_fn} {s_ln}".strip()
                if response_note.module:
                    note_resp_data["module_name"] = response_note.module.name
                if response_note.teacher and hasattr(response_note.teacher, 'user') and response_note.teacher.user:
                    note_resp_data["teacher_name"] = f"{response_note.teacher.user.first_name} {response_note.teacher.user.last_name}".strip()
                elif response_note.teacher:
                     note_resp_data["teacher_name"] = f"{response_note.teacher.first_name} {response_note.teacher.last_name}".strip()


            resp = message(True, "Note created successfully.")
            resp["note"] = note_resp_data
            return resp, 201

        except ValidationError as err:
            db.session.rollback(); return validation_error(False, err.messages), 400
        except IntegrityError as e:
            db.session.rollback()
            # Check if it's the unique constraint for (student_id, module_id, type)
            # The name of this constraint depends on how it was defined in your Note model.
            # Example: if 'uq_student_module_type' in str(e.orig):
            #    return err_resp(f"A '{data.get('type')}' note already exists for this student in this module.", "duplicate_note_type", 409)
            current_app.logger.error(f"Integrity error creating note: {e}", exc_info=True)
            return internal_err_resp(message="Database integrity error (e.g. duplicate note).")
        except Exception as error:
            db.session.rollback(); current_app.logger.error(f"Unexpected error creating note: {error}", exc_info=True)
            return internal_err_resp()

    @staticmethod
    def update_note(note_id: int, data: dict, current_user_id: int, current_user_role: str):
        note = Note.query.get(note_id)
        if not note:
            return err_resp("Note not found!", "note_404_update", 404)

        can_update = (current_user_role == "admin") or \
                     (current_user_role == "teacher" and note.teacher_id == int(current_user_id))
        if not can_update:
            return err_resp("Forbidden: You cannot update this note.", "update_note_forbidden", 403)
        if not data:
            return err_resp("Request body cannot be empty for update.", "empty_update_data_note", 400)

        try:
            from app.models.Note import NoteType as NoteModelTypeEnum # Specific import

            updated_any_field = False
            if "value" in data:
                grade_value = data["value"]
                MIN_GRADE, MAX_GRADE = 0, 20
                if not (MIN_GRADE <= grade_value <= MAX_GRADE):
                    return err_resp(f"Invalid grade value. Must be between {MIN_GRADE} and {MAX_GRADE}.", "invalid_grade_value_update", 400)
                note.value = grade_value
                updated_any_field = True

            if "type" in data:
                try:
                    note_type_enum_val = NoteModelTypeEnum(data["type"].lower())
                    # Check for duplicate if type is changing
                    if note.type != note_type_enum_val:
                        existing_note = Note.query.filter(
                            Note.student_id == note.student_id,
                            Note.module_id == note.module_id,
                            Note.type == note_type_enum_val,
                            Note.id != note_id # Exclude self
                        ).first()
                        if existing_note:
                            return err_resp(f"A '{data['type']}' note already exists for this student in this module.", "duplicate_note_type_update", 409)
                    note.type = note_type_enum_val
                    updated_any_field = True
                except ValueError:
                    return err_resp("Invalid note type. Must be one of: cc, exam1, exam2.", "invalid_note_type_update", 400)
                except ImportError:
                     current_app.logger.error("NoteType enum for update not found in app.models.Note.")
                     return internal_err_resp(message="Server configuration error for note types.")


            if "comment" in data:
                note.comment = data.get("comment") # Allow setting comment to None or empty
                updated_any_field = True

            if not updated_any_field:
                 return err_resp("No valid fields (value, type, comment) provided for update.", "no_fields_to_update_note", 400)


            db.session.add(note) # or just db.session.commit() if changes are tracked
            db.session.commit()

            # For the API response, reload or ensure joins for consistent output
            response_note = Note.query.options(
                joinedload(Note.student).joinedload(Student.user),
                joinedload(Note.student).joinedload(Student.parent),
                joinedload(Note.module),
                joinedload(Note.teacher).joinedload(Teacher.user)
            ).get(note.id)

            note_resp_data = dump_data(response_note if response_note else note)
            if response_note:
                if response_note.student:
                    s_user = getattr(response_note.student, 'user', None)
                    s_fn = getattr(s_user or response_note.student, 'first_name', '')
                    s_ln = getattr(s_user or response_note.student, 'last_name', '')
                    note_resp_data["student_name"] = f"{s_fn} {s_ln}".strip()
                if response_note.module:
                    note_resp_data["module_name"] = response_note.module.name
                if response_note.teacher and hasattr(response_note.teacher, 'user') and response_note.teacher.user:
                    note_resp_data["teacher_name"] = f"{response_note.teacher.user.first_name} {response_note.teacher.user.last_name}".strip()
                elif response_note.teacher:
                     note_resp_data["teacher_name"] = f"{response_note.teacher.first_name} {response_note.teacher.last_name}".strip()

            resp = message(True, "Note updated successfully.")
            resp["note"] = note_resp_data
            return resp, 200
        except Exception as error:
            db.session.rollback()
            current_app.logger.error(f"Error updating note {note_id}: {error}", exc_info=True)
            return internal_err_resp()

    @staticmethod
    def delete_note(note_id: int, current_user_id: int, current_user_role: str):
        note = Note.query.get(note_id)
        if not note:
            return err_resp("Note not found!", "note_404_delete", 404)

        can_delete = (current_user_role == "admin") or \
                     (current_user_role == "teacher" and note.teacher_id == int(current_user_id))
        if not can_delete:
            return err_resp("Forbidden: You cannot delete this note.", "delete_note_forbidden", 403)
        try:
            db.session.delete(note)
            db.session.commit()
            return None, 204
        except Exception as error:
            db.session.rollback()
            current_app.logger.error(f"Error deleting note {note_id}: {error}", exc_info=True)
            return internal_err_resp()

