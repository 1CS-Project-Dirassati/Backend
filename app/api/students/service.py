from flask import current_app
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from marshmallow import ValidationError
from werkzeug.security import generate_password_hash  # For hashing passwords

# Import DB instance and models
from app import db
from app.models import Student, Level, Group, Parent  # Import related models

# Import shared utilities and the schema CLASS
# Ensure StudentSchema exists and excludes 'password' on dump
from app.models.Schemas import StudentSchema
from app.utils import err_resp, message, internal_err_resp, validation_error

# --- Schema instances FOR VALIDATION (.load) ---
# Assume StudentSchema has load_instance=True if needed, and handles password on load
# Ensure password field in schema has load_only=True
student_create_schema = StudentSchema()
student_update_schema = StudentSchema(
    partial=True, exclude=("email", "password"),
        dump_only="parent_id"
)  # Exclude sensitive/immutable fields on update
student_approval_schema = StudentSchema(only=("is_approved",), partial=True)


# --- Utility for SERIALIZATION (.dump) ---
from .utils import load_data


class StudentService:

    # --- Helper for Foreign Key Validation ---
    @staticmethod
    def _validate_foreign_keys(data, is_update=False):
        errors = {}
        if "level_id" in data and not Level.query.get(data["level_id"]):
            errors["level_id"] = f"Level with ID {data['level_id']} not found."
        # group_id is nullable, but if provided, should exist
        if data.get("group_id") is not None and not Group.query.get(data["group_id"]):
            errors["group_id"] = f"Group with ID {data['group_id']} not found."
        # parent_id is required on create, check existence
        if "parent_id" in data and not Parent.query.get(data["parent_id"]):
            errors["parent_id"] = f"Parent with ID {data['parent_id']} not found."

        if not is_update:  # Check required FKs for creation
            if "level_id" not in data:
                errors["level_id"] = "level_id is required."
            if "parent_id" not in data:
                errors["parent_id"] = "parent_id is required."
        return errors

    # --- Check Authorization for Specific Student ---
    @staticmethod
    def _check_access(
        target_student_id,
        current_user_id,
        current_user_role,
        current_user_parent_id=None,
    ):
        """Check if the current user can access the target student"""
        if current_user_role == "admin" or current_user_role == "teacher":
            return True  # Admins/Teachers can access any student
        if current_user_role == "student" and target_student_id == current_user_id:
            return True  # Student can access their own profile
        if (
            current_user_role == "parent"
            and current_user_parent_id == target_student_id
        ):
            # Correction: Parent access check should be against student.parent_id
            # This check needs the actual student object, so move inside get/update methods
            return True  # Placeholder - actual check moved
        return False

    # --- GET Single ---
    @staticmethod
    def get_student_data(
        student_id, current_user_id, current_user_role, current_user_parent_id=None
    ):
        """Get student data by ID, with authorization check"""
        student = Student.query.get(student_id)
        if not student:
            return err_resp("Student not found!", "student_404", 404)

        # --- Authorization Check ---
        can_access = False
        if current_user_role in ["admin", "teacher"]:
            can_access = True
        elif current_user_role == "student" and student.id == current_user_id:
            can_access = True
        elif (
            current_user_role == "parent" and student.parent_id == current_user_id
        ):  # Compare student's parent_id with JWT user ID (assuming parent JWT ID is parent.id)
            can_access = True

        if not can_access:
            return err_resp(
                "Forbidden: You do not have access to this student's data.",
                "access_denied",
                403,
            )

        try:
            student_data = load_data(student)  # Excludes password via schema
            resp = message(True, "Student data sent successfully")
            resp["student"] = student_data
            return resp, 200
        except Exception as error:
            current_app.logger.error(
                f"Error getting student data for ID {student_id}: {error}",
                exc_info=True,
            )
            return internal_err_resp()

    # --- GET List with Filters ---
    @staticmethod
    def get_all_students(
        level_id=None,
        group_id=None,
        parent_id=None,
        is_approved=None,
        current_user_role=None,
        current_user_id=None,
    ):
        """Get a list of students, filtered, with role-based access control"""
        try:
            query = Student.query

            # --- Role-Based Filtering ---
            # Parents should only see their own children
            if current_user_role == "parent":
                query = query.filter(Student.parent_id == current_user_id)  # type: ignore[reportGeneralTypeIssues]
            # Students should only see themselves (list endpoint might not be useful for them)
            elif current_user_role == "student":
                query = query.filter(Student.id == current_user_id)
            # Admins/Teachers can see all, apply other filters

            # --- Apply Standard Filters ---
            if level_id is not None:
                query = query.filter(Student.level_id == level_id)  # type: ignore[reportGeneralTypeIssues]
            if group_id is not None:
                query = query.filter(Student.group_id == group_id)
            # Only apply parent_id filter if user is admin/teacher (parent filter already applied above)
            if parent_id is not None and current_user_role in ["admin", "teacher"]:
                query = query.filter(Student.parent_id == parent_id)  # type: ignore[reportGeneralTypeIssues]
            if is_approved is not None:
                query = query.filter(Student.is_approved == is_approved)

            # Add ordering
            students = query.order_by(Student.last_name, Student.first_name).all()  # type: ignore[reportGeneralTypeIssues]

            students_data = load_data(students, many=True)  # Excludes password
            resp = message(True, "Students list retrieved successfully")
            resp["students"] = students_data
            return resp, 200
        except Exception as error:
            # Log details including filters
            filters_applied = {
                k: v
                for k, v in locals().items()
                if k in ["level_id", "group_id", "parent_id", "is_approved"]
                and v is not None
            }
            current_app.logger.error(
                f"Error getting all students (role: {current_user_role}) with filters {filters_applied}: {error}",
                exc_info=True,
            )
            return internal_err_resp()

    # --- CREATE ---
    @staticmethod
    def create_student(data):
        """Create a new student"""
        try:
            # 1. Schema Validation (Handles basic types, required fields)
            # Ensure your schema defines 'password' as load_only=True
            validated_data = student_create_schema.load(data)

            # 2. Foreign Key Validation
            fk_errors = StudentService._validate_foreign_keys(
                validated_data, is_update=False
            )
            if fk_errors:
                return validation_error(False, fk_errors), 400

            # 3. Hash Password
            password_plain = validated_data.pop("password")  # Get plain password
            password_hash = generate_password_hash(password_plain)

            # 4. Create Instance & Commit
            # Use the explicit __init__ if it correctly maps validated_data fields
            # Or create instance and set attributes individually
            new_student = Student(
                email=validated_data["email"],
                password_hash=password_hash,  # Pass the generated hash
                level_id=validated_data["level_id"],
                parent_id=validated_data["parent_id"],
                first_name=validated_data.get("first_name"),
                last_name=validated_data.get("last_name"),
                docs_url=validated_data.get("docs_url"),
            )
            # Note: is_approved defaults to False in the model

            db.session.add(new_student)
            db.session.commit()

            # 5. Serialize & Respond (Excluding password)
            student_data = load_data(new_student)
            resp = message(True, "Student created successfully. Approval pending.")
            resp["student"] = student_data
            return resp, 201

        except ValidationError as err:
            current_app.logger.warning(
                f"Validation error creating student: {err.messages}"
            )
            return validation_error(False, err.messages), 400
        except IntegrityError as error:  # Catch duplicate email
            db.session.rollback()
            current_app.logger.warning(
                f"Integrity error creating student: {error}", exc_info=True
            )
            if "student_email_key" in str(
                error
            ) or "UNIQUE constraint failed: student.email" in str(error):
                return err_resp(
                    f"Email '{data.get('email')}' already exists.",
                    "duplicate_email",
                    409,
                )
            return internal_err_resp()
        except SQLAlchemyError as error:
            db.session.rollback()
            current_app.logger.error(
                f"Database error creating student: {error}", exc_info=True
            )
            return internal_err_resp()
        except Exception as error:
            db.session.rollback()
            current_app.logger.error(f"Error creating student: {error}", exc_info=True)
            return internal_err_resp()

    # --- UPDATE (Limited fields, Admin only for now) ---
    @staticmethod
    def update_student(student_id, data, current_user_role):
        """Update an existing student by ID (Admin only)"""
        # Authorization check (simplified - only admin can update for now)
        if current_user_role != "admin":
            return err_resp(
                "Forbidden: Only administrators can update student details.",
                "update_forbidden",
                403,
            )

        student = Student.query.get(student_id)
        if not student:
            return err_resp("Student not found!", "student_404", 404)

        if not data:
            return err_resp(
                "Request body cannot be empty for update.", "empty_update_data", 400
            )

        try:
            # 1. Schema Validation (Partial, excludes email/password/parent_id)
            validated_data = student_update_schema.load(data)

            # 2. Foreign Key Validation (only for keys being updated)
            fk_errors = StudentService._validate_foreign_keys(
                validated_data, is_update=True
            )
            if fk_errors:
                return validation_error(False, fk_errors), 400

            # 3. Update Instance Fields & Commit
            for key, value in validated_data.items():
                setattr(student, key, value)
            # Manually update updated_at if not handled by DB/SQLAlchemy event
            # student.updated_at = datetime.now(timezone.utc) # Already handled by onupdate

            db.session.add(student)
            db.session.commit()

            # 4. Serialize & Respond (Excluding password)
            student_data = load_data(student)
            resp = message(True, "Student updated successfully")
            resp["student"] = student_data
            return resp, 200

        except ValidationError as err:
            db.session.rollback()
            current_app.logger.warning(
                f"Validation error updating student {student_id}: {err.messages}"
            )
            return validation_error(False, err.messages), 400
        except (
            IntegrityError
        ) as error:  # Catch potential FK issues if validation missed something
            db.session.rollback()
            current_app.logger.warning(
                f"Database integrity error updating student {student_id}: {error}",
                exc_info=True,
            )
            return internal_err_resp()
        except SQLAlchemyError as error:
            db.session.rollback()
            current_app.logger.error(
                f"Database error updating student {student_id}: {error}", exc_info=True
            )
            return internal_err_resp()
        except Exception as error:
            db.session.rollback()
            current_app.logger.error(
                f"Error updating student {student_id}: {error}", exc_info=True
            )
            return internal_err_resp()

    # --- UPDATE Approval Status (Admin only) ---
    @staticmethod
    def update_approval_status(student_id, data, current_user_role):
        """Update a student's approval status (Admin only)"""
        if current_user_role != "admin":
            return err_resp(
                "Forbidden: Only administrators can change approval status.",
                "approval_forbidden",
                403,
            )

        student = Student.query.get(student_id)
        if not student:
            return err_resp("Student not found!", "student_404", 404)

        try:
            validated_data = student_approval_schema.load(data)
            student.is_approved = validated_data["is_approved"]
            # student.updated_at = datetime.now(timezone.utc) # Handled by onupdate

            db.session.add(student)
            db.session.commit()

            student_data = load_data(student)
            resp = message(
                True, f"Student approval status set to {student.is_approved}"
            )
            resp["student"] = student_data
            return resp, 200

        except ValidationError as err:
            db.session.rollback()
            current_app.logger.warning(
                f"Validation error updating approval for student {student_id}: {err.messages}"
            )
            return validation_error(False, err.messages), 400
        except Exception as error:
            db.session.rollback()
            current_app.logger.error(
                f"Error updating approval for student {student_id}: {error}",
                exc_info=True,
            )
            return internal_err_resp()

    # --- DELETE (Admin only) ---
    @staticmethod
    def delete_student(student_id, current_user_role):
        """Delete a student by ID (Admin only)"""
        if current_user_role != "admin":
            return err_resp(
                "Forbidden: Only administrators can delete students.",
                "delete_forbidden",
                403,
            )

        student = Student.query.get(student_id)
        if not student:
            return err_resp("Student not found!", "student_404", 404)

        try:
            # Absences and Notes have cascade delete-orphan. Check other dependencies if needed.
            db.session.delete(student)
            db.session.commit()
            return None, 204  # 204 No Content

        except SQLAlchemyError as error:
            db.session.rollback()
            current_app.logger.error(
                f"Database error deleting student {student_id}: {error}", exc_info=True
            )
            return err_resp(
                f"Could not delete student due to a database constraint or error.",
                "delete_error_db",
                500,
            )
        except Exception as error:
            db.session.rollback()
            current_app.logger.error(
                f"Error deleting student {student_id}: {error}", exc_info=True
            )
            return internal_err_resp()
