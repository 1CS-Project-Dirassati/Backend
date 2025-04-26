from flask import current_app
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from marshmallow import ValidationError
from werkzeug.security import generate_password_hash

# Import DB instance and models
from app import db
from app.models import Teacher, Session, Module  # Import related models for checks

# Import shared utilities and the schema CLASS
# Ensure TeacherSchema exists, handles password load/dump correctly
from app.models.Schemas import TeacherSchema
from app.utils import err_resp, message, internal_err_resp, validation_error

# --- Schema instances FOR VALIDATION (.load) ---
# Ensure password field in TeacherSchema has load_only=True
teacher_create_schema = TeacherSchema()
# Define schemas for specific update scenarios
teacher_admin_update_schema = TeacherSchema(partial=True, exclude=("email", "password"))
teacher_self_update_schema = TeacherSchema(
    partial=True, exclude=("email", "password", "module_key")
)


# --- Utility for SERIALIZATION (.dump) ---
from .utils import load_data


class TeacherService:

    # --- GET Single ---
    @staticmethod
    def get_teacher_data(teacher_id, current_user_id, current_user_role):
        """Get teacher data by ID, with authorization check"""
        teacher = Teacher.query.get(teacher_id)
        if not teacher:
            return err_resp("Teacher not found!", "teacher_404", 404)

        # --- Authorization Check ---
        # Admins can see any teacher, teachers can see themselves
        if current_user_role != "admin" and current_user_id != teacher.id:
            return err_resp(
                "Forbidden: You do not have access to this teacher's data.",
                "access_denied",
                403,
            )

        try:
            teacher_data = load_data(teacher)  # Excludes password via schema
            resp = message(True, "Teacher data sent successfully")
            resp["teacher"] = teacher_data
            return resp, 200
        except Exception as error:
            current_app.logger.error(
                f"Error getting teacher data for ID {teacher_id}: {error}",
                exc_info=True,
            )
            return internal_err_resp()

    # --- GET List with Filters (Admin only) ---
    @staticmethod
    def get_all_teachers(module_key=None, current_user_role=None):
        """Get a list of teachers, filtered (Admin only view)"""
        if current_user_role != "admin":
            return err_resp("Forbidden: Access denied.", "list_forbidden", 403)

        try:
            query = Teacher.query

            # Apply filters
            if module_key is not None:
                # Use ilike for case-insensitive partial match, or == for exact match
                if not Teacher.module_key:
                    return err_resp(
                        "Module key cannot be empty.", "empty_module_key", 400
                    )
                query = query.filter(Teacher.module_key.ilike(f"%{module_key}%"))
                # query = query.filter(Teacher.module_key == module_key) # Exact match

            # Add ordering
            teachers = (
                query.order_by(Teacher.last_name).order_by(Teacher.first_name).all()
            )

            teachers_data = load_data(teachers, many=True)  # Excludes password
            resp = message(True, "Teachers list retrieved successfully")
            resp["teachers"] = teachers_data
            return resp, 200
        except Exception as error:
            filters_applied = {
                k: v
                for k, v in locals().items()
                if k in ["module_key"] and v is not None
            }
            current_app.logger.error(
                f"Error getting all teachers with filters {filters_applied}: {error}",
                exc_info=True,
            )
            return internal_err_resp()

    # --- CREATE (Admin only) ---
    @staticmethod
    def create_teacher(data, current_user_role):
        """Create a new teacher (Admin only)"""
        if current_user_role != "admin":
            return err_resp(
                "Forbidden: Only administrators can create teacher accounts.",
                "create_forbidden",
                403,
            )

        try:
            # 1. Schema Validation
            validated_data = teacher_create_schema.load(data)

            # 2. Hash Password
            password_plain = validated_data.pop("password")
            password_hash = generate_password_hash(password_plain)

            # 3. Create Instance & Commit
            new_teacher = Teacher(
                email=validated_data["email"],
                password_hash=password_hash,  # Pass HASHED password
                phone_number=validated_data["phone_number"],
                first_name=validated_data.get("first_name"),
                last_name=validated_data.get("last_name"),
                module_key=validated_data.get("module_key"),
                # address and profile_picture have defaults or can be set if provided
            )
            # If address/profile_picture are in validated_data, set them explicitly
            if "address" in validated_data:
                new_teacher.address = validated_data["address"]
            if "profile_picture" in validated_data:
                new_teacher.profile_picture = validated_data["profile_picture"]

            db.session.add(new_teacher)
            db.session.commit()

            # 4. Serialize & Respond
            teacher_data = load_data(new_teacher)
            resp = message(True, "Teacher created successfully.")
            resp["teacher"] = teacher_data
            return resp, 201

        except ValidationError as err:
            current_app.logger.warning(
                f"Validation error creating teacher: {err.messages}"
            )
            return validation_error(False, err.messages), 400
        except IntegrityError as error:  # Catch duplicate email
            db.session.rollback()
            current_app.logger.warning(
                f"Integrity error creating teacher: {error}", exc_info=True
            )
            if "teacher_email_key" in str(
                error
            ) or "UNIQUE constraint failed: teacher.email" in str(error):
                return err_resp(
                    f"Email '{data.get('email')}' already exists.",
                    "duplicate_email",
                    409,
                )
            return internal_err_resp()
        except SQLAlchemyError as error:
            db.session.rollback()
            current_app.logger.error(
                f"Database error creating teacher: {error}", exc_info=True
            )
            return internal_err_resp()
        except Exception as error:
            db.session.rollback()
            current_app.logger.error(f"Error creating teacher: {error}", exc_info=True)
            return internal_err_resp()

    # --- UPDATE (Admin Perspective) ---
    @staticmethod
    def update_teacher_by_admin(teacher_id, data, current_user_role):
        """Update an existing teacher by ID (Admin only)"""
        if current_user_role != "admin":
            return err_resp(
                "Forbidden: Only administrators can update teacher details.",
                "update_forbidden",
                403,
            )

        teacher = Teacher.query.get(teacher_id)
        if not teacher:
            return err_resp("Teacher not found!", "teacher_404", 404)

        if not data:
            return err_resp(
                "Request body cannot be empty for update.", "empty_update_data", 400
            )

        try:
            validated_data = teacher_admin_update_schema.load(data)

            for key, value in validated_data.items():
                setattr(teacher, key, value)
            # teacher.updated_at handled by onupdate

            db.session.add(teacher)
            db.session.commit()

            teacher_data = load_data(teacher)
            resp = message(True, "Teacher updated successfully by admin.")
            resp["teacher"] = teacher_data
            return resp, 200

        except ValidationError as err:
            db.session.rollback()
            current_app.logger.warning(
                f"Validation error updating teacher {teacher_id} by admin: {err.messages}"
            )
            return validation_error(False, err.messages), 400
        except (
            IntegrityError
        ) as error:  # Catch potential unique constraint violations (e.g., phone if unique)
            db.session.rollback()
            current_app.logger.warning(
                f"Integrity error updating teacher {teacher_id} by admin: {error}",
                exc_info=True,
            )
            return internal_err_resp()
        except SQLAlchemyError as error:
            db.session.rollback()
            current_app.logger.error(
                f"Database error updating teacher {teacher_id} by admin: {error}",
                exc_info=True,
            )
            return internal_err_resp()
        except Exception as error:
            db.session.rollback()
            current_app.logger.error(
                f"Error updating teacher {teacher_id} by admin: {error}", exc_info=True
            )
            return internal_err_resp()

    # --- UPDATE (Teacher updating own profile) ---
    @staticmethod
    def update_own_profile(current_user_id, data):
        """Update the currently logged-in teacher's own profile"""
        teacher = Teacher.query.get(current_user_id)
        if not teacher:
            return err_resp("Teacher profile not found.", "self_not_found", 404)

        if not data:
            return err_resp(
                "Request body cannot be empty for update.", "empty_update_data", 400
            )

        try:
            validated_data = teacher_self_update_schema.load(data)

            for key, value in validated_data.items():
                setattr(teacher, key, value)
            # teacher.updated_at handled by onupdate

            db.session.add(teacher)
            db.session.commit()

            teacher_data = load_data(teacher)
            resp = message(True, "Your profile has been updated successfully.")
            resp["teacher"] = teacher_data
            return resp, 200

        except ValidationError as err:
            db.session.rollback()
            current_app.logger.warning(
                f"Validation error updating own profile for teacher {current_user_id}: {err.messages}"
            )
            return validation_error(False, err.messages), 400
        except (
            IntegrityError
        ) as error:  # Catch potential unique constraint violations (e.g., phone if unique)
            db.session.rollback()
            current_app.logger.warning(
                f"Integrity error updating own profile for teacher {current_user_id}: {error}",
                exc_info=True,
            )
            return internal_err_resp()
        except SQLAlchemyError as error:
            db.session.rollback()
            current_app.logger.error(
                f"Database error updating own profile for teacher {current_user_id}: {error}",
                exc_info=True,
            )
            return internal_err_resp()
        except Exception as error:
            db.session.rollback()
            current_app.logger.error(
                f"Error updating own profile for teacher {current_user_id}: {error}",
                exc_info=True,
            )
            return internal_err_resp()

    # --- DELETE (Admin only) ---
    @staticmethod
    def delete_teacher(teacher_id, current_user_role):
        """Delete a teacher by ID (Admin only)"""
        if current_user_role != "admin":
            return err_resp(
                "Forbidden: Only administrators can delete teachers.",
                "delete_forbidden",
                403,
            )

        teacher = Teacher.query.get(teacher_id)
        if not teacher:
            return err_resp("Teacher not found!", "teacher_404", 404)

        try:
            # --- Dependency Checks (Crucial!) ---
            # Check if teacher is assigned to any modules
            if teacher.modules:
                module_names = [m.name for m in teacher.modules]
                return err_resp(
                    f"Cannot delete teacher: Assigned to modules: {', '.join(module_names)}. Reassign modules first.",
                    "delete_conflict_modules",
                    409,
                )

            # Check if teacher has upcoming sessions (optional, depends on requirements)
            # from datetime import datetime, timezone
            # upcoming_sessions = Session.query.filter(Session.teacher_id == teacher_id, Session.start_time >= datetime.now(timezone.utc)).count()
            # if upcoming_sessions > 0:
            #     return err_resp(f"Cannot delete teacher: Has {upcoming_sessions} upcoming scheduled sessions. Reschedule first.", "delete_conflict_sessions", 409)

            # Note: assigned_groups (Teachings), cours, notes have cascade delete.
            # Sessions relationship does NOT have cascade - deleting teacher would fail if sessions exist unless teacher_id is nullable (it's not).
            # Need to decide: prevent delete if sessions exist, or manually delete/reassign sessions first.
            # Let's prevent deletion if sessions exist for safety.
            if teacher.sessions:
                session_ids = [
                    s.id for s in teacher.sessions[:5]
                ]  # Show first few session IDs
                return err_resp(
                    f"Cannot delete teacher: Associated with existing sessions (e.g., IDs: {session_ids}). Delete or reassign sessions first.",
                    "delete_conflict_sessions",
                    409,
                )

            current_app.logger.warning(
                f"Attempting to delete teacher {teacher_id} by admin {current_user_role}. This will cascade delete associated Teachings, Cours, Notes."
            )

            # If checks pass:
            db.session.delete(teacher)
            db.session.commit()

            current_app.logger.info(
                f"Teacher {teacher_id} and associated data (Teachings, Cours, Notes) deleted successfully."
            )
            return None, 204  # 204 No Content

        except SQLAlchemyError as error:
            db.session.rollback()
            current_app.logger.error(
                f"Database error deleting teacher {teacher_id}: {error}", exc_info=True
            )
            # This might happen if a dependency check was missed or a DB constraint exists
            return err_resp(
                f"Could not delete teacher due to a database constraint or error.",
                "delete_error_db",
                500,
            )
        except Exception as error:
            db.session.rollback()
            current_app.logger.error(
                f"Error deleting teacher {teacher_id}: {error}", exc_info=True
            )
            return internal_err_resp()
