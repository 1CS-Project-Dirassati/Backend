import json
from flask import current_app
from marshmallow import ValidationError
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
)
from datetime import datetime, timedelta  # Ensure datetime is imported for Fee creation

from werkzeug.security import generate_password_hash
from itsdangerous import (
    URLSafeTimedSerializer,
    SignatureExpired,
    BadSignature,
)

from app import db
from app.models import Student, Level, Group, Parent, Fee, FeeStatus

# Assuming FeeStatus is an Enum correctly defined in app.models

from app.utils import (
    err_resp,
    message,
    internal_err_resp,
    validation_error,
)
from app.service import send_email
from app.extensions import redis_client
from .utils import dump_data, load_data


class StudentService:

    @staticmethod
    def _get_child_registration_serializer():
        if (
            "SECRET_KEY" not in current_app.config
            or not current_app.config["SECRET_KEY"]
        ):
            current_app.logger.critical("SECRET_KEY is not configured.")
            raise ValueError("Application is not configured with a SECRET_KEY.")
        salt = current_app.config.get(
            "CHILD_REGISTRATION_SERIALIZER_SALT", "child-registration-salt"
        )
        return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt=salt)

    @staticmethod
    def _validate_foreign_keys(data):
        errors = {}
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
        if (
            group_id is not None and group_id != "" and not Group.query.get(group_id)
        ):  # Allow group_id to be None or empty string for unassigning
            errors["group_id"] = f"Group with ID {group_id} not found."

        if parent_id is not None:
            parent = Parent.query.get(parent_id)
            if not parent:
                errors["parent_id"] = f"Parent with ID {parent_id} not found."
            elif parent.archived:  # Check if parent is archived
                errors["parent_id"] = (
                    f"Parent with ID {parent_id} is archived and cannot be assigned."
                )
        return errors

    @staticmethod
    def _can_user_access_student_record(
        student: Student,
        current_user_id: int,
        current_user_role: str,
        allow_archived_view_for_admin=False,
    ) -> bool:
        if not student:
            return False

        if student.archived and not (
            current_user_role == "admin" and allow_archived_view_for_admin
        ):
            return False

        if current_user_role in ["admin", "teacher"]:
            return True
        if current_user_role == "student" and student.id == int(current_user_id):
            return True
        if current_user_role == "parent" and student.parent_id == int(current_user_id):
            return True

        current_app.logger.warning(
            f"Record access DENIED: User {current_user_id} (Role: {current_user_role}) to student {student.id}."
        )
        return False

    @staticmethod
    def get_student_data(student_id: int, current_user_id: int, current_user_role: str):
        student = Student.query.get(student_id)
        allow_archived_view = current_user_role == "admin"

        if not student:
            return err_resp("Student not found!", "student_404", 404)

        if not StudentService._can_user_access_student_record(
            student,
            current_user_id,
            current_user_role,
            allow_archived_view_for_admin=allow_archived_view,
        ):
            return err_resp(
                "Forbidden or Student not found.",
                "access_denied_or_not_found",
                403 if student.archived else 404,
            )

        try:
            student_data = dump_data(student)
            resp = message(True, "Student data sent successfully")
            resp["student"] = student_data
            return resp, 200
        except Exception as error:
            current_app.logger.error(
                f"Error serializing student {student_id}: {error}", exc_info=True
            )
            return internal_err_resp()

    @staticmethod
    def get_all_students(
        level_id=None,
        group_id=None,
        parent_id=None,
        is_approved=None,
        archived=0,
        page=None,
        per_page=None,
        current_user_role=None,
        current_user_id=None,
    ):
        page = page or 1
        per_page = per_page or 10
        archived_bool = bool(archived)

        try:
            query = Student.query
            filters_applied = {"archived": archived_bool}

            if current_user_role == "parent":
                if not current_user_id:
                    return err_resp(
                        "Parent ID is required for parent role.",
                        "parent_id_required",
                        400,
                    )
                query = query.filter(Student.parent_id == int(current_user_id))
            elif current_user_role == "student":
                if not current_user_id:
                    return err_resp(
                        "Student ID is required for student role.",
                        "student_id_required",
                        400,
                    )
                query = query.filter(Student.id == int(current_user_id))

            query = query.filter(Student.archived == archived_bool)

            if level_id is not None:
                filters_applied["level_id"] = level_id
                query = query.filter(Student.level_id == level_id)
            if group_id is not None:
                filters_applied["group_id"] = group_id
                query = query.filter(Student.group_id == group_id)

            if parent_id is not None:
                if not current_user_id:
                    return err_resp(
                        "Parent ID is required for filtering by parent.",
                        "parent_id_required_filter",
                        400,
                    )
                if current_user_role == "parent" and int(current_user_id) != parent_id:
                    current_app.logger.warning(
                        f"Parent {current_user_id} trying to filter by other parent_id {parent_id}. Query will yield no results for this parent."
                    )
                    query = query.filter(
                        False
                    )  # Effectively make query return nothing for this parent
                elif current_user_role in ["admin", "teacher"] or (
                    current_user_role == "parent" and int(current_user_id) == parent_id
                ):
                    filters_applied["parent_id"] = parent_id
                    query = query.filter(Student.parent_id == parent_id)

            if is_approved is not None:
                filters_applied["is_approved"] = bool(is_approved)
                query = query.filter(Student.is_approved == bool(is_approved))

            current_app.logger.debug(
                f"Applying student list filters: {filters_applied}"
            )
            query = query.order_by(Student.last_name, Student.first_name)
            paginated_students = query.paginate(
                page=page, per_page=per_page, error_out=False
            )

            students_data = dump_data(paginated_students.items, many=True)
            resp = message(True, "Students list retrieved successfully")
            resp.update(
                {
                    "students": students_data,
                    "total": paginated_students.total,
                    "pages": paginated_students.pages,
                    "current_page": paginated_students.page,
                    "per_page": paginated_students.per_page,
                    "has_next": paginated_students.has_next,
                    "has_prev": paginated_students.has_prev,
                }
            )
            return resp, 200
        except Exception as error:
            current_app.logger.error(
                f"Error getting students list: {error}", exc_info=True
            )
            return internal_err_resp()

    @staticmethod
    def create_student(data: dict):
        try:
            existing_student = Student.query.filter_by(email=data.get("email")).first()
            if existing_student:
                status = "archived" if existing_student.archived else "active"
                return err_resp(
                    f"Email '{data.get('email')}' already exists for an {status} student.",
                    "duplicate_email",
                    409,
                )

            fk_errors = StudentService._validate_foreign_keys(data)
            if fk_errors:
                return validation_error(False, fk_errors), 400

            new_student = load_data(data)
            new_student.archived = False
            new_student.password = generate_password_hash(data["password"])

            db.session.add(new_student)
            db.session.commit()
            student_resp_data = dump_data(new_student)
            return {
                "status": True,
                "message": "Student created successfully.",
                "student": student_resp_data,
            }, 201
        except ValidationError as err:
            db.session.rollback()
            return validation_error(False, err.messages), 400
        except Exception as error:
            db.session.rollback()
            current_app.logger.error(f"Error creating student: {error}", exc_info=True)
            return internal_err_resp()

    @staticmethod
    def add_child(data: dict, parent_id: int):
        try:
            student_email = data["email"]
            parent = Parent.query.get(parent_id)
            if not parent or parent.archived:
                return err_resp(
                    "Parent account not found or is archived.", "parent_not_active", 403
                )

            existing_student = Student.query.filter_by(email=student_email).first()
            if existing_student:
                status = "archived" if existing_student.archived else "active"
                return err_resp(
                    f"A student account with the email '{student_email}' already exists ({status}).",
                    "duplicate_email",
                    409,
                )

            redis_key = f"child_reg_pending:{student_email}"
            if redis_client.exists(redis_key):
                return err_resp(
                    "Registration invitation already sent recently.",
                    "registration_pending",
                    429,
                )

            redis_data = {
                "parent_id": parent_id,
                "email": student_email,
                "first_name": data["first_name"],
                "last_name": data["last_name"],
                "docs_url": data.get("docs_url"),
            }
            redis_expiry = current_app.config.get(
                "CHILD_REGISTRATION_TOKEN_MAX_AGE_SECONDS", 7200
            )
            redis_client.set(redis_key, json.dumps(redis_data), ex=redis_expiry)

            serializer = StudentService._get_child_registration_serializer()
            token = serializer.dumps({"email": student_email})

            reg_link = f"{current_app.config.get('FRONTEND_BASE_URL')}{current_app.config.get('FRONTEND_CHILD_REGISTRATION_PATH', '/complete-child-registration')}?token={token}"

            email_context = {
                "reset_link": reg_link,
                "expiration_minutes": int(redis_expiry / 60),
                "parent_first_name": parent.first_name,
                "child_first_name": data["first_name"],
            }
            send_email(
                to_email=student_email,
                subject="Complete Your Madrassati Registration",
                template_prefix="email/password_reset",
                context=email_context,
            )

            return (
                message(True, "Registration invitation email sent to the child."),
                200,
            )
        except Exception as error:
            current_app.logger.error(f"Error in add_child: {error}", exc_info=True)
            return internal_err_resp()

    @staticmethod
    def complete_child_registration(data: dict):
        token = data.get("token")
        password = data.get("password")
        redis_key = None
        try:
            serializer = StudentService._get_child_registration_serializer()
            if not token:
                return err_resp("Token is required.", "token_required", 400)

            token_payload = serializer.loads(
                token,
                max_age=current_app.config.get(
                    "CHILD_REGISTRATION_TOKEN_MAX_AGE_SECONDS", 7200
                ),
            )
            student_email = token_payload["email"]
            redis_key = f"child_reg_pending:{student_email}"

            redis_data_json = redis_client.get(redis_key)
            if not redis_data_json:
                return err_resp(
                    "Registration data not found or expired.", "reg_data_not_found", 404
                )
            redis_data = json.loads(redis_data_json)

            existing_student = Student.query.filter_by(email=student_email).first()
            if existing_student:
                redis_client.delete(redis_key)
                return err_resp(
                    f"Student email already registered ({'archived' if existing_student.archived else 'active'}).",
                    "duplicate_email_concurrent",
                    409,
                )

            parent = Parent.query.get(redis_data["parent_id"])
            if not parent or parent.archived:
                redis_client.delete(redis_key)
                return err_resp(
                    "Associated parent account is not active.",
                    "parent_not_active_reg",
                    400,
                )

            student_creation_data = {
                **redis_data,
                "password": password,
                "is_approved": False,
                "archived": False,
            }
            new_student = load_data(
                student_creation_data
            )  # Assumes StudentSchema handles hashing
            if (
                not hasattr(new_student, "password") or not new_student.password
            ):  # Manual hash if schema didn't

                if not password:
                    redis_client.delete(redis_key)
                    return err_resp(
                        "Password is required for registration.",
                        "password_required",
                        400,
                    )
                new_student.password = generate_password_hash(password)

            db.session.add(new_student)
            db.session.commit()
            redis_client.delete(redis_key)

            identity = str(new_student.id)
            access_token = create_access_token(
                identity=identity,
                additional_claims={"role": "student"},
                expires_delta=timedelta(
                    seconds=current_app.config["ACCESS_EXPIRES_SECONDS"]
                ),
            )
            refresh_token = create_refresh_token(
                identity=identity,
                additional_claims={"role": "student"},
                expires_delta=timedelta(
                    days=current_app.config["REFRESH_EXPIRES_DAYS"]
                ),
            )

            student_resp_data = dump_data(new_student)
            return {
                "status": True,
                "message": "Registration complete. Welcome!",
                "access_token": access_token,
                "refresh_token": refresh_token,
                "user": student_resp_data,
            }, 201
        except (SignatureExpired, BadSignature):
            if redis_key:
                redis_client.delete(redis_key)
            return err_resp("Invalid or expired registration link.", "token_error", 400)
        except Exception as error:
            db.session.rollback()
            if redis_key:
                redis_client.delete(redis_key)
            current_app.logger.error(
                f"Error completing child registration: {error}", exc_info=True
            )
            return internal_err_resp()

    @staticmethod
    def update_student(student_id: int, data: dict):
        student = Student.query.filter_by(id=student_id, archived=False).first()
        if not student:
            return err_resp(
                "Student not found or is archived.", "student_not_active_update", 404
            )
        if not data:
            return err_resp("Request body empty.", "empty_update_data", 400)

        data.pop("archived", None)  # Cannot unarchive via general update
        if "parent_id" in data and data["parent_id"] != student.parent_id:
            parent_fk_error = StudentService._validate_foreign_keys(
                {"parent_id": data.get("parent_id")}
            )
            if parent_fk_error.get("parent_id"):
                return validation_error(False, parent_fk_error), 400

        other_fk_errors = StudentService._validate_foreign_keys(
            {k: v for k, v in data.items() if k != "parent_id"}
        )
        if other_fk_errors:
            return validation_error(False, other_fk_errors), 400

        try:
            updated_student = load_data(data, partial=True, instance=student)
            db.session.commit()
            return {
                "status": True,
                "message": "Student updated successfully",
                "student": dump_data(updated_student),
            }, 200
        except ValidationError as err:
            db.session.rollback()
            return validation_error(False, err.messages), 400
        except Exception as error:
            db.session.rollback()
            current_app.logger.error(
                f"Error updating student {student_id}: {error}", exc_info=True
            )
            return internal_err_resp()

    @staticmethod
    def update_approval_status(student_id: int, data: dict):
        student = Student.query.filter_by(id=student_id, archived=False).first()
        if not student:
            return err_resp(
                "Student not found or is archived.", "student_not_active_approval", 404
            )
        try:
            if "is_approved" not in data or not isinstance(data["is_approved"], bool):
                return err_resp(
                    "Invalid 'is_approved' field.", "validation_error_approval", 400
                )

            student.is_approved = data["is_approved"]

            if student.is_approved and student.parent_id:
                parent = Parent.query.get(student.parent_id)
                if parent and not parent.archived:
                    existing_fee = Fee.query.filter(
                        Fee.parent_id == student.parent_id,
                        Fee.description.like(
                            f"Registration fee for student {student.first_name} {student.last_name}%"
                        ),  # More flexible check
                    ).first()
                    if not existing_fee:
                        from app.models.Schemas import FeeSchema  # Local import

                        fee_schema = FeeSchema()
                        fee_data = {
                            "parent_id": student.parent_id,
                            "amount": current_app.config.get(
                                "REGISTRATION_FEE_AMOUNT", 1000.0
                            ),
                            "description": f"Registration fee for student {student.first_name} {student.last_name}",
                            "due_date": (datetime.now() + timedelta(days=30))
                            .date()
                            .isoformat(),
                            "status": FeeStatus.UNPAID.value,
                        }
                        try:
                            db.session.add(fee_schema.load(fee_data))
                        except Exception as fee_e:
                            current_app.logger.error(
                                f"Fee creation failed for student {student.id}: {fee_e}",
                                exc_info=True,
                            )
                elif parent and parent.archived:
                    current_app.logger.warning(
                        f"Parent {student.parent_id} is archived. No fee for student {student.id}."
                    )

            db.session.commit()
            return {
                "status": True,
                "message": f"Student approval set to {student.is_approved}",
                "student": dump_data(student),
            }, 200
        except Exception as error:
            db.session.rollback()
            current_app.logger.error(
                f"Error student approval {student_id}: {error}", exc_info=True
            )
            return internal_err_resp()

    @staticmethod
    def archive_student(student_id: int):
        student = Student.query.get(student_id)
        if not student:
            return err_resp("Student not found!", "student_404", 404)
        if student.archived:
            return {
                "status": True,
                "message": "Student is already archived.",
                "student": dump_data(student),
            }, 200
        try:
            student.archived = True
            db.session.commit()
            current_app.logger.info(f"Student archived: ID {student_id}")
            return {
                "status": True,
                "message": "Student archived successfully.",
                "student": dump_data(student),
            }, 200
        except Exception as error:
            db.session.rollback()
            current_app.logger.error(
                f"Error archiving student {student_id}: {error}", exc_info=True
            )
            return internal_err_resp()

    @staticmethod
    def unarchive_student(student_id: int):
        """Unarchive a student by ID. If their parent is archived, unarchive the parent too."""
        student = Student.query.get(
            student_id
        )  # Get student regardless of current archived status
        if not student:
            return err_resp("Student not found!", "student_404", 404)

        if not student.archived:
            current_app.logger.info(
                f"Student {student_id} is already active (not archived)."
            )
            return {
                "status": True,
                "message": "Student is already active.",
                "student": dump_data(student),
            }, 200

        try:
            student.archived = False
            current_app.logger.info(f"Student unarchived: ID {student_id}")

            # Check and unarchive parent if necessary
            parent = None  # Initialize parent to None
            if student.parent_id:
                parent = Parent.query.get(student.parent_id)
                if parent and parent.archived:
                    parent.archived = False
                    # Potentially, other logic for unarchiving a parent might trigger here in the future
                    # For now, direct unarchiving is what's requested for the student's parent.
                    current_app.logger.info(
                        f"Parent {parent.id} of student {student.id} was archived and has been unarchived."
                    )
                elif parent and not parent.archived:
                    current_app.logger.info(
                        f"Parent {parent.id} of student {student.id} is already active."
                    )
                elif not parent:
                    current_app.logger.warning(
                        f"Parent with ID {student.parent_id} for student {student.id} not found during unarchive."
                    )

            db.session.commit()

            student_data = dump_data(student)
            resp = message(True, "Student unarchived successfully.")
            if (
                parent
                and hasattr(parent, "archived")
                and not parent.archived
                and student.parent_id == parent.id
            ):  # Check if parent was actually unarchived in this operation
                resp["message"] += " The student's parent was also unarchived."

            resp["student"] = student_data
            return resp, 200
        except Exception as error:
            db.session.rollback()
            current_app.logger.error(
                f"Error unarchiving student {student_id}: {error}", exc_info=True
            )
            return internal_err_resp()
