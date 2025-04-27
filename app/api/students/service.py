from flask import current_app
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from marshmallow import ValidationError
from werkzeug.security import generate_password_hash

# Import DB instance and models
from app import db
from app.models import Student, Level, Group, Parent

# Import shared utilities
from app.utils import (
    err_resp,
    message,
    internal_err_resp,
    validation_error,
)

# Import serialization/deserialization utilities from local utils.py
from .utils import dump_data, load_data


class StudentService:

    # --- Helper for Foreign Key Validation ---
    @staticmethod
    def _validate_foreign_keys(data: dict):
        """Check if related entities referenced in data exist. Returns dict of errors."""
        errors = {}
        if data.get("level_id") is not None and not Level.query.get(data["level_id"]):
            errors["level_id"] = f"Level with ID {data['level_id']} not found."
        if data.get("group_id") is not None and not Group.query.get(data["group_id"]):
            errors["group_id"] = f"Group with ID {data['group_id']} not found."
        if data.get("parent_id") is not None and not Parent.query.get(data["parent_id"]):
            errors["parent_id"] = f"Parent with ID {data['parent_id']} not found."
        return errors

    # --- Authorization/Scoping Check Helper (Refined) ---
    @staticmethod
    def _can_user_access_student_record(student: Student, current_user_id: int, current_user_role: str) -> bool:
        """
        Checks if the current user has permission to view/interact with THIS SPECIFIC student record.
        This is different from the role check for the endpoint itself.
        Assumes the user has already passed the @roles_required decorator for the endpoint.
        """
        if not student:
             return False
        # Admins and Teachers can access any record after passing the decorator
        if current_user_role in ["admin", "teacher"]:
            current_app.logger.debug(f"Record access granted: User {current_user_id} (Role: {current_user_role}) accessing student {student.id}.")
            return True
        # Students can access their own record
        if current_user_role == "student" and student.id == current_user_id:
            current_app.logger.debug(f"Record access granted: Student {current_user_id} accessing own profile.")
            return True
        # Parents can access their own child's record (assuming JWT user_id IS parent.id)
        if current_user_role == "parent" and student.parent_id == current_user_id:
            current_app.logger.debug(f"Record access granted: Parent {current_user_id} accessing child student {student.id}.")
            return True

        current_app.logger.warning(f"Record access DENIED: User {current_user_id} (Role: {current_user_role}) attempted to access specific student record {student.id}.")
        return False

    # --- GET Single ---
    @staticmethod
    def get_student_data(student_id: int, current_user_id: int, current_user_role: str, current_user_parent_id=None): # Keep role/id for record-level check
        """Get student data by ID, with record-level access check"""
        student = Student.query.get(student_id)
        if not student:
            current_app.logger.info(f"Student with ID {student_id} not found.")
            return err_resp("Student not found!", "student_404", 404)

        # --- Record-Level Access Check ---
        # Can this specific user (parent/student) view THIS student's record?
        # Admins/Teachers skip this detailed check as they passed the decorator.
        if not StudentService._can_user_access_student_record(student, current_user_id, current_user_role):
             return err_resp(
                 "Forbidden: You do not have permission to access this specific student's record.",
                 "record_access_denied",
                 403,
             )

        try:
            student_data = dump_data(student)
            resp = message(True, "Student data sent successfully")
            resp["student"] = student_data
            current_app.logger.debug(f"Successfully retrieved student ID {student_id}")
            return resp, 200
        except Exception as error:
            current_app.logger.error(
                f"Error serializing student data for ID {student_id}: {error}",
                exc_info=True,
            )
            return internal_err_resp()

    # --- GET List with Filters and Pagination ---
    @staticmethod
    def get_all_students(
        level_id=None,
        group_id=None,
        parent_id=None,
        is_approved=None,
        page=None,
        per_page=None,
        current_user_role=None, # Still needed for scoping the query
        current_user_id=None,   # Still needed for scoping the query
    ):
        """Get a list of students, filtered, paginated, with role-based data scoping"""
        page = page or 1
        per_page = per_page or 10

        try:
            query = Student.query

            # --- Role-Based Data Scoping ---
            # Decorator ensures role is allowed, here we filter *which* records they see
            if current_user_role == "parent":
                current_app.logger.debug(f"Scoping student list for parent ID: {current_user_id}")
                query = query.filter(Student.parent_id == current_user_id) # type:ignore[reportGeneralTypeIssues]
            elif current_user_role == "student":
                current_app.logger.debug(f"Scoping student list for student ID: {current_user_id}")
                query = query.filter(Student.id == current_user_id)
            # Admins/Teachers see all applicable records based on other filters

            # --- Apply Standard Filters ---
            filters_applied = {}
            if level_id is not None:
                filters_applied['level_id'] = level_id
                query = query.filter(Student.level_id == level_id) #type:ignore[reportGeneralTypeIssues]
            if group_id is not None:
                filters_applied['group_id'] = group_id
                query = query.filter(Student.group_id == group_id)
            # Only apply parent_id filter if user is admin/teacher (parent scope already applied)
            if parent_id is not None and current_user_role in ["admin", "teacher"]:
                filters_applied['parent_id'] = parent_id
                query = query.filter(Student.parent_id == parent_id) # type:ignore[reportGeneralTypeIssues]
            if is_approved is not None:
                filters_applied['is_approved'] = is_approved
                query = query.filter(Student.is_approved == is_approved)

            if filters_applied:
                 current_app.logger.debug(f"Applying student list filters: {filters_applied}")

            query = query.order_by(Student.last_name).order_by(Student.first_name)

            current_app.logger.debug(f"Paginating students: page={page}, per_page={per_page}")
            paginated_students = query.paginate(page=page, per_page=per_page, error_out=False)
            current_app.logger.debug(f"Paginated students items count: {len(paginated_students.items)}")

            students_data = dump_data(paginated_students.items, many=True)

            current_app.logger.debug(f"Serialized {len(students_data)} students")
            resp = message(True, "Students list retrieved successfully")
            resp["students"] = students_data
            resp["total"] = paginated_students.total
            resp["pages"] = paginated_students.pages
            resp["current_page"] = paginated_students.page
            resp["per_page"] = paginated_students.per_page
            resp["has_next"] = paginated_students.has_next
            resp["has_prev"] = paginated_students.has_prev

            current_app.logger.debug(f"Successfully retrieved students page {page}. Total: {paginated_students.total}")
            return resp, 200

        except Exception as error:
            log_msg = f"Error getting students list (role: {current_user_role})"
            filters_applied = {}
            if filters_applied: log_msg += f" with filters {filters_applied}"
            if page: log_msg += f", page {page}"
            current_app.logger.error(f"{log_msg}: {error}", exc_info=True)
            return internal_err_resp()

    # --- CREATE ---
    @staticmethod
    def create_student(data: dict):
        """Create a new student. Assumes @roles_required('admin') handled authorization."""
        # No role check needed here - decorator handles it.
        try:
            # Using temporary manual schema load as discussed before
            from app.models.Schemas import StudentSchema
            student_create_schema = StudentSchema()
            validated_data = student_create_schema.load(data)
            current_app.logger.debug(f"Student data validated by schema. Proceeding with FK checks.")

            fk_errors = StudentService._validate_foreign_keys(validated_data)
            if fk_errors:
                current_app.logger.warning(f"Foreign key validation failed creating student: {fk_errors}. Data: {data}")
                return validation_error(False, fk_errors), 400

            password_plain = validated_data.pop("password")
            password_hash = generate_password_hash(password_plain)
            current_app.logger.debug(f"Password hashed for student email: {validated_data.get('email')}")

            new_student = Student(
                password_hash=password_hash,
                **validated_data
            )

            db.session.add(new_student)
            db.session.commit()
            current_app.logger.info(f"Student created successfully with ID: {new_student.id}")

            student_resp_data = dump_data(new_student)
            resp = message(True, "Student created successfully. Approval pending.")
            resp["student"] = student_resp_data
            return resp, 201

        except ValidationError as err:
            db.session.rollback()
            current_app.logger.warning(
                f"Schema validation error creating student: {err.messages}. Data: {data}"
            )
            return validation_error(False, err.messages), 400
        except IntegrityError as error:
            db.session.rollback()
            current_app.logger.warning(
                f"Database integrity error creating student: {error}. Data: {data}", exc_info=True
            )
            if "student_email_key" in str(
                error.orig
            ) or "UNIQUE constraint failed: student.email" in str(error.orig):
                return err_resp(
                    f"Email '{data.get('email')}' already exists.",
                    "duplicate_email",
                    409,
                )
            return internal_err_resp()
        except SQLAlchemyError as error:
            db.session.rollback()
            current_app.logger.error(
                f"Database error creating student: {error}. Data: {data}", exc_info=True
            )
            return internal_err_resp()
        except Exception as error:
            db.session.rollback()
            current_app.logger.error(f"Unexpected error creating student: {error}. Data: {data}", exc_info=True)
            return internal_err_resp()

    # --- UPDATE (Limited fields) ---
    @staticmethod
    def update_student(student_id: int, data: dict): # Removed current_user_role
        """Update an existing student by ID. Assumes @roles_required('admin') handled authorization."""
        # No role check needed here - decorator handles it.

        student = Student.query.get(student_id)
        if not student:
            current_app.logger.info(f"Attempted to update non-existent student ID: {student_id}")
            return err_resp("Student not found!", "student_404", 404)

        if not data:
            current_app.logger.warning(f"Attempted update for student {student_id} with empty data.")
            return err_resp(
                "Request body cannot be empty for update.", "empty_update_data", 400
            )

        try:
            updated_student = load_data(data, partial=True, instance=student)
            current_app.logger.debug(f"Student data validated by schema for update. Proceeding with FK checks for ID: {student_id}")

            fk_errors = StudentService._validate_foreign_keys(data)
            if fk_errors:
                current_app.logger.warning(f"Foreign key validation failed updating student {student_id}: {fk_errors}. Data: {data}")
                return validation_error(False, fk_errors), 400

            db.session.commit()
            current_app.logger.info(f"Student updated successfully for ID: {student_id}")

            student_resp_data = dump_data(updated_student)
            resp = message(True, "Student updated successfully")
            resp["student"] = student_resp_data
            return resp, 200

        except ValidationError as err:
            db.session.rollback()
            current_app.logger.warning(
                f"Schema validation error updating student {student_id}: {err.messages}. Data: {data}"
            )
            return validation_error(False, err.messages), 400
        except IntegrityError as error:
            db.session.rollback()
            current_app.logger.warning(
                f"Database integrity error updating student {student_id}: {error}. Data: {data}",
                exc_info=True,
            )
            return internal_err_resp()
        except SQLAlchemyError as error:
            db.session.rollback()
            current_app.logger.error(
                f"Database error updating student {student_id}: {error}. Data: {data}", exc_info=True
            )
            return internal_err_resp()
        except Exception as error:
            db.session.rollback()
            current_app.logger.error(
                f"Unexpected error updating student {student_id}: {error}. Data: {data}", exc_info=True
            )
            return internal_err_resp()

    # --- UPDATE Approval Status ---
    @staticmethod
    def update_approval_status(student_id: int, data: dict): # Removed current_user_role
        """Update a student's approval status. Assumes @roles_required('admin') handled authorization."""
        # No role check needed here - decorator handles it.

        student = Student.query.get(student_id)
        if not student:
            current_app.logger.info(f"Attempted to update approval for non-existent student ID: {student_id}")
            return err_resp("Student not found!", "student_404", 404)

        try:
            # Using temporary manual schema load
            from app.models.Schemas import StudentSchema
            student_approval_schema = StudentSchema(only=("is_approved",), partial=True)
            validated_data = student_approval_schema.load(data)

            student.is_approved = validated_data["is_approved"]
            current_app.logger.debug(f"Setting student {student_id} approval status to: {student.is_approved}")

            db.session.add(student)
            db.session.commit()
            current_app.logger.info(f"Student approval status updated successfully for ID: {student_id}")

            student_resp_data = dump_data(student)
            resp = message(
                True, f"Student approval status set to {student.is_approved}"
            )
            resp["student"] = student_resp_data
            return resp, 200

        except ValidationError as err:
            db.session.rollback()
            current_app.logger.warning(
                f"Validation error updating approval for student {student_id}: {err.messages}. Data: {data}"
            )
            return validation_error(False, err.messages), 400
        except SQLAlchemyError as error:
             db.session.rollback()
             current_app.logger.error(
                 f"Database error updating approval for student {student_id}: {error}. Data: {data}", exc_info=True
             )
             return internal_err_resp()
        except Exception as error:
            db.session.rollback()
            current_app.logger.error(
                f"Unexpected error updating approval for student {student_id}: {error}. Data: {data}",
                exc_info=True,
            )
            return internal_err_resp()

    # --- DELETE ---
    @staticmethod
    def delete_student(student_id: int): # Removed current_user_role
        """Delete a student by ID. Assumes @roles_required('admin') handled authorization."""
        # No role check needed here - decorator handles it.

        student = Student.query.get(student_id)
        if not student:
            current_app.logger.info(f"Attempted to delete non-existent student ID: {student_id}")
            return err_resp("Student not found!", "student_404", 404)

        try:
            current_app.logger.debug(f"Deleting student ID: {student_id}")
            db.session.delete(student)
            db.session.commit()
            current_app.logger.info(f"Student deleted successfully: ID {student_id}")
            return None, 204

        except SQLAlchemyError as error:
            db.session.rollback()
            current_app.logger.error(
                f"Database error deleting student {student_id}: {error}", exc_info=True
            )
            return err_resp(
                f"Could not delete student due to a database error.",
                "delete_error_db",
                500,
            )
        except Exception as error:
            db.session.rollback()
            current_app.logger.error(
                f"Unexpected error deleting student {student_id}: {error}", exc_info=True
            )
            return internal_err_resp()

