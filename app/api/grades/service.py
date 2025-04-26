from flask import current_app
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from marshmallow import ValidationError
from sqlalchemy.orm import joinedload  # For eager loading related data

# Import DB instance and models
from app import db
from app.models import Note, Student, Module, Teacher, Parent  # Import related models

# Import shared utilities and the schema CLASS
from app.models.Schemas import NoteSchema
from app.utils import err_resp, message, internal_err_resp, validation_error

# --- Schema instances FOR VALIDATION (.load) ---
# teacher_id often excluded as it's derived from logged-in user
note_create_schema = NoteSchema(exclude=(), dump_only=("teacher_id"))
note_update_schema = NoteSchema(partial=True, only=("value", "comment"))

# --- Utility for SERIALIZATION (.dump) ---
from .utils import load_data


class NoteService:

    # --- Helper for Foreign Key Validation ---
    @staticmethod
    def _validate_foreign_keys(data):
        errors = {}
        if "student_id" in data and not Student.query.get(data["student_id"]):
            errors["student_id"] = f"Student with ID {data['student_id']} not found."
        if "module_id" in data and not Module.query.get(data["module_id"]):
            errors["module_id"] = f"Module with ID {data['module_id']} not found."
        # teacher_id is usually handled separately based on logged-in user
        return errors

    # --- Helper for Authorization Check (View/Modify) ---
    @staticmethod
    def _can_access_note(
        note, current_user_id, current_user_role, current_user_parent_id=None
    ):
        """Check if the current user can access/modify this specific note"""
        if current_user_role == "admin":
            return True
        if current_user_role == "teacher" and note.teacher_id == current_user_id:
            # Teacher can access/modify notes they created
            return True
        if current_user_role == "student" and note.student_id == current_user_id:
            # Student can view their own notes
            return True
        if current_user_role == "parent":
            # Parent check needs Student object to get parent_id
            # This check is better performed within the method after fetching the note/student
            # Placeholder: return note.student.parent_id == current_user_id
            return True  # Actual check moved
        return False

    # --- GET Single ---
    @staticmethod
    def get_note_data(note_id, current_user_id, current_user_role):
        """Get note data by ID, with authorization check"""
        # Eager load related data for context if needed by schema/DTO
        note = Note.query.options(
            joinedload(Note.student), joinedload(Note.module), joinedload(Note.teacher)
        ).get(note_id)

        if not note:
            return err_resp("Note not found!", "note_404", 404)

        # --- Authorization Check ---
        can_access = False
        if current_user_role == "admin":
            can_access = True
        elif current_user_role == "teacher" and note.teacher_id == current_user_id:
            can_access = True
        elif current_user_role == "student" and note.student_id == current_user_id:
            can_access = True
        elif (
            current_user_role == "parent" and note.student.parent_id == current_user_id
        ):  # Assuming JWT ID for parent IS parent.id
            can_access = True

        if not can_access:
            return err_resp(
                "Forbidden: You do not have access to this note.", "access_denied", 403
            )

        try:
            # Pass context if schema needs it for related fields
            # note_data = load_data(note, context={'include_relations': True})
            note_data = load_data(note)
            resp = message(True, "Note data sent successfully")
            resp["note"] = note_data
            return resp, 200
        except Exception as error:
            current_app.logger.error(
                f"Error getting note data for ID {note_id}: {error}", exc_info=True
            )
            return internal_err_resp()

    # --- GET List with Filters & Authorization ---
    @staticmethod
    def get_all_notes(
        student_id=None,
        module_id=None,
        teacher_id=None,
        current_user_id=None,
        current_user_role=None,
    ):
        """Get a list of notes, filtered, with role-based access control"""
        try:
            query = Note.query.options(
                joinedload(Note.student),  # Eager load for potential filtering/display
                joinedload(Note.module),
                joinedload(Note.teacher),
            )

            # --- Role-Based Filtering (Applied first) ---
            if current_user_role == "student":
                # Students ONLY see their own notes
                query = query.filter(Note.student_id == current_user_id)  # type: ignore[reportGeneralTypeIssues]
                # Ignore other filters passed by student
                module_id = teacher_id = None
            elif current_user_role == "parent":
                # Parents ONLY see notes for their children
                # Find the parent's children IDs first
                parent = Parent.query.get(current_user_id)
                if not parent:
                    return err_resp("Parent profile not found.", "parent_404", 404)
                # Assuming Parent has a relationship with Student
                # initialize child_ids to an empty list
                child_ids = [student.id for student in parent.students]
                if not child_ids:  # Parent has no students linked
                    resp = message(True, "No students found for this parent.")
                    resp["notes"] = []
                    return resp, 200
                query = query.filter(Note.student_id.in_(child_ids))  # type: ignore[reportGeneralTypeIssues]
                # Apply student_id filter only if it's one of their children
                if student_id is not None and student_id not in child_ids:
                    return err_resp(
                        f"Forbidden: Cannot filter by student ID {student_id}.",
                        "parent_filter_denied",
                        403,
                    )
                # Ignore teacher_id filter for parents
                teacher_id = None
            elif current_user_role == "teacher":
                # Teachers see notes THEY created, OR notes for students in modules THEY teach (more complex)
                # Simple approach: Only show notes they created
                query = query.filter(Note.teacher_id == current_user_id)  # type: ignore[reportGeneralTypeIssues]
                # Allow filtering by student/module within their own notes
            # Admins see all - apply standard filters below

            # --- Apply Standard Filters (if not overridden by role) ---

            if student_id is not None:
                # Check again for parent role edge case handled above
                if current_user_role != "parent" or student_id in child_ids:
                    query = query.filter(Note.student_id == student_id)  # type: ignore[reportGeneralTypeIssues]
            if module_id is not None:
                query = query.filter(Note.module_id == module_id)  # type: ignore[reportGeneralTypeIssues]
            # Apply teacher_id filter only if user is admin AND param is provided
            if teacher_id is not None and current_user_role == "admin":
                query = query.filter(Note.teacher_id == teacher_id)  # type: ignore[reportGeneralTypeIssues]

            # Add ordering
            notes = query.order_by(Note.created_at.desc()).all()

            notes_data = load_data(notes, many=True)
            resp = message(True, "Notes list retrieved successfully")
            resp["notes"] = notes_data
            return resp, 200
        except Exception as error:
            filters_applied = {
                k: v
                for k, v in locals().items()
                if k in ["student_id", "module_id", "teacher_id"] and v is not None
            }
            current_app.logger.error(
                f"Error getting all notes (role: {current_user_role}) with filters {filters_applied}: {error}",
                exc_info=True,
            )
            return internal_err_resp()

    # --- CREATE (Teacher/Admin) ---
    @staticmethod
    def create_note(data, current_user_id, current_user_role):
        """Create a new note (grade)"""
        # Only teachers and admins can create notes
        if current_user_role not in ["admin", "teacher"]:
            return err_resp(
                "Forbidden: Only Teachers or Administrators can create notes.",
                "create_forbidden",
                403,
            )

        try:
            # 1. Schema Validation (excludes teacher_id)
            validated_data = note_create_schema.load(data)

            # 2. Foreign Key Validation
            fk_errors = NoteService._validate_foreign_keys(validated_data)
            if fk_errors:
                return validation_error(False, fk_errors), 400

            # 3. Authorization/Business Logic Check (Teacher specific)
            teacher_id_to_assign = None
            if current_user_role == "teacher":
                teacher_id_to_assign = current_user_id
                # --- Add check: Does this teacher teach this module? ---
                # module = Module.query.get(validated_data['module_id'])
                # if not module or module.teacher_id != current_user_id:
                #    return err_resp(f"Forbidden: You do not teach module ID {validated_data['module_id']}.", "module_mismatch", 403)
                # --- Add check: Is this student enrolled in a group taught by this teacher for this module? (More complex) ---
            elif current_user_role == "admin":
                # Admin needs to specify the teacher ID - modify schema/logic if needed
                # For now, assume admin assigns it as themselves (or needs modification)
                # teacher_id_to_assign = data.get('teacher_id') # If admin provides it
                # if not teacher_id_to_assign or not Teacher.query.get(teacher_id_to_assign):
                #    return err_resp("Invalid or missing teacher_id for admin creation.", "admin_teacher_id_invalid", 400)
                # Let's assume admin *is* the teacher for simplicity here, needs refinement
                teacher_id_to_assign = current_user_id  # Requires Admin user ID to exist in Teacher table or adjust logic

            if teacher_id_to_assign is None:  # Safety check
                return internal_err_resp()

            # 4. Validate Grade Value (Example: 0-20)
            if not (0 <= validated_data["value"] <= 20):
                return err_resp(
                    "Invalid grade value. Must be between 0 and 20.",
                    "invalid_grade_value",
                    400,
                )

            # 5. Create Instance & Commit
            new_note = Note(
                student_id=validated_data["student_id"],
                module_id=validated_data["module_id"],
                teacher_id=teacher_id_to_assign,  # Use determined teacher ID
                value=validated_data["value"],
                comment=validated_data.get("comment"),
            )

            db.session.add(new_note)
            db.session.commit()

            # 6. Serialize & Respond
            note_data = load_data(new_note)
            resp = message(True, "Note created successfully.")
            resp["note"] = note_data
            return resp, 201

        except ValidationError as err:
            current_app.logger.warning(
                f"Validation error creating note: {err.messages}"
            )
            return validation_error(False, err.messages), 400
        except (
            IntegrityError
        ) as error:  # Catch potential unique constraints if added (e.g., one note per student/module)
            db.session.rollback()
            current_app.logger.warning(
                f"Integrity error creating note: {error}", exc_info=True
            )
            # Example: if "unique_student_module_note" in str(error):
            #     return err_resp("A grade already exists for this student in this module.", "duplicate_note", 409)
            return internal_err_resp()
        except SQLAlchemyError as error:
            db.session.rollback()
            current_app.logger.error(
                f"Database error creating note: {error}", exc_info=True
            )
            return internal_err_resp()
        except Exception as error:
            db.session.rollback()
            current_app.logger.error(f"Error creating note: {error}", exc_info=True)
            return internal_err_resp()

    # --- UPDATE (Teacher/Admin) ---
    @staticmethod
    def update_note(note_id, data, current_user_id, current_user_role):
        """Update an existing note (value, comment)"""
        note = Note.query.get(note_id)
        if not note:
            return err_resp("Note not found!", "note_404", 404)

        # --- Authorization Check ---
        # Only admin or the teacher who created the note can update
        if not (
            current_user_role == "admin"
            or (current_user_role == "teacher" and note.teacher_id == current_user_id)
        ):
            return err_resp(
                "Forbidden: You cannot update this note.", "update_forbidden", 403
            )

        if not data:
            return err_resp(
                "Request body cannot be empty for update.", "empty_update_data", 400
            )

        try:
            # 1. Schema Validation (only value, comment)
            validated_data = note_update_schema.load(data)

            # 2. Validate Grade Value (if provided)
            if "value" in validated_data and not (0 <= validated_data["value"] <= 20):
                return err_resp(
                    "Invalid grade value. Must be between 0 and 20.",
                    "invalid_grade_value",
                    400,
                )

            # 3. Update Instance Fields & Commit
            if "value" in validated_data:
                note.value = validated_data["value"]
            if "comment" in validated_data:
                note.comment = validated_data["comment"]
            # Note: updated_at is not in the model, created_at remains fixed

            db.session.add(note)
            db.session.commit()

            # 4. Serialize & Respond
            note_data = load_data(note)
            resp = message(True, "Note updated successfully.")
            resp["note"] = note_data
            return resp, 200

        except ValidationError as err:
            db.session.rollback()
            current_app.logger.warning(
                f"Validation error updating note {note_id}: {err.messages}"
            )
            return validation_error(False, err.messages), 400
        except Exception as error:  # Catch potential DB errors
            db.session.rollback()
            current_app.logger.error(
                f"Error updating note {note_id}: {error}", exc_info=True
            )
            return internal_err_resp()

    # --- DELETE (Teacher/Admin) ---
    @staticmethod
    def delete_note(note_id, current_user_id, current_user_role):
        """Delete a note by ID"""
        note = Note.query.get(note_id)
        if not note:
            return err_resp("Note not found!", "note_404", 404)

        # --- Authorization Check ---
        # Only admin or the teacher who created the note can delete
        if not (
            current_user_role == "admin"
            or (current_user_role == "teacher" and note.teacher_id == current_user_id)
        ):
            return err_resp(
                "Forbidden: You cannot delete this note.", "delete_forbidden", 403
            )

        try:
            db.session.delete(note)
            db.session.commit()
            return None, 204  # 204 No Content

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
                f"Error deleting note {note_id}: {error}", exc_info=True
            )
            return internal_err_resp()
