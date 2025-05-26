from flask import current_app
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy.orm import aliased  # Import aliased for cleaner joins
from marshmallow import ValidationError
from werkzeug.security import generate_password_hash

from app import db
from app.models import (
    Group,
    Parent,
    Student,
    Session,  # Import Session model
    # Fee, Notification etc. only needed if manually checking cascade on delete
)

from app.utils import (
    err_resp,
    message,
    internal_err_resp,
    validation_error,
)

from .utils import dump_data, load_data


class ParentService:

    @staticmethod
    def get_parent_data(parent_id: int, current_user_id: int, current_user_role: str):
        """Get parent data by ID, with record-level authorization check"""
        parent = Parent.query.get(parent_id)
        if not parent:
            current_app.logger.info(f"Parent with ID {parent_id} not found.")
            return err_resp("Parent not found!", "parent_404", 404)

        # Record-Level Authorization Check
        can_access = False
        if current_user_role == "admin":
            can_access = True
        elif current_user_role == "parent" and int(current_user_id) == parent.id:
            can_access = True
        elif current_user_role == "teacher":
            # Teacher can access if they teach one of the parent's students
            # This logic can be complex, for now, let's assume if they have a link.
            # A more robust check would join through Student and Session.
            # For simplicity in this specific method, we might rely on the list view filtering for teachers.
            # Or, add a specific check here:
            teacher_has_link = (
                db.session.query(Parent.id)
                .join(Parent.students)
                .join(Student.sessions)
                .filter(Session.teacher_id == current_user_id, Parent.id == parent_id)
                .first()
            )
            if teacher_has_link:
                can_access = True

        if not can_access:
            current_app.logger.warning(
                f"Forbidden: User {current_user_id} (Role: {current_user_role}) attempted to access parent record {parent_id}."
            )
            return err_resp(
                "Forbidden: You do not have permission to access this parent's data.",
                "record_access_denied",
                403,
            )

        current_app.logger.debug(
            f"Record access granted for user {current_user_id} to parent {parent_id}."
        )

        try:
            parent_data = dump_data(parent)
            resp = message(True, "Parent data sent successfully")
            resp["parent"] = parent_data
            current_app.logger.debug(f"Successfully retrieved parent ID {parent_id}")
            return resp, 200
        except Exception as error:
            current_app.logger.error(
                f"Error serializing parent data for ID {parent_id}: {error}",
                exc_info=True,
            )
            return internal_err_resp()

    @staticmethod
    def get_all_parents(
        is_email_verified=None,
        is_phone_verified=None,
        student_id=None,
        teacher_id=None,  # ADDED teacher_id parameter
        page=None,
        per_page=None,
        current_user_role=None,
    ):
        """Get a paginated list of parents, filtered (Admin or Teacher view)"""
        # Role check for teacher specific logic if needed, though decorator covers general access
        # if current_user_role not in ["admin", "teacher"]:
        #     current_app.logger.warning(f"Unauthorized attempt to list parents by role: {current_user_role}")
        #     return err_resp("Forbidden: You do not have permission to list parents.", "list_access_denied", 403)

        page = page or 1
        per_page = per_page or 10

        try:
            query = Parent.query
            filters_applied = {}

            # Apply filters
            if is_email_verified is not None:
                filters_applied["is_email_verified"] = is_email_verified
                query = query.filter(Parent.is_email_verified == is_email_verified)
            if is_phone_verified is not None:
                filters_applied["is_phone_verified"] = is_phone_verified
                query = query.filter(Parent.is_phone_verified == is_phone_verified)

            # Student ID filter
            if student_id is not None:
                filters_applied["student_id"] = student_id
                # Ensure Parent.students relationship exists and is correctly named
                query = query.join(Parent.students).filter(Student.id == student_id)

            # Teacher ID filter - NEW
            if teacher_id is not None:
                filters_applied["teacher_id"] = teacher_id
                # Join path: Parent -> Student -> student_session (association table for Student <-> Session) -> Session
                # Assuming Student.sessions is the relationship to Session model (many-to-many or via association object)
                # If Student.sessions directly links to Session model (e.g., if a student has a list of sessions they attend)
                query = (
                    query.join(Parent.students)  # Join Parent to Student
                    .join(Student.group)  # Join Student to Group if needed
                    .join(Group.sessions)  # Join Group to Session
                    .filter(Session.teacher_id == teacher_id)
                    .distinct()
                )  # Use distinct to avoid duplicate parents if multiple students of same parent are taught by the teacher

            if filters_applied:
                current_app.logger.debug(
                    f"Applying parent list filters: {filters_applied}"
                )

            query = query.order_by(
                Parent.last_name, Parent.first_name
            )  # Corrected order_by

            current_app.logger.debug(
                f"Paginating parents: page={page}, per_page={per_page}"
            )
            paginated_parents = query.paginate(
                page=page, per_page=per_page, error_out=False
            )
            current_app.logger.debug(
                f"Paginated parents items count: {len(paginated_parents.items)}"
            )

            parents_data = dump_data(paginated_parents.items, many=True)

            current_app.logger.debug(f"Serialized {len(parents_data)} parents")
            resp = message(True, "Parents list retrieved successfully")
            resp["parents"] = parents_data
            resp["total"] = paginated_parents.total
            resp["pages"] = paginated_parents.pages
            resp["current_page"] = paginated_parents.page
            resp["per_page"] = paginated_parents.per_page
            resp["has_next"] = paginated_parents.has_next
            resp["has_prev"] = paginated_parents.has_prev

            current_app.logger.debug(
                f"Successfully retrieved parents page {page}. Total: {paginated_parents.total}"
            )
            return resp, 200

        except Exception as error:
            log_msg = f"Error getting parents list"
            if page:
                log_msg += f", page {page}"
            current_app.logger.error(f"{log_msg}: {error}", exc_info=True)
            return internal_err_resp()

    @staticmethod
    def create_parent(data: dict):
        """Create a new parent. Assumes @roles_required('admin') handled authorization."""
        try:
            from app.models.Schemas import ParentSchema

            parent_create_schema = ParentSchema(
                exclude=(
                    "is_email_verified",
                    "is_phone_verified",
                    "created_at",
                    "updated_at",
                    "id",
                )  # Ensure these are not loaded
            )
            validated_data = parent_create_schema.load(data)

            current_app.logger.debug(
                f"Parent data validated by schema. Proceeding with hash."
            )

            password_plain = validated_data.pop("password")
            password_hash = generate_password_hash(password_plain)
            current_app.logger.debug(
                f"Password hashed for parent email: {validated_data.get('email')}"
            )

            new_parent = {
                **validated_data,
                "password": password_hash,
                "user_type": "parent",  # Set user_type to 'parent'
            }

            new_parent = load_data(new_parent)  # Convert dict to Parent model instance
            db.session.add(new_parent)
            db.session.commit()
            current_app.logger.info(
                f"Parent created successfully with ID: {new_parent.id}"
            )

            parent_resp_data = dump_data(new_parent)
            resp = message(True, "Parent created successfully.")
            resp["parent"] = parent_resp_data
            return resp, 201

        except ValidationError as err:
            db.session.rollback()
            current_app.logger.warning(
                f"Schema validation error creating parent: {err.messages}. Data: {data}"
            )
            return validation_error(False, err.messages), 400
        except IntegrityError as error:
            db.session.rollback()
            current_app.logger.warning(
                f"Database integrity error creating parent: {error}. Data: {data}",
                exc_info=True,
            )
            if "parent_email_key" in str(
                error.orig
            ) or "UNIQUE constraint failed: parent.email" in str(error.orig):
                return err_resp(
                    f"Email '{data.get('email')}' already exists.",
                    "duplicate_email",
                    409,
                )
            return internal_err_resp()
        except SQLAlchemyError as error:
            db.session.rollback()
            current_app.logger.error(
                f"Database error creating parent: {error}. Data: {data}", exc_info=True
            )
            return internal_err_resp()
        except Exception as error:
            db.session.rollback()
            current_app.logger.error(
                f"Unexpected error creating parent: {error}. Data: {data}",
                exc_info=True,
            )
            return internal_err_resp()

    @staticmethod
    def update_parent_by_admin(parent_id: int, data: dict):
        """Update an existing parent by ID. Assumes @roles_required('admin') handled authorization."""
        parent = Parent.query.get(parent_id)
        if not parent:
            current_app.logger.info(
                f"Attempted admin update for non-existent parent ID: {parent_id}"
            )
            return err_resp("Parent not found!", "parent_404", 404)

        if not data:
            current_app.logger.warning(
                f"Attempted admin update for parent {parent_id} with empty data."
            )
            return err_resp(
                "Request body cannot be empty for update.", "empty_update_data", 400
            )

        try:
            # For admin updates, explicitly exclude fields admin shouldn't change
            from app.models.Schemas import ParentSchema

            admin_update_schema = ParentSchema(
                partial=True,
                exclude=(
                    "id",
                    "email",
                    "password",
                    "is_email_verified",
                    "is_phone_verified",
                    "created_at",
                    "updated_at",
                ),
            )
            # Use the schema's load method with instance for update
            updated_parent = admin_update_schema.load(
                data, instance=parent, partial=True
            )

            current_app.logger.debug(
                f"Parent data validated by schema for admin update. Committing changes for ID: {parent_id}"
            )

            db.session.commit()
            current_app.logger.info(
                f"Parent updated successfully by admin for ID: {parent_id}"
            )

            parent_resp_data = dump_data(updated_parent)
            resp = message(True, "Parent updated successfully by admin.")
            resp["parent"] = parent_resp_data
            return resp, 200

        except ValidationError as err:
            db.session.rollback()
            current_app.logger.warning(
                f"Schema validation error during admin update for parent {parent_id}: {err.messages}. Data: {data}"
            )
            return validation_error(False, err.messages), 400
        except IntegrityError as error:
            db.session.rollback()
            current_app.logger.warning(
                f"Database integrity error during admin update for parent {parent_id}: {error}. Data: {data}",
                exc_info=True,
            )
            return internal_err_resp()
        except SQLAlchemyError as error:
            db.session.rollback()
            current_app.logger.error(
                f"Database error during admin update for parent {parent_id}: {error}. Data: {data}",
                exc_info=True,
            )
            return internal_err_resp()
        except Exception as error:
            db.session.rollback()
            current_app.logger.error(
                f"Unexpected error during admin update for parent {parent_id}: {error}. Data: {data}",
                exc_info=True,
            )
            return internal_err_resp()

    @staticmethod
    def update_own_profile(current_user_id: int, data: dict):
        """Update the currently logged-in parent's own profile. Assumes @roles_required('parent') handled authorization."""
        parent = Parent.query.get(current_user_id)
        if not parent:
            current_app.logger.error(
                f"Attempted self-update for non-existent parent ID: {current_user_id}. JWT might be invalid."
            )
            return err_resp("Parent profile not found.", "self_not_found", 404)

        if not data:
            current_app.logger.warning(
                f"Attempted self-update for parent {current_user_id} with empty data."
            )
            return err_resp(
                "Request body cannot be empty for update.", "empty_update_data", 400
            )

        try:
            from app.models.Schemas import ParentSchema

            self_update_schema = ParentSchema(
                partial=True,
                exclude=(
                    "id",
                    "email",
                    "password",
                    "is_email_verified",
                    "is_phone_verified",
                    "created_at",
                    "updated_at",
                ),
            )
            updated_parent = self_update_schema.load(
                data, instance=parent, partial=True
            )

            current_app.logger.debug(
                f"Parent data validated by schema for self-update. Committing changes for ID: {current_user_id}"
            )

            db.session.commit()
            current_app.logger.info(
                f"Parent self-profile updated successfully for ID: {current_user_id}"
            )

            parent_resp_data = dump_data(updated_parent)
            resp = message(True, "Your profile has been updated successfully.")
            resp["parent"] = parent_resp_data
            return resp, 200

        except ValidationError as err:
            db.session.rollback()
            current_app.logger.warning(
                f"Schema validation error during self-update for parent {current_user_id}: {err.messages}. Data: {data}"
            )
            return validation_error(False, err.messages), 400
        except IntegrityError as error:
            db.session.rollback()
            current_app.logger.warning(
                f"Database integrity error during self-update for parent {current_user_id}: {error}. Data: {data}",
                exc_info=True,
            )
            return internal_err_resp()
        except SQLAlchemyError as error:
            db.session.rollback()
            current_app.logger.error(
                f"Database error during self-update for parent {current_user_id}: {error}. Data: {data}",
                exc_info=True,
            )
            return internal_err_resp()
        except Exception as error:
            db.session.rollback()
            current_app.logger.error(
                f"Unexpected error during self-update for parent {current_user_id}: {error}. Data: {data}",
                exc_info=True,
            )
            return internal_err_resp()

    @staticmethod
    def delete_parent(parent_id: int):
        """Delete a parent by ID. Assumes @roles_required('admin') handled authorization."""
        parent = Parent.query.get(parent_id)
        if not parent:
            current_app.logger.info(
                f"Attempted admin delete for non-existent parent ID: {parent_id}"
            )
            return err_resp("Parent not found!", "parent_404", 404)

        try:
            current_app.logger.warning(
                f"Attempting admin delete for parent {parent_id}. THIS WILL CASCADE DELETE associated students, fees, notifications, etc."
            )

            db.session.delete(parent)
            db.session.commit()

            current_app.logger.info(
                f"Parent {parent_id} and associated data deleted successfully by admin."
            )
            return None, 204

        except SQLAlchemyError as error:
            db.session.rollback()
            current_app.logger.error(
                f"Database error during admin delete for parent {parent_id}: {error}",
                exc_info=True,
            )
            return err_resp(
                f"Could not delete parent due to a database constraint or error.",
                "delete_error_db",
                500,
            )
        except Exception as error:
            db.session.rollback()
            current_app.logger.error(
                f"Unexpected error during admin delete for parent {parent_id}: {error}",
                exc_info=True,
            )
            return internal_err_resp()
