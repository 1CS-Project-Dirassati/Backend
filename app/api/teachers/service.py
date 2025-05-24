# Added current_app
from flask import current_app
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from marshmallow import ValidationError
from werkzeug.security import generate_password_hash

# Import DB instance and models
from app import db

# Import related models needed for dependency checks
from app.models import Teacher, Session, Module, TeacherModuleAssociation

# Import shared utilities
from app.utils import (
    err_resp,
    message,
    internal_err_resp,
    validation_error,
)

# Import serialization/deserialization utilities from local utils.py
from .utils import dump_data, load_data


class TeacherService:

    # --- GET Single ---
    @staticmethod
    # Add type hints
    def get_teacher_data(teacher_id: int, current_user_id: int, current_user_role: str):
        """Get teacher data by ID, with record-level authorization check"""
        teacher = Teacher.query.get(teacher_id)
        if not teacher:
            current_app.logger.info(
                f"Teacher with ID {teacher_id} not found."
            )  # Add logging
            return err_resp("Teacher not found!", "teacher_404", 404)

        # --- Record-Level Authorization Check ---
        # Admins can see any teacher, teachers can see themselves
        print(int(current_user_id))
        print(int(teacher.id))
       
        if current_user_role != "admin" and int(current_user_id) != int(teacher.id):
            current_app.logger.warning(
                f"Forbidden: User {current_user_id} (Role: {current_user_role}) attempted to access teacher record {teacher_id}."
            )  # Add logging
            return err_resp(
                "Forbidden: You do not have permission to access this teacher's data.",
                "record_access_denied",
                403,
            )
        current_app.logger.debug(
            f"Record access granted for user {current_user_id} to teacher {teacher_id}."
        )  # Add logging

        try:
            # Use dump_data for serialization (excludes password via schema)
            teacher_data = dump_data(teacher)
            resp = message(True, "Teacher data sent successfully")
            resp["teacher"] = teacher_data
            current_app.logger.debug(
                f"Successfully retrieved teacher ID {teacher_id}"
            )  # Add logging
            return resp, 200
        except Exception as error:
            current_app.logger.error(
                f"Error serializing teacher data for ID {teacher_id}: {error}",  # Update log message
                exc_info=True,
            )
            return internal_err_resp()

    # --- GET List with Filters and Pagination (Admin only) ---
    @staticmethod
    # Add type hints
    def get_all_teachers(
        module_id=None,
        page=None,
        per_page=None,
        current_user_role=None,  # Kept for explicit check
    ):
        """Get a paginated list of teachers, filtered (Admin only view)"""
        

        page = page or 1
        per_page = per_page or 10

        try:
            query = Teacher.query
            filters_applied = {}

            # Apply filters
            if module_id is not None:
                filters_applied["module_id"] = module_id
                # Join with TeacherModuleAssociation to filter by module
                query = query.join(TeacherModuleAssociation).filter(
                    TeacherModuleAssociation.module_id == module_id
                )

            if filters_applied:
                current_app.logger.debug(
                    f"Applying teacher list filters: {filters_applied}"
                )

            # Add ordering
            query = query.order_by(Teacher.last_name).order_by(Teacher.first_name)
            

            # Implement pagination
            current_app.logger.debug(
                f"Paginating teachers: page={page}, per_page={per_page}"
            )
            paginated_teachers = query.paginate(
                page=page, per_page=per_page, error_out=False
            )
            
            current_app.logger.debug(
                f"Paginated teachers items count: {len(paginated_teachers.items)}"
            )

            # Serialize results using dump_data (excludes password)
            teachers_data = dump_data(paginated_teachers.items, many=True)
            print(teachers_data)

            current_app.logger.debug(f"Serialized {len(teachers_data)} teachers")
            resp = message(True, "Teachers list retrieved successfully")
            # Add pagination metadata
            resp["teachers"] = teachers_data
            resp["total"] = paginated_teachers.total
            resp["pages"] = paginated_teachers.pages
            resp["current_page"] = paginated_teachers.page
            resp["per_page"] = paginated_teachers.per_page
            resp["has_next"] = paginated_teachers.has_next
            resp["has_prev"] = paginated_teachers.has_prev

            current_app.logger.debug(
                f"Successfully retrieved teachers page {page}. Total: {paginated_teachers.total}"
            )
            return resp, 200

        except Exception as error:
            log_msg = f"Error getting teachers list"
            if page:
                log_msg += f", page {page}"
            current_app.logger.error(f"{log_msg}: {error}", exc_info=True)
            return internal_err_resp()

    # --- CREATE (Admin only) ---
    @staticmethod
    def create_teacher(data: dict):
        """Create a new teacher. Assumes @roles_required('admin') handled authorization."""
        try:
            from app.models.Schemas import TeacherSchema  # Using SQLAlchemyAutoSchema with load_instance=True
            teacher_schema = TeacherSchema()
            
            teacher_instance = teacher_schema.load(data)  # <- Already a Teacher object now!

            # Hash the password AFTER loading
            teacher_instance.password = generate_password_hash(teacher_instance.password)
            current_app.logger.debug(f"Password hashed for teacher email: {teacher_instance.email}")

            db.session.add(teacher_instance)
            db.session.commit()
            current_app.logger.info(f"Teacher created successfully with ID: {teacher_instance.id}")

            teacher_resp_data = dump_data(teacher_instance)
            resp = message(True, "Teacher created successfully.")
            resp["teacher"] = teacher_resp_data
            return resp, 201

        except ValidationError as err:
            db.session.rollback()
            current_app.logger.warning(f"Schema validation error creating teacher: {err.messages}. Data: {data}")
            return validation_error(False, err.messages), 400
        except IntegrityError as error:
            db.session.rollback()
            current_app.logger.warning(f"Database integrity error creating teacher: {error}. Data: {data}", exc_info=True)
            if "teacher_email_key" in str(error.orig) or "UNIQUE constraint failed: teacher.email" in str(error.orig):
                return err_resp(f"Email '{data.get('email')}' already exists.", "duplicate_email", 409)
            return internal_err_resp()
        except SQLAlchemyError as error:
            db.session.rollback()
            current_app.logger.error(f"Database error creating teacher: {error}. Data: {data}", exc_info=True)
            return internal_err_resp()
        except Exception as error:
            db.session.rollback()
            current_app.logger.error(f"Unexpected error creating teacher: {error}. Data: {data}", exc_info=True)
            return internal_err_resp()

    # --- UPDATE (Admin Perspective) ---
    @staticmethod
    # Add type hints
    def update_teacher_by_admin(teacher_id: int, data: dict):
        """Update an existing teacher by ID. Assumes @roles_required('admin') handled authorization."""
        # No role check needed here - decorator handles it.

        teacher = Teacher.query.get(teacher_id)
        if not teacher:
            current_app.logger.info(
                f"Attempted admin update for non-existent teacher ID: {teacher_id}"
            )  # Add logging
            return err_resp("Teacher not found!", "teacher_404", 404)

        try:
            # Update fields
            if "first_name" in data:
                teacher.first_name = data["first_name"]
            if "last_name" in data:
                teacher.last_name = data["last_name"]
            if "email" in data:
                teacher.email = data["email"]
            if "phone_number" in data:
                teacher.phone_number = data["phone_number"]
            if "address" in data:
                teacher.address = data["address"]
            if "profile_picture" in data:
                teacher.profile_picture = data["profile_picture"]
            if "module_key" in data:
                teacher.module_key = data["module_key"]

            db.session.commit()
            current_app.logger.info(f"Teacher {teacher_id} updated successfully by admin")

            teacher_data = dump_data(teacher)
            resp = message(True, "Teacher updated successfully.")
            resp["teacher"] = teacher_data
            return resp, 200

        except ValidationError as err:
            db.session.rollback()
            current_app.logger.warning(
                f"Validation error updating teacher: {err.messages}"
            )
            return validation_error(False, err.messages), 400
        except IntegrityError as error:
            db.session.rollback()
            current_app.logger.warning(
                f"Integrity error updating teacher: {error}", exc_info=True
            )
            if "teacher_email_key" in str(error.orig):
                return err_resp(
                    f"Email '{data.get('email')}' already exists.",
                    "duplicate_email",
                    409,
                )
            return internal_err_resp()
        except SQLAlchemyError as error:
            db.session.rollback()
            current_app.logger.error(
                f"Database error updating teacher: {error}", exc_info=True
            )
            return internal_err_resp()
        except Exception as error:
            db.session.rollback()
            current_app.logger.error(f"Error updating teacher: {error}", exc_info=True)
            return internal_err_resp()

    # --- UPDATE (Teacher updating own profile) ---
    @staticmethod
    # Add type hints
    def update_own_profile(current_user_id: int, data: dict):
        """Update the currently logged-in teacher's own profile. Assumes @roles_required('teacher') handled authorization."""
        teacher = Teacher.query.get(current_user_id)
        if not teacher:
            current_app.logger.error(
                f"Attempted self-update for non-existent teacher ID: {current_user_id}. JWT might be invalid."
            )
            return err_resp("Teacher profile not found.", "self_not_found", 404)

        if not data:
            current_app.logger.warning(
                f"Attempted self-update for teacher {current_user_id} with empty data."
            )  # Add logging
            return err_resp(
                "Request body cannot be empty for update.", "empty_update_data", 400
            )

        try:
            # Use load_data with partial=True and instance=teacher
            # Ensure TeacherSchema excludes email, password, module_key for partial self-updates
            updated_teacher = load_data(data, partial=True, instance=teacher)
            current_app.logger.debug(
                f"Teacher data validated by schema for self-update. Committing changes for ID: {current_user_id}"
            )  # Add logging

            db.session.commit()
            current_app.logger.info(
                f"Teacher self-profile updated successfully for ID: {current_user_id}"
            )  # Add logging

            # Serialize & Respond using dump_data
            teacher_resp_data = dump_data(updated_teacher)
            resp = message(True, "Your profile has been updated successfully.")
            resp["teacher"] = teacher_resp_data
            return resp, 200

        except ValidationError as err:
            db.session.rollback()
            current_app.logger.warning(
                f"Schema validation error during self-update for teacher {current_user_id}: {err.messages}. Data: {data}"
            )
            return validation_error(False, err.messages), 400
        except (
            IntegrityError
        ) as error:  # Catch potential unique constraint violations (e.g., phone if unique)
            db.session.rollback()
            current_app.logger.warning(
                f"Database integrity error during self-update for teacher {current_user_id}: {error}. Data: {data}",
                exc_info=True,
            )
            # Add specific checks if needed
            return internal_err_resp()  # Or a specific 409
        except SQLAlchemyError as error:
            db.session.rollback()
            current_app.logger.error(
                f"Database error during self-update for teacher {current_user_id}: {error}. Data: {data}",
                exc_info=True,
            )
            return internal_err_resp()
        except Exception as error:
            db.session.rollback()
            current_app.logger.error(
                f"Unexpected error during self-update for teacher {current_user_id}: {error}. Data: {data}",
                exc_info=True,
            )
            return internal_err_resp()

    # --- DELETE (Admin only) ---
    @staticmethod
    # Add type hint
    def delete_teacher(teacher_id: int):
        """Delete a teacher by ID. Assumes @roles_required('admin') handled authorization."""
        # No role check needed here - decorator handles it.

        teacher = Teacher.query.get(teacher_id)
        if not teacher:
            current_app.logger.info(
                f"Attempted admin delete for non-existent teacher ID: {teacher_id}"
            )  # Add logging
            return err_resp("Teacher not found!", "teacher_404", 404)

        try:
            # --- Dependency Checks ---
            # Check modules assigned via association table
            modules_assigned = (
                Module.query.join(Teacher).filter(Teacher.id == teacher_id).all()
            )
            if modules_assigned:
                module_names = [m.name for m in modules_assigned]
                current_app.logger.warning(
                    f"Delete conflict for teacher {teacher_id}: Assigned to modules: {module_names}"
                )
                return err_resp(
                    f"Cannot delete teacher: Assigned to modules: {', '.join(module_names)}. Reassign modules first.",
                    "delete_conflict_modules",
                    409,
                )

            # Check sessions (direct relationship)
            if teacher.sessions:
                session_ids = [s.id for s in teacher.sessions[:5]]  # Example IDs
                current_app.logger.warning(
                    f"Delete conflict for teacher {teacher_id}: Has sessions: {session_ids}"
                )
                return err_resp(
                    f"Cannot delete teacher: Associated with existing sessions (e.g., IDs: {session_ids}). Delete or reassign sessions first.",
                    "delete_conflict_sessions",
                    409,
                )

            # If checks pass:
            current_app.logger.warning(
                f"Attempting admin delete for teacher {teacher_id}. THIS WILL CASCADE DELETE associated Teachings, Cours, Notes."
            )  # Log warning

            db.session.delete(teacher)
            db.session.commit()

            current_app.logger.info(
                f"Teacher {teacher_id} and associated data (Teachings, Cours, Notes) deleted successfully by admin."  # Clarify admin action
            )
            return None, 204

        except SQLAlchemyError as error:
            db.session.rollback()
            current_app.logger.error(
                f"Database error during admin delete for teacher {teacher_id}: {error}",
                exc_info=True,
            )
            return err_resp(
                f"Could not delete teacher due to a database constraint or error.",
                "delete_error_db",
                500,
            )
        except Exception as error:
            db.session.rollback()
            current_app.logger.error(
                f"Unexpected error during admin delete for teacher {teacher_id}: {error}",
                exc_info=True,
            )
            return internal_err_resp()

    # --- Assign Module to Teacher ---
    @staticmethod
    def assign_module(teacher_id: int, module_id: int):
        """Assign a module to a teacher"""
        try:
            # Check if both teacher and module exist
            teacher = Teacher.query.get(teacher_id)
            module = Module.query.get(module_id)
            
            if not teacher:
                return err_resp("Teacher not found!", "teacher_404", 404)
            if not module:
                return err_resp("Module not found!", "module_404", 404)
            
            # Check if association already exists
            existing_association = TeacherModuleAssociation.query.filter_by(
                teacher_id=teacher_id,
                module_id=module_id
            ).first()
            
            if existing_association:
                return err_resp(
                    "Module is already assigned to this teacher.",
                    "duplicate_assignment",
                    409
                )
            
            # Create new association
            association = TeacherModuleAssociation(
                teacher_id=teacher_id,
                module_id=module_id
            )
            
            db.session.add(association)
            db.session.commit()
            
            return message(True, "Module assigned to teacher successfully."), 201
            
        except SQLAlchemyError as error:
            db.session.rollback()
            current_app.logger.error(
                f"Database error assigning module to teacher: {error}",
                exc_info=True
            )
            return internal_err_resp()
        except Exception as error:
            db.session.rollback()
            current_app.logger.error(
                f"Error assigning module to teacher: {error}",
                exc_info=True
            )
            return internal_err_resp()

    # --- Remove Module from Teacher ---
    @staticmethod
    def remove_module(teacher_id: int, module_id: int):
        """Remove a module from a teacher"""
        try:
            # Check if association exists
            association = TeacherModuleAssociation.query.filter_by(
                teacher_id=teacher_id,
                module_id=module_id
            ).first()
            
            if not association:
                return err_resp(
                    "Module is not assigned to this teacher.",
                    "assignment_not_found",
                    404
                )
            
            db.session.delete(association)
            db.session.commit()
            
            return None, 204  # No Content
            
        except SQLAlchemyError as error:
            db.session.rollback()
            current_app.logger.error(
                f"Database error removing module from teacher: {error}",
                exc_info=True
            )
            return internal_err_resp()
        except Exception as error:
            db.session.rollback()
            current_app.logger.error(
                f"Error removing module from teacher: {error}",
                exc_info=True
            )
            return internal_err_resp()
