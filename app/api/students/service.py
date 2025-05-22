import json
from flask import current_app
from marshmallow import ValidationError
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
)
from datetime import timedelta

# Removed Marshmallow imports specific to local validation schema
from werkzeug.security import generate_password_hash
from itsdangerous import (
    URLSafeTimedSerializer,
    SignatureExpired,
    BadSignature,
)

# Import DB instance and models
from app import db
from app.models import Student, Level, Group, Parent

# Import shared utilities
from app.utils import (
    err_resp,
    message,
    internal_err_resp,
    validation_error,  # Keep for other methods if needed
)

# Import email sending utility
from app.service import send_email

# Import Redis client
from app.extensions import redis_client  # Assuming redis_client is in extensions

# Import serialization/deserialization utilities from local utils.py
# No AddChildSchema import needed
from .utils import dump_data, load_data


class StudentService:

    # --- Helper for Timed Serializer (Child Registration) ---
    @staticmethod
    def _get_child_registration_serializer():
        """Creates an instance of the timed serializer for child registration."""
        if (
            "SECRET_KEY" not in current_app.config
            or not current_app.config["SECRET_KEY"]
        ):
            current_app.logger.critical(
                "SECRET_KEY is not configured. Cannot generate secure tokens."
            )
            raise ValueError("Application is not configured with a SECRET_KEY.")
        salt = current_app.config.get(
            "CHILD_REGISTRATION_SERIALIZER_SALT", "child-registration-salt"
        )
        return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt=salt)

    # --- Helper for Foreign Key Validation ---
    @staticmethod
    def _validate_foreign_keys(data):
        """Check if related entities referenced in data exist. Returns dict of errors."""
        errors = {}
        # Handle both dict and object inputs
        level_id = (
            data.get("level_id")
            if isinstance(data, dict)
            else getattr(data, "level_id", None)
        )
        group_id = (
            data.get("group_id")
            if isinstance(data, dict)
            else getattr(data, "group_id", None)
        )
        parent_id = (
            data.get("parent_id")
            if isinstance(data, dict)
            else getattr(data, "parent_id", None)
        )

        if level_id is not None and not Level.query.get(level_id):
            errors["level_id"] = f"Level with ID {level_id} not found."
        if group_id is not None and not Group.query.get(group_id):
            errors["group_id"] = f"Group with ID {group_id} not found."
        if parent_id is not None and not Parent.query.get(parent_id):
            errors["parent_id"] = f"Parent with ID {parent_id} not found."
        return errors

    # --- Authorization/Scoping Check Helper ---
    @staticmethod
    def _can_user_access_student_record(
        student: Student, current_user_id: int, current_user_role: str
    ) -> bool:
        """
        Checks if the current user has permission to view/interact with THIS SPECIFIC student record.
        """
        if not student:
            return False
        # Admins and Teachers can access any record after passing the decorator
        if current_user_role in ["admin", "teacher"]:
            current_app.logger.debug(
                f"Record access granted: User {current_user_id} (Role: {current_user_role}) accessing student {student.id}."
            )
            return True
        # Students can access their own record
        if current_user_role == "student" and student.id == int(current_user_id):
            current_app.logger.debug(
                f"Record access granted: Student {current_user_id} accessing own profile."
            )
            return True
        # Parents can access their own child's record (assuming JWT user_id IS parent.id)
        if current_user_role == "parent" and student.parent_id == int(current_user_id):
            # Parents can access their own child's record
            current_app.logger.debug(
                f"Record access granted: Parent {current_user_id} accessing child student {student.id}."
            )
            return True

        current_app.logger.warning(
            f"Record access DENIED: User {current_user_id} (Role: {current_user_role}) attempted to access specific student record {student.id}."
        )
        return False

    # --- GET Single ---
    @staticmethod
    def get_student_data(
        student_id: int,
        current_user_id: int,
        current_user_role: str,
        current_user_parent_id=None,
    ):
        """Get student data by ID, with record-level access check"""
        student = Student.query.get(student_id)
        if not student:
            current_app.logger.info(f"Student with ID {student_id} not found.")
            return err_resp("Student not found!", "student_404", 404)

        # --- Record-Level Access Check ---
        if not StudentService._can_user_access_student_record(
            student, current_user_id, current_user_role
        ):
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
        current_user_role=None,
        current_user_id=None,
    ):
        """Get a list of students, filtered, paginated, with role-based data scoping"""
        page = page or 1
        per_page = per_page or 10

        try:
            query = Student.query

            # --- Role-Based Data Scoping ---
            if current_user_role == "parent":
                current_app.logger.debug(
                    f"Scoping student list for parent ID: {current_user_id}"
                )
                query = query.filter(
                    Student.parent_id
                    == int(current_user_id)  # type:ignore[reportGeneralTypeIssues]
                )  # type:ignore[reportGeneralTypeIssues]
            elif current_user_role == "student":
                current_app.logger.debug(
                    f"Scoping student list for student ID: {current_user_id}"
                )
                query = query.filter(
                    Student.id
                    == int(current_user_id)  # type:ignore[reportGeneralTypeIssues]
                )  # type:ignore[reportGeneralTypeIssues]
            # Admins/Teachers see all applicable records based on other filters

            # --- Apply Standard Filters ---
            filters_applied = {}
            if level_id is not None:
                filters_applied["level_id"] = level_id
                query = query.filter(
                    Student.level_id == level_id
                )  # type:ignore[reportGeneralTypeIssues]
            if group_id is not None:
                filters_applied["group_id"] = group_id
                query = query.filter(Student.group_id == group_id)
            # Only apply parent_id filter if user is admin/teacher (parent scope already applied)
            if parent_id is not None:
                if current_user_role in ["admin", "teacher"] or (
                    current_user_role == "parent"
                    and int(current_user_id)  # type:ignore[reportGeneralTypeIssues]
                    == parent_id  # type:ignore[reportGeneralTypeIssues]
                ):  # type:ignore[reportGeneralTypeIssues]
                    filters_applied["parent_id"] = parent_id
                    query = query.filter(
                        Student.parent_id == parent_id
                    )  # type:ignore[reportGeneralTypeIssues]
                else:
                    raise ValueError("Unauthorized: Cannot filter by parent_id")

            if is_approved is not None:
                filters_applied["is_approved"] = is_approved
                query = query.filter(Student.is_approved == is_approved)

            if filters_applied:
                current_app.logger.debug(
                    f"Applying student list filters: {filters_applied}"
                )

            query = query.order_by(Student.last_name).order_by(Student.first_name)

            current_app.logger.debug(
                f"Paginating students: page={page}, per_page={per_page}"
            )
            paginated_students = query.paginate(
                page=page, per_page=per_page, error_out=False
            )
            current_app.logger.debug(
                f"Paginated students items count: {len(paginated_students.items)}"
            )

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

            current_app.logger.debug(
                f"Successfully retrieved students page {page}. Total: {paginated_students.total}"
            )
            return resp, 200

        except Exception as error:
            log_msg = f"Error getting students list (role: {current_user_role})"
            # Rebuild filters_applied for logging safety
            filters_applied = {}
            if level_id is not None:
                filters_applied["level_id"] = level_id
            if group_id is not None:
                filters_applied["group_id"] = group_id
            if parent_id is not None and current_user_role in ["admin", "teacher"]:
                filters_applied["parent_id"] = parent_id
            if is_approved is not None:
                filters_applied["is_approved"] = is_approved
            if filters_applied:
                log_msg += f" with filters {filters_applied}"
            if page:
                log_msg += f", page {page}"
            current_app.logger.error(f"{log_msg}: {error}", exc_info=True)
            return internal_err_resp()

    # --- CREATE (Admin Direct Creation) ---
    @staticmethod
    def create_student(data: dict):
        """Create a new student directly (Admin)."""
        try:
            # Import schema here if not already imported at top level
            # from app.models.Schemas import StudentSchema

            # Using load_data utility which uses StudentSchema
            new_student = load_data(data)  # Assumes schema has load_instance=True

            current_app.logger.debug(
                f"Admin creating student directly. Validating FKs."
            )
            fk_errors = StudentService._validate_foreign_keys(
                new_student
            )  # Pass the instance
            if fk_errors:
                current_app.logger.warning(
                    f"Foreign key validation failed creating student: {fk_errors}. Data: {data}"
                )
                return validation_error(False, fk_errors), 400

            # Hash password (assuming 'password' field was loaded by schema)
            password_plain = data["password"]  # Get plain password from original data
            new_student.password = generate_password_hash(password_plain)
            current_app.logger.debug(
                f"Password hashed for student email: {new_student.email}"
            )

            # Admins might set approval directly or default it
            # new_student.is_approved = data.get('is_approved', False) # Example

            db.session.add(new_student)
            db.session.commit()
            current_app.logger.info(
                f"Student created successfully by admin with ID: {new_student.id}"
            )

            student_resp_data = dump_data(new_student)
            resp = message(True, "Student created successfully.")
            resp["student"] = student_resp_data
            return resp, 201

        except ValidationError as err:  # Catch validation errors from load_data
            db.session.rollback()
            current_app.logger.warning(
                f"Schema validation error creating student: {err.messages}. Data: {data}"
            )
            return validation_error(False, err.messages), 400
        except IntegrityError as error:
            db.session.rollback()
            current_app.logger.warning(
                f"Database integrity error creating student: {error}. Data: {data}",
                exc_info=True,
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
            current_app.logger.error(
                f"Unexpected error creating student: {error}. Data: {data}",
                exc_info=True,
            )
            return internal_err_resp()

    # --- ADD CHILD (Parent Initiated Registration) ---
    @staticmethod
    def add_child(data: dict, parent_id: int):
        """
        Initiates the registration process for a child by a parent.
        Relies on controller validation via @api.expect.
        Stores data in Redis, generates a token, and sends an email to the child.
        """
        try:
            # 1. Extract data (assuming validated by @api.expect in controller)
            student_email = data["email"]
            first_name = data["first_name"]
            last_name = data["last_name"]
            docs_url = data.get("docs_url")  # Optional

            current_app.logger.info(
                f"Parent {parent_id} initiating registration for child with email {student_email}"
            )
            current_app.logger.debug(
                f"Received add_child data: {data}"
            )  # Log received data

            # 2. Check if email is already in use by ANY student in DB
            existing_student = Student.query.filter_by(email=student_email).first()
            if existing_student:
                current_app.logger.warning(
                    f"Attempt to add child failed: Email '{student_email}' already exists for student ID {existing_student.id}."
                )
                return err_resp(
                    f"A student account with the email '{student_email}' already exists.",
                    "duplicate_email",
                    409,
                )

            # 3. Check if registration is already pending in Redis
            redis_key = f"child_reg_pending:{student_email}"
            if redis_client.exists(redis_key):
                ttl = redis_client.ttl(redis_key)
                current_app.logger.warning(
                    f"Attempt to add child failed: Registration already pending for email '{student_email}'. TTL: {ttl}s"
                )
                return err_resp(
                    f"A registration invitation has already been sent recently to {student_email}. Please check the inbox or wait.",
                    "registration_pending",
                    429,
                )

            # 4. Prepare Data for Redis
            redis_data = {
                "parent_id": parent_id,
                "email": student_email,
                "first_name": first_name,
                "last_name": last_name,
                "docs_url": docs_url,
            }
            redis_expiry_seconds = current_app.config.get(
                "CHILD_REGISTRATION_TOKEN_MAX_AGE_SECONDS", 7200
            )

            # 5. Store Data in Redis
            try:
                redis_client.set(
                    redis_key, json.dumps(redis_data), ex=redis_expiry_seconds
                )
                current_app.logger.debug(
                    f"Stored pending child registration data in Redis for {student_email} with expiry {redis_expiry_seconds}s."
                )
            except Exception as redis_err:
                current_app.logger.error(
                    f"Failed to store child registration data in Redis for {student_email}: {redis_err}",
                    exc_info=True,
                )
                return internal_err_resp()

            # 6. Generate Token
            serializer = StudentService._get_child_registration_serializer()
            token_payload = {"email": student_email}
            try:
                token = serializer.dumps(token_payload)
                current_app.logger.debug(
                    f"Generated child registration token for email {student_email}"
                )
            except Exception as e:
                current_app.logger.error(
                    f"Failed to serialize child registration token for {student_email}: {e}",
                    exc_info=True,
                )
                try:
                    redis_client.delete(redis_key)  # Cleanup Redis
                except:
                    pass
                return internal_err_resp()

            # 7. Construct Registration Link
            frontend_base = current_app.config.get("FRONTEND_BASE_URL")
            if not frontend_base:
                current_app.logger.error(
                    "FRONTEND_BASE_URL is not configured. Cannot create child registration link."
                )
                try:
                    redis_client.delete(redis_key)  # Cleanup Redis
                except:
                    pass
                return internal_err_resp()

            registration_path = current_app.config.get(
                "FRONTEND_CHILD_REGISTRATION_PATH", "/complete-child-registration"
            )
            registration_link = f"{frontend_base}{registration_path}?token={token}"

            # 8. Send Email to Child
            subject = "Complete Your Madrassati Registration"
            template = "email/password_reset"  # Use a generic template for registration
            expiration_minutes = int(redis_expiry_seconds / 60)
            parent_obj = Parent.query.get(parent_id)  # Fetch parent object
            parent_name = (
                parent_obj.first_name if parent_obj else "Your Parent"
            )  # Get name safely
            print(registration_link)
            context = {
                "registration_link": registration_link,
                "expiration_minutes": expiration_minutes,
                "parent_first_name": parent_name,
                "child_first_name": first_name,
            }

            email_sent = send_email(
                to_email=student_email,
                subject=subject,
                template_prefix=template,
                context=context,
            )

            if not email_sent:
                current_app.logger.error(
                    f"Failed to send child registration email to {student_email}. Data remains in Redis."
                )
                return (
                    message(
                        True,
                        "Registration invitation sent, but email delivery failed. Please contact support if the child doesn't receive it.",
                    ),
                    200,
                )

            # 9. Return Success Response to Parent
            current_app.logger.info(
                f"Child registration email successfully sent to {student_email} initiated by parent {parent_id}."
            )
            return (
                message(True, "Registration invitation email sent to the child."),
                200,
            )

        except ValueError as ve:  # Catch config errors
            current_app.logger.critical(
                f"Configuration error during add child process: {ve}"
            )
            return internal_err_resp()
        except KeyError as ke:  # Catch if expected keys are missing from data
            current_app.logger.error(
                f"Missing expected key in add_child data: {ke}. Data: {data}",
                exc_info=True,
            )
            return err_resp(f"Missing required field: {ke}", "missing_field", 400)
        except Exception as error:  # Catch all other errors
            current_app.logger.error(
                f"Unexpected error during add child process for parent {parent_id}, email {data.get('email')}: {error}",
                exc_info=True,
            )
            redis_key = f"child_reg_pending:{data.get('email')}"
            try:
                redis_client.delete(redis_key)  # Attempt cleanup
            except:
                pass
            return internal_err_resp()

    # -----------------------------------------------------
    @staticmethod
    def complete_child_registration(data: dict):
        """
        Completes child registration using token, sets password, creates DB entry,
        cleans up Redis, and generates login tokens.
        """
        token = data.get("token")
        password = data.get("password")
        redis_key = None  # Initialize for potential cleanup

        try:
            # 1. Validate Token & Extract Email
            serializer = StudentService._get_child_registration_serializer()
            max_age = current_app.config.get(
                "CHILD_REGISTRATION_TOKEN_MAX_AGE_SECONDS", 7200
            )
            try:
                if not token:
                    current_app.logger.warning(f"Missing token in request data.")
                    return err_resp("Token is required.", "token_missing", 400)
                token_payload = serializer.loads(token, max_age=max_age)
                student_email = token_payload.get("email")
                if not student_email:
                    raise BadSignature("Token payload missing email.")
                redis_key = (
                    f"child_reg_pending:{student_email}"  # Define key here for cleanup
                )
                current_app.logger.debug(
                    f"Child registration token validated for email: {student_email}"
                )
            except SignatureExpired:
                current_app.logger.warning(
                    f"Expired child registration token received."
                )
                return err_resp("Registration link has expired.", "token_expired", 400)
            except BadSignature as e:
                current_app.logger.warning(
                    f"Invalid child registration token received: {e}"
                )
                return err_resp("Invalid registration link.", "token_invalid", 400)

            # 2. Retrieve Data from Redis
            try:
                redis_data_json = redis_client.get(redis_key)
                if not redis_data_json:
                    current_app.logger.warning(
                        f"No pending registration data found in Redis for key: {redis_key} (likely expired/completed)."
                    )
                    # Use 404 Not Found as the resource (pending registration) is gone
                    return err_resp(
                        "Registration data not found. It may have expired or already been used.",
                        "reg_data_not_found",
                        404,
                    )
                redis_data = json.loads(redis_data_json)
                current_app.logger.debug(
                    f"Retrieved pending registration data from Redis for {student_email}"
                )
            except json.JSONDecodeError:
                current_app.logger.error(
                    f"Failed to decode JSON registration data from Redis for key: {redis_key}"
                )
                return internal_err_resp()  # Internal state error
            except Exception as redis_err:
                current_app.logger.error(
                    f"Failed to retrieve child registration data from Redis for {redis_key}: {redis_err}",
                    exc_info=True,
                )
                return internal_err_resp()

            # Extract required data (handle potential missing keys in stored data)
            try:
                data = {}
                data["email"] = student_email
                data["user_type"] = "student"
                data["first_name"] = redis_data["first_name"]
                data["last_name"] = redis_data["last_name"]
                data["parent_id"] = redis_data["parent_id"]
                data["docs_url"] = redis_data.get("docs_url")  # Optional
                data["is_approved"] = False  # Default to unapproved
            except KeyError as ke:
                current_app.logger.error(
                    f"Missing expected key in Redis data for {redis_key}: {ke}"
                )
                return internal_err_resp()  # Internal state error

            # 3. Check for Existing Student (Race Condition)
            existing_student = Student.query.filter_by(email=student_email).first()
            if existing_student:
                current_app.logger.warning(
                    f"Conflict during child registration completion: Email '{student_email}' already exists for student ID {existing_student.id}."
                )
                # Attempt to clean up Redis key if found during race condition check
                try:
                    redis_client.delete(redis_key)
                except:
                    pass
                return err_resp(
                    f"A student account with the email '{student_email}' was created after the invitation was sent.",
                    "duplicate_email_concurrent",
                    409,
                )

            # 4. Hash Password
            # Basic length validation done by DTO/expect
            hashed_password = generate_password_hash(str(password))
            data["password"] = hashed_password
            current_app.logger.debug(
                f"Password hashed for completing registration for {student_email}"
            )

            # 5. Create Student Record in DB

            new_student = load_data(data)  # Validate against schema
            db.session.add(new_student)
            db.session.commit()
            current_app.logger.info(
                f"Student record created successfully upon registration completion for email {student_email}, ID: {new_student.id}"
            )

            # 6. Delete Redis Data (Cleanup) - After successful commit
            try:
                deleted_count = redis_client.delete(redis_key)
                if deleted_count > 0:
                    current_app.logger.debug(
                        f"Successfully deleted pending registration data from Redis for key: {redis_key}"
                    )
                else:
                    current_app.logger.warning(
                        f"Attempted to delete Redis key {redis_key} after registration, but key was not found."
                    )
            except Exception as redis_del_err:
                # Log error but don't fail the request, registration is complete
                current_app.logger.error(
                    f"Failed to delete Redis key {redis_key} after successful registration: {redis_del_err}",
                    exc_info=True,
                )

            # 7. Generate Login Tokens for the new student
            identity = str(new_student.id)  # Use student's new ID
            role = "student"  # Hardcode role
            additional_claims = {"role": role}

            access_token = create_access_token(
                identity=identity,
                additional_claims=additional_claims,
                expires_delta=timedelta(
                    seconds=current_app.config["ACCESS_EXPIRES_SECONDS"]
                ),
            )
            refresh_token = create_refresh_token(
                identity=identity,
                additional_claims=additional_claims,
                expires_delta=timedelta(
                    days=current_app.config["REFRESH_EXPIRES_DAYS"]
                ),
            )
            current_app.logger.info(
                f"Generated login tokens for newly registered student {new_student.id}"
            )

            # 8. Prepare Success Response (including tokens and user data)
            student_resp_data = dump_data(new_student)  # Serialize student data
            resp = message(True, "Registration complete. Welcome!")
            resp["access_token"] = access_token
            resp["refresh_token"] = refresh_token
            resp["user"] = (
                student_resp_data  # Use 'user' key consistent with auth responses
            )
            return resp, 201  # 201 Created

        except ValueError as ve:  # Catch config errors
            current_app.logger.critical(
                f"Configuration error during complete child registration: {ve}"
            )
            return internal_err_resp()
        except (
            IntegrityError
        ) as error:  # Catch potential DB unique constraint issues (should be caught by earlier check)
            db.session.rollback()
            current_app.logger.error(
                f"Database integrity error during complete child registration: {error}",
                exc_info=True,
            )
            return internal_err_resp()  # Unexpected if pre-check worked
        except SQLAlchemyError as error:
            db.session.rollback()
            current_app.logger.error(
                f"Database error during complete child registration: {error}",
                exc_info=True,
            )
            return internal_err_resp()
        except Exception as error:
            db.session.rollback()
            current_app.logger.error(
                f"Unexpected error during complete child registration: {error}",
                exc_info=True,
            )
            # Attempt cleanup if Redis key might exist
            if redis_key:
                try:
                    redis_client.delete(redis_key)
                except:
                    pass
            return internal_err_resp()

    # --- UPDATE (Limited fields, Admin) ---
    @staticmethod
    def update_student(student_id: int, data: dict):
        """Update an existing student by ID (Admin)."""
        student = Student.query.get(student_id)
        if not student:
            current_app.logger.info(
                f"Attempted to update non-existent student ID: {student_id}"
            )
            return err_resp("Student not found!", "student_404", 404)

        if not data:
            current_app.logger.warning(
                f"Attempted update for student {student_id} with empty data."
            )
            return err_resp(
                "Request body cannot be empty for update.", "empty_update_data", 400
            )

        try:
            # Validate FKs *before* applying changes via load_data
            fk_errors = StudentService._validate_foreign_keys(data)
            if fk_errors:
                current_app.logger.warning(
                    f"Foreign key validation failed updating student {student_id}: {fk_errors}. Data: {data}"
                )
                return validation_error(False, fk_errors), 400

            # Load data into the existing instance
            updated_student = load_data(data, partial=True, instance=student)
            current_app.logger.debug(
                f"Student data validated by schema for update. Committing changes for ID: {student_id}"
            )

            db.session.commit()
            current_app.logger.info(
                f"Student updated successfully for ID: {student_id}"
            )

            student_resp_data = dump_data(updated_student)
            resp = message(True, "Student updated successfully")
            resp["student"] = student_resp_data
            return resp, 200

        except ValidationError as err:  # Catch validation errors from load_data
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
                f"Database error updating student {student_id}: {error}. Data: {data}",
                exc_info=True,
            )
            return internal_err_resp()
        except Exception as error:
            db.session.rollback()
            current_app.logger.error(
                f"Unexpected error updating student {student_id}: {error}. Data: {data}",
                exc_info=True,
            )
            return internal_err_resp()

    # --- UPDATE Approval Status (Admin) ---
    @staticmethod
    def update_approval_status(student_id: int, data: dict):
        """Update a student's approval status (Admin)."""
        student = Student.query.get(student_id)
        if not student:
            current_app.logger.info(
                f"Attempted to update approval for non-existent student ID: {student_id}"
            )
            return err_resp("Student not found!", "student_404", 404)

        try:
            # Manual validation for single field
            if "is_approved" not in data or not isinstance(data["is_approved"], bool):
                # Use validation_error helper if available and appropriate
                # return validation_error(False, {'is_approved': ['Missing or invalid data.']}), 400
                # Or simpler err_resp
                return err_resp(
                    "Missing or invalid 'is_approved' field.", "validation_error", 400
                )

            new_status = data["is_approved"]
            if student.is_approved != new_status:
                student.is_approved = new_status
                current_app.logger.debug(
                    f"Setting student {student_id} approval status to: {student.is_approved}"
                )
                db.session.add(student)  # Add to session before commit
                db.session.commit()
                current_app.logger.info(
                    f"Student approval status updated successfully for ID: {student_id}"
                )
            else:
                current_app.logger.info(
                    f"Student {student_id} approval status already {new_status}. No update needed."
                )

            student_resp_data = dump_data(student)
            resp = message(
                True, f"Student approval status set to {student.is_approved}"
            )
            resp["student"] = student_resp_data
            return resp, 200

        # Removed ValidationError catch as manual check is done
        except SQLAlchemyError as error:
            db.session.rollback()
            current_app.logger.error(
                f"Database error updating approval for student {student_id}: {error}. Data: {data}",
                exc_info=True,
            )
            return internal_err_resp()
        except Exception as error:
            db.session.rollback()
            current_app.logger.error(
                f"Unexpected error updating approval for student {student_id}: {error}. Data: {data}",
                exc_info=True,
            )
            return internal_err_resp()

    # --- DELETE (Admin) ---
    @staticmethod
    def delete_student(student_id: int):
        """Delete a student by ID (Admin)."""
        student = Student.query.get(student_id)
        if not student:
            current_app.logger.info(
                f"Attempted to delete non-existent student ID: {student_id}"
            )
            return err_resp("Student not found!", "student_404", 404)

        try:
            current_app.logger.warning(
                f"Admin attempting to delete student ID: {student_id}"
            )
            db.session.delete(student)
            db.session.commit()
            current_app.logger.info(f"Student deleted successfully: ID {student_id}")
            return None, 204

        except SQLAlchemyError as error:
            db.session.rollback()
            current_app.logger.error(
                f"Database error deleting student {student_id}: {error}", exc_info=True
            )
            # Check for specific constraint violation
            if "FOREIGN KEY constraint" in str(error):
                return err_resp(
                    "Cannot delete student. They may have associated records (absences, notes, etc.).",
                    "delete_conflict",
                    409,
                )
            return err_resp(
                f"Could not delete student due to a database error.",
                "delete_error_db",
                500,
            )
        except Exception as error:
            db.session.rollback()
            current_app.logger.error(
                f"Unexpected error deleting student {student_id}: {error}",
                exc_info=True,
            )
            return internal_err_resp()
