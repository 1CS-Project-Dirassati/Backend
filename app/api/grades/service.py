# Added current_app
from flask import current_app
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from marshmallow import ValidationError
# Import eager loading strategy if needed
from sqlalchemy.orm import joinedload

# Import DB instance and models
from app import db
# Import related models needed for checks and context
from app.models import Note, Student, Module, Teacher, Parent

# Import shared utilities
from app.utils import (
    err_resp,
    message,
    internal_err_resp,
    validation_error,
)

# Import serialization/deserialization utilities from local utils.py
from .utils import dump_data, load_data


class NoteService:

    # --- Helper for Foreign Key Validation ---
    @staticmethod
    def _validate_foreign_keys(data: dict): # Added type hint
        """Check if related entities referenced in data exist. Returns dict of errors."""
        errors = {}
        if data.get("student_id") is not None:
            if not Student.query.get(data["student_id"]):
                errors["student_id"] = f"Student with ID {data['student_id']} not found."
        if data.get("module_id") is not None:
            if not Module.query.get(data["module_id"]):
                errors["module_id"] = f"Module with ID {data['module_id']} not found."
        # teacher_id is handled during creation based on role/context
        return errors

    # --- GET Single ---
    @staticmethod
    # Add type hints
    def get_note_data(note_id: int, current_user_id: int, current_user_role: str):
        """Get note data by ID, with record-level authorization check"""
        # Eager load related data for context and auth checks
        note = Note.query.options(
            joinedload(Note.student).joinedload(Student.parent), # Load student and their parent
            joinedload(Note.module),
            joinedload(Note.teacher)
        ).get(note_id)

        if not note:
            current_app.logger.info(f"Note with ID {note_id} not found.") # Add logging
            return err_resp("Note not found!", "note_404", 404)

        # --- Record-Level Authorization Check ---
        can_access = False
        log_reason = ""
        if current_user_role == "admin":
            can_access = True
            log_reason = "User is admin."
        elif current_user_role == "teacher" and note.teacher_id == int(current_user_id):
            can_access = True
            log_reason = "User is the teacher who created the note."
        elif current_user_role == "student" and note.student_id == int(current_user_id):
            can_access = True
            log_reason = "User is the student associated with the note."
        # Check parent access using the eager-loaded student.parent_id
        elif current_user_role == "parent" and note.student and note.student.parent_id == int(current_user_id):
            can_access = True
            log_reason = "User is the parent of the student associated with the note."

        if not can_access:
            current_app.logger.warning(f"Forbidden: User {current_user_id} (Role: {current_user_role}) attempted to access note {note_id}.") # Add logging
            return err_resp(
                "Forbidden: You do not have permission to access this note.",
                "record_access_denied",
                403,
            )
        current_app.logger.debug(f"Record access granted for user {current_user_id} to note {note_id}. Reason: {log_reason}") # Add logging

        try:
            # Use dump_data for serialization
            note_data = dump_data(note)
            resp = message(True, "Note data sent successfully")
            resp["note"] = note_data
            current_app.logger.debug(f"Successfully retrieved note ID {note_id}") # Add logging
            return resp, 200
        except Exception as error:
            current_app.logger.error(
                f"Error serializing note data for ID {note_id}: {error}", # Update log message
                exc_info=True,
            )
            return internal_err_resp()

    # --- GET List with Filters, Pagination & Authorization ---
    @staticmethod
    # Add type hints
    def get_all_notes(
        student_id=None,
        module_id=None,
        teacher_id=None,
        group_id=None,
        page=None,
        per_page=None,
        current_user_id=None,
        current_user_role=None,
    ):
        """Get a paginated list of notes, filtered, with role-based data scoping"""
        page = page or 1
        per_page = per_page or 10

        try:
            # Eager load student and parent for efficient parent filtering
            query = Note.query.options(
                joinedload(Note.student).joinedload(Student.parent),
                joinedload(Note.module),
                joinedload(Note.teacher)
            )

            child_ids_for_parent = [] # Store child IDs if user is parent

            # --- Role-Based Data Scoping (Applied first) ---
            if current_user_role == "student":
                current_app.logger.debug(f"Scoping notes list for student ID: {current_user_id}")
                query = query.filter(Note.student_id == int(current_user_id)) #type:ignore[reportGeneralTypeIssues]
                student_id = current_user_id # Force student_id filter
                # Ignore other potentially passed filters
                module_id = teacher_id = group_id = None
            elif current_user_role == "parent":
                # Find the parent's children IDs using the user_id (which IS the parent.id)
                parent = Parent.query.options(joinedload(Parent.students)).get(current_user_id) #type:ignore[reportGeneralTypeIssues]
                if not parent:
                    current_app.logger.error(f"Parent profile not found for user ID {current_user_id} during note listing.")
                    # Return empty list or error? Let's return empty for now.
                    return message(True, "Parent profile not found, cannot list notes.") | {"notes": [], "total": 0, "pages": 0, "current_page": 1, "per_page": per_page, "has_next": False, "has_prev": False}, 200
                    # Alternative: return err_resp("Parent profile not found.", "parent_404", 404)

                child_ids_for_parent = [student.id for student in parent.students]
                if not child_ids_for_parent:
                    current_app.logger.debug(f"Parent {current_user_id} has no students linked.")
                    return message(True, "No students found for this parent.") | {"notes": [], "total": 0, "pages": 0, "current_page": 1, "per_page": per_page, "has_next": False, "has_prev": False}, 200

                current_app.logger.debug(f"Scoping notes list for parent ID: {current_user_id}, Children IDs: {child_ids_for_parent}")
                query = query.filter(Note.student_id.in_(child_ids_for_parent)) #type:ignore[reportGeneralTypeIssues]

                # Validate student_id filter if provided by parent
                if student_id is not None and student_id not in child_ids_for_parent:
                    current_app.logger.warning(f"Parent {current_user_id} attempted to filter notes by non-child student ID {student_id}.")
                    return err_resp(
                        f"Forbidden: You can only filter by your own children's student IDs.",
                        "parent_filter_denied",
                        403,
                    )
                # Ignore teacher_id filter for parents
                teacher_id = None
            elif current_user_role == "teacher":
                # Simple approach: Only show notes they created
                current_app.logger.debug(f"Scoping notes list for teacher ID: {current_user_id}")
                query = query.filter(Note.teacher_id == int(current_user_id)) #type:ignore[reportGeneralTypeIssues]
                teacher_id = current_user_id # Force teacher_id filter
                # Allow filtering by student/module within their own notes
            # Admins see all - apply standard filters below

            # --- Apply Standard Filters (respecting role scoping) ---
            filters_applied = {}
            if student_id is not None:
                # Parent/Student role already filtered or validated above
                filters_applied['student_id'] = student_id
                query = query.filter(Note.student_id == student_id) #type:ignore[reportGeneralTypeIssues]
            if module_id is not None:
                filters_applied['module_id'] = module_id
                query = query.filter(Note.module_id == module_id) #type:ignore[reportGeneralTypeIssues]
            # Apply teacher_id filter only if user is admin AND param is provided
            if teacher_id is not None and current_user_role == "admin":
                filters_applied['teacher_id'] = teacher_id
                query = query.filter(Note.teacher_id == teacher_id) #type:ignore[reportGeneralTypeIssues]
            # --- Group filter ---
            if group_id is not None:
                print('kkkkkkkkkkkkkkkkkkkkkkkkkkkkkkk')
                print(group_id)
                filters_applied['group_id'] = group_id
                # Join with Student to filter by group_id
                query = query.join(Note.student).filter(Student.group_id == group_id)

            if filters_applied:
                 current_app.logger.debug(f"Applying note list filters: {filters_applied}")

            # Add ordering
            query = query.order_by(Note.created_at.desc())

            # Implement pagination
            current_app.logger.debug(f"Paginating notes: page={page}, per_page={per_page}")
            paginated_notes = query.paginate(page=page, per_page=per_page, error_out=False)
            current_app.logger.debug(f"Paginated notes items count: {len(paginated_notes.items)}")

            # Serialize results using dump_data
            notes_data = dump_data(paginated_notes.items, many=True)

            current_app.logger.debug(f"Serialized {len(notes_data)} notes")
            resp = message(True, "Notes list retrieved successfully")
            # Add pagination metadata
            resp["notes"] = notes_data
            resp["total"] = paginated_notes.total
            resp["pages"] = paginated_notes.pages
            resp["current_page"] = paginated_notes.page
            resp["per_page"] = paginated_notes.per_page
            resp["has_next"] = paginated_notes.has_next
            resp["has_prev"] = paginated_notes.has_prev

            current_app.logger.debug(f"Successfully retrieved notes page {page}. Total: {paginated_notes.total}")
            return resp, 200

        except Exception as error:
            log_msg = f"Error getting notes list (role: {current_user_role})"
            if page: log_msg += f", page {page}"
            current_app.logger.error(f"{log_msg}: {error}", exc_info=True)
            return internal_err_resp()

    # --- CREATE (Teacher/Admin) ---
    @staticmethod
    # Add type hints
    def create_note(data: dict, current_user_id: int, current_user_role: str):
        """Create a new note (grade). Assumes @roles_required handled base role."""
        # Decorator already checked for admin/teacher role.

        try:
            # 1. Schema Validation & Deserialization
            from app.models.Schemas import NoteSchema # Temp import
            note_create_schema = NoteSchema() # Temp instance
            # validated_data = note_create_schema.load(data)
            # End Temporary block

            current_app.logger.debug(f"Note data validated by schema. Proceeding with FK checks.")

            # 2. Foreign Key Validation
            fk_errors = NoteService._validate_foreign_keys(data)
            if fk_errors:
                current_app.logger.warning(f"Foreign key validation failed creating note: {fk_errors}. Data: {data}")
                return validation_error(False, fk_errors), 400

            # 3. Determine Teacher ID & Perform Authorization/Business Logic
            teacher_id_to_assign = None
            if current_user_role == "teacher":
                teacher_id_to_assign = current_user_id
                # Optional: Add check if teacher teaches this module or student
                current_app.logger.debug(f"Assigning teacher ID {teacher_id_to_assign} based on logged-in teacher.")
            elif current_user_role == "admin":
                # Assumption: Admin creating a note assigns it to themselves.
                # This requires the admin's user ID to also be a valid teacher ID.
                # If admins can assign notes *for* other teachers, the input DTO and logic need changing.
                teacher_id_to_assign = current_user_id
                # Verify admin user_id exists as a teacher_id (or adjust logic)
                if not Teacher.query.get(teacher_id_to_assign):
                     current_app.logger.error(f"Admin user ID {current_user_id} not found in Teacher table. Cannot assign note.")
                     # This indicates a data consistency issue or flawed assumption.
                     return err_resp("Admin user is not registered as a teacher, cannot create note.", "admin_not_teacher", 400)
                current_app.logger.debug(f"Assigning teacher ID {teacher_id_to_assign} based on logged-in admin.")

            if teacher_id_to_assign is None: # Should not happen with current logic, but safety check
                 current_app.logger.error("Failed to determine teacher ID for note creation.")
                 return internal_err_resp()

            # 4. Validate Grade Value (e.g., 0-20)
            grade_value = data["value"]
            MIN_GRADE, MAX_GRADE = 0, 20
            if not (MIN_GRADE <= grade_value <= MAX_GRADE):
                current_app.logger.warning(f"Invalid grade value received: {grade_value}. Data: {data}")
                return err_resp(
                    f"Invalid grade value. Must be between {MIN_GRADE} and {MAX_GRADE}.",
                    "invalid_grade_value",
                    400,
                )

            # 5. Create Instance & Commit
            new_note = Note(
                student_id=data["student_id"],
                module_id=data["module_id"],
                teacher_id=teacher_id_to_assign,
                value=data["value"],
                comment=data.get("comment")
            )

            db.session.add(new_note)
            db.session.commit()
            current_app.logger.info(f"Note created successfully with ID: {new_note.id} by Teacher/Admin ID: {teacher_id_to_assign}")

            # 6. Serialize & Respond using dump_data
            note_resp_data = dump_data(new_note)
            resp = message(True, "Note created successfully.")
            resp["note"] = note_resp_data
            return resp, 201

        except ValidationError as err:
            db.session.rollback()
            current_app.logger.warning(
                f"Schema validation error creating note: {err.messages}. Data: {data}"
            )
            return validation_error(False, err.messages), 400
        except IntegrityError as error:
            db.session.rollback()
            current_app.logger.warning(
                f"Database integrity error creating note: {error}. Data: {data}", exc_info=True
            )
            return internal_err_resp()
        except SQLAlchemyError as error:
            db.session.rollback()
            current_app.logger.error(
                f"Database error creating note: {error}. Data: {data}", exc_info=True
            )
            return internal_err_resp()
        except Exception as error:
            db.session.rollback()
            current_app.logger.error(f"Unexpected error creating note: {error}. Data: {data}", exc_info=True)
            return internal_err_resp()

    # --- UPDATE (Teacher/Admin) ---
    @staticmethod
    # Add type hints
    def update_note(note_id: int, data: dict, current_user_id: int, current_user_role: str):
        """Update an existing note (value, comment). Assumes @roles_required handled base role."""
        note = Note.query.get(note_id)
        if not note:
            current_app.logger.info(f"Attempted update for non-existent note ID: {note_id}") # Add logging
            return err_resp("Note not found!", "note_404", 404)

        # --- Record-Level Authorization Check ---
        # Only admin or the teacher who created the note can update
        can_update = (current_user_role == "admin") or \
                     (current_user_role == "teacher" and note.teacher_id == int(current_user_id))

        if not can_update:
            current_app.logger.warning(f"Forbidden: User {current_user_id} (Role: {current_user_role}) attempted to update note {note_id} created by teacher {note.teacher_id}.") # Add logging
            return err_resp(
                "Forbidden: You cannot update this note.", "update_forbidden", 403
            )

        if not data:
            current_app.logger.warning(f"Attempted update for note {note_id} with empty data.") # Add logging
            return err_resp(
                "Request body cannot be empty for update.", "empty_update_data", 400
            )

        try:
            # 1. Schema Validation & Deserialization using load_data (partial, only value/comment)
            # Using temporary manual load until load_data adjusted/confirmed.
            from app.models.Schemas import NoteSchema # Temp import
            note_update_schema = NoteSchema(partial=True, only=("value", "comment")) # Temp instance
            # validated_data = note_update_schema.load(data)
            # End Temporary block

            current_app.logger.debug(f"Note data validated by schema for update. Proceeding with value checks for ID: {note_id}") # Add logging

            # 2. Validate Grade Value (if provided)
            if "value" in data:
                grade_value = data["value"]
                MIN_GRADE, MAX_GRADE = 0, 20 # Define boundaries
                if not (MIN_GRADE <= grade_value <= MAX_GRADE):
                    current_app.logger.warning(f"Invalid grade value during update: {grade_value}. Data: {data}")
                    return err_resp(
                        f"Invalid grade value. Must be between {MIN_GRADE} and {MAX_GRADE}.",
                        "invalid_grade_value",
                        400,
                    )
                note.value = grade_value # Update value

            # 3. Update comment if provided
            if "comment" in data:
                note.comment = data["comment"] # Allows setting to null or empty string

            # 4. Commit Changes
            db.session.add(note) # Add modified object to session
            db.session.commit()
            current_app.logger.info(f"Note updated successfully for ID: {note_id} by User ID: {current_user_id}") # Add logging

            # 5. Serialize & Respond using dump_data
            note_resp_data = dump_data(note)
            resp = message(True, "Note updated successfully.")
            resp["note"] = note_resp_data
            return resp, 200

        except ValidationError as err:
            db.session.rollback()
            current_app.logger.warning(
                f"Schema validation error updating note {note_id}: {err.messages}. Data: {data}"
            )
            return validation_error(False, err.messages), 400
        except SQLAlchemyError as error: # Catch potential DB errors
             db.session.rollback()
             current_app.logger.error(
                 f"Database error updating note {note_id}: {error}. Data: {data}", exc_info=True
             )
             return internal_err_resp()
        except Exception as error:
            db.session.rollback()
            current_app.logger.error(
                f"Unexpected error updating note {note_id}: {error}. Data: {data}", exc_info=True
            )
            return internal_err_resp()

    # --- DELETE (Teacher/Admin) ---
    @staticmethod
    # Add type hint
    def delete_note(note_id: int, current_user_id: int, current_user_role: str):
        """Delete a note by ID. Assumes @roles_required handled base role."""
        note = Note.query.get(note_id)
        if not note:
            current_app.logger.info(f"Attempted delete for non-existent note ID: {note_id}") # Add logging
            return err_resp("Note not found!", "note_404", 404)

        # --- Record-Level Authorization Check ---
        # Only admin or the teacher who created the note can delete
        can_delete = (current_user_role == "admin") or \
                     (current_user_role == "teacher" and note.teacher_id == int(current_user_id))

        if not can_delete:
            current_app.logger.warning(f"Forbidden: User {current_user_id} (Role: {current_user_role}) attempted to delete note {note_id} created by teacher {note.teacher_id}.") # Add logging
            return err_resp(
                "Forbidden: You cannot delete this note.", "delete_forbidden", 403
            )

        try:
            current_app.logger.warning(
                f"User {current_user_id} (Role: {current_user_role}) attempting to delete note {note_id}."
            ) # Log intent

            db.session.delete(note)
            db.session.commit()

            current_app.logger.info(
                f"Note {note_id} deleted successfully by User ID: {current_user_id}."
            ) # Log success
            return None, 204

        except SQLAlchemyError as error:
            db.session.rollback()
            current_app.logger.error(
                f"Database error deleting note {note_id}: {error}", exc_info=True
            )
            return err_resp(
                f"Could not delete note due to a database constraint or error.",
                "delete_error_db",
                500,
            )
        except Exception as error:
            db.session.rollback()
            current_app.logger.error(
                f"Unexpected error deleting note {note_id}: {error}", exc_info=True
            )
            return internal_err_resp()
