# Added current_app
from flask import current_app
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from marshmallow import ValidationError
from werkzeug.security import generate_password_hash

# Import DB instance and models
from app import db
from app.models import (
    Parent,
)  # Student, Fee, Notification etc. only needed if manually checking cascade on delete

# Import shared utilities
from app.utils import (
    err_resp,
    message,
    internal_err_resp,
    validation_error,
)

# Import serialization/deserialization utilities from local utils.py
from .utils import dump_data, load_data


class ParentService:

    # --- GET Single ---
    @staticmethod
    # Add type hints
    def get_parent_data(parent_id: int, current_user_id: int, current_user_role: str):
        """Get parent data by ID, with record-level authorization check"""
        parent = Parent.query.get(parent_id)
        if not parent:
            current_app.logger.info(
                f"Parent with ID {parent_id} not found."
            )  # Add logging
            return err_resp("Parent not found!", "parent_404", 404)

        # --- Record-Level Authorization Check ---
        # Can the current user view THIS specific parent's record?
        if  current_user_role=="parent" and int(current_user_id) != parent.id:
            current_app.logger.warning(
                f"Forbidden: User {current_user_id} (Role: {current_user_role}) attempted to access parent record {parent_id}."
            )  # Add logging
            return err_resp(
                "Forbidden: You do not have permission to access this parent's data.",
                "record_access_denied",
                403,
            )
        current_app.logger.debug(
            f"Record access granted for user {current_user_id} to parent {parent_id}."
        )  # Add logging

        try:
            # Use dump_data for serialization (excludes password via schema)
            parent_data = dump_data(parent)
            resp = message(True, "Parent data sent successfully")
            resp["parent"] = parent_data
            current_app.logger.debug(
                f"Successfully retrieved parent ID {parent_id}"
            )  # Add logging
            return resp, 200
        except Exception as error:
            current_app.logger.error(
                f"Error serializing parent data for ID {parent_id}: {error}",  # Update log message
                exc_info=True,
            )
            return internal_err_resp()

    # --- GET List with Filters and Pagination (Admin only) ---
    @staticmethod
    # Add type hints
    def get_all_parents(
        is_email_verified=None,
        is_phone_verified=None,
        page=None,
        per_page=None,
        current_user_role=None,  # Kept for explicit check, though decorator also covers it
    ):
        """Get a paginated list of parents, filtered (Admin only view)"""
        # Explicit check remains as belt-and-suspenders, though decorator should prevent non-admins
        

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

            if filters_applied:
                current_app.logger.debug(
                    f"Applying parent list filters: {filters_applied}"
                )

            # Add ordering
            query = query.order_by(Parent.last_name).order_by(Parent.first_name)

            # Implement pagination
            current_app.logger.debug(
                f"Paginating parents: page={page}, per_page={per_page}"
            )
            paginated_parents = query.paginate(
                page=page, per_page=per_page, error_out=False
            )
            current_app.logger.debug(
                f"Paginated parents items count: {len(paginated_parents.items)}"
            )

            # Serialize results using dump_data (excludes password)
            parents_data = dump_data(paginated_parents.items, many=True)

            current_app.logger.debug(f"Serialized {len(parents_data)} parents")
            resp = message(True, "Parents list retrieved successfully")
            # Add pagination metadata
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

    # --- CREATE (Admin only) ---
    @staticmethod
    # Add type hint
    def create_parent(data: dict):
        """Create a new parent. Assumes @roles_required('admin') handled authorization."""
        # No role check needed here - decorator handles it.
        try:
            # 1. Schema Validation & Deserialization using load_data
            # Assuming load_data returns a dict for creation, or adjust as needed.
            # Using temporary manual load until load_data adjusted/confirmed.
            from app.models.Schemas import ParentSchema  # Temp import

            parent_create_schema = ParentSchema()  # Temp instance
            validated_data = parent_create_schema.load(data)
            # End Temporary block

            current_app.logger.debug(
                f"Parent data validated by schema. Proceeding with hash."
            )

            # 2. Hash Password
            password_plain = validated_data.pop("password")
            password_hash = generate_password_hash(password_plain)
            current_app.logger.debug(
                f"Password hashed for parent email: {validated_data.get('email')}"
            )

            # 3. Create Instance & Commit
            new_parent = Parent(
                password=password_hash,  # Pass HASHED password
                **validated_data,  # Pass remaining validated fields
                # Verification flags default to False in model
            )

            db.session.add(new_parent)
            db.session.commit()
            current_app.logger.info(
                f"Parent created successfully with ID: {new_parent.id}"
            )

            # 4. Serialize & Respond using dump_data (Excludes password)
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
                error.orig  # Access original DBAPI error if needed
            ) or "UNIQUE constraint failed: parent.email" in str(error.orig):
                return err_resp(
                    f"Email '{data.get('email')}' already exists.",
                    "duplicate_email",
                    409,
                )
            # Add check for phone number if it needs to be unique
            # if "parent_phone_number_key" in str(error.orig): ...
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

    # --- UPDATE (Admin Perspective) ---
    @staticmethod
    # Add type hints
    def update_parent_by_admin(parent_id: int, data: dict):
        """Update an existing parent by ID. Assumes @roles_required('admin') handled authorization."""
        # No role check needed here - decorator handles it.

        parent = Parent.query.get(parent_id)
        if not parent:
            current_app.logger.info(
                f"Attempted admin update for non-existent parent ID: {parent_id}"
            )  # Add logging
            return err_resp("Parent not found!", "parent_404", 404)

        if not data:
            current_app.logger.warning(
                f"Attempted admin update for parent {parent_id} with empty data."
            )  # Add logging
            return err_resp(
                "Request body cannot be empty for update.", "empty_update_data", 400
            )

        try:
            # Use load_data with partial=True and instance=parent
            # Ensure ParentSchema excludes email, password, verification status for partial admin updates
            updated_parent = load_data(data, partial=True, instance=parent)
            current_app.logger.debug(
                f"Parent data validated by schema for admin update. Committing changes for ID: {parent_id}"
            )  # Add logging

            db.session.commit()
            current_app.logger.info(
                f"Parent updated successfully by admin for ID: {parent_id}"
            )  # Add logging

            # Serialize & Respond using dump_data
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
        except (
            IntegrityError
        ) as error:  # Catch potential unique constraint violations (e.g., phone if unique)
            db.session.rollback()
            current_app.logger.warning(
                f"Database integrity error during admin update for parent {parent_id}: {error}. Data: {data}",
                exc_info=True,
            )
            # Add specific checks if needed (e.g., phone number uniqueness)
            return internal_err_resp()  # Or a specific 409
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

    # --- UPDATE (Parent updating own profile) ---
    @staticmethod
    # Add type hints
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
            )  # Add logging
            return err_resp(
                "Request body cannot be empty for update.", "empty_update_data", 400
            )

        try:
            # Use load_data with partial=True and instance=parent
            # Ensure ParentSchema excludes email, password, verification status for partial self-updates
            updated_parent = load_data(data, partial=True, instance=parent)
            current_app.logger.debug(
                f"Parent data validated by schema for self-update. Committing changes for ID: {current_user_id}"
            )  # Add logging

            # Check if phone number changed and potentially trigger re-verification logic here if needed
            # if 'phone_number' in data and data['phone_number'] != parent.phone_number:
            #     updated_parent.is_phone_verified = False
            #     current_app.logger.info(f"Parent {current_user_id} phone number updated, requires re-verification.")
            #     # Add code to send verification SMS

            db.session.commit()
            current_app.logger.info(
                f"Parent self-profile updated successfully for ID: {current_user_id}"
            )  # Add logging

            # Serialize & Respond using dump_data
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
        except (
            IntegrityError
        ) as error:  # Catch potential unique constraint violations (e.g., phone if unique)
            db.session.rollback()
            current_app.logger.warning(
                f"Database integrity error during self-update for parent {current_user_id}: {error}. Data: {data}",
                exc_info=True,
            )
            # Add specific checks if needed (e.g., phone number uniqueness)
            return internal_err_resp()  # Or a specific 409
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

    # --- DELETE (Admin only) ---
    @staticmethod
    # Add type hint
    def delete_parent(parent_id: int):
        """Delete a parent by ID. Assumes @roles_required('admin') handled authorization."""
        # No role check needed here - decorator handles it.

        parent = Parent.query.get(parent_id)
        if not parent:
            current_app.logger.info(
                f"Attempted admin delete for non-existent parent ID: {parent_id}"
            )  # Add logging
            return err_resp("Parent not found!", "parent_404", 404)

        try:
            # Cascade delete is handled by SQLAlchemy relationships (Student.parent, Fee.parent, etc.)
            current_app.logger.warning(
                f"Attempting admin delete for parent {parent_id}. THIS WILL CASCADE DELETE associated students, fees, notifications, etc."
            )  # Log warning

            db.session.delete(parent)
            db.session.commit()

            current_app.logger.info(
                f"Parent {parent_id} and associated data deleted successfully by admin."  # Clarify admin action
            )
            return None, 204

        except SQLAlchemyError as error:
            db.session.rollback()
            current_app.logger.error(
                f"Database error during admin delete for parent {parent_id}: {error}",
                exc_info=True,
            )
            # Add specific constraint checks if cascade fails unexpectedly
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
