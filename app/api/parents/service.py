from flask import current_app
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from marshmallow import ValidationError
from werkzeug.security import generate_password_hash

# Import DB instance and models
from app import db
from app.models import (
    Parent,
)  # Student, Fee, Notification needed if checking dependencies on delete

# Import shared utilities and the schema CLASS
# Ensure ParentSchema exists and excludes 'password' on dump, handles password on load
from app.models.Schemas import ParentSchema
from app.utils import err_resp, message, internal_err_resp, validation_error

# --- Schema instances FOR VALIDATION (.load) ---
# Ensure password field in ParentSchema has load_only=True
parent_create_schema = ParentSchema()
# Define schemas for specific update scenarios, excluding immutable/sensitive fields
parent_admin_update_schema = ParentSchema(
    partial=True,
    exclude=("email", "password", "is_email_verified", "is_phone_verified"),
)
parent_self_update_schema = ParentSchema(
    partial=True,
    exclude=("email", "password", "is_email_verified", "is_phone_verified"),
)


# --- Utility for SERIALIZATION (.dump) ---
from .utils import load_data


class ParentService:

    # --- GET Single ---
    @staticmethod
    def get_parent_data(parent_id, current_user_id, current_user_role):
        """Get parent data by ID, with authorization check"""
        parent = Parent.query.get(parent_id)
        if not parent:
            return err_resp("Parent not found!", "parent_404", 404)

        # --- Authorization Check ---
        if current_user_role != "admin" and current_user_id != parent.id:
            return err_resp(
                "Forbidden: You do not have access to this parent's data.",
                "access_denied",
                403,
            )

        try:
            parent_data = load_data(parent)  # Excludes password via schema
            resp = message(True, "Parent data sent successfully")
            resp["parent"] = parent_data
            return resp, 200
        except Exception as error:
            current_app.logger.error(
                f"Error getting parent data for ID {parent_id}: {error}", exc_info=True
            )
            return internal_err_resp()

    # --- GET List with Filters (Admin only) ---
    @staticmethod
    def get_all_parents(
        is_email_verified=None, is_phone_verified=None, current_user_role=None
    ):
        """Get a list of parents, filtered (Admin only view)"""
        if current_user_role != "admin":
            # Non-admins should not be able to list all parents
            return err_resp("Forbidden: Access denied.", "list_forbidden", 403)

        try:
            query = Parent.query

            # Apply filters
            if is_email_verified is not None:
                query = query.filter(Parent.is_email_verified == is_email_verified)
            if is_phone_verified is not None:
                query = query.filter(Parent.is_phone_verified == is_phone_verified)

            # Add ordering
            parents = query.order_by(Parent.last_name).order_by(Parent.first_name).all()

            parents_data = load_data(parents, many=True)  # Excludes password
            resp = message(True, "Parents list retrieved successfully")
            resp["parents"] = parents_data
            return resp, 200
        except Exception as error:
            filters_applied = {
                k: v
                for k, v in locals().items()
                if k in ["is_email_verified", "is_phone_verified"] and v is not None
            }
            current_app.logger.error(
                f"Error getting all parents with filters {filters_applied}: {error}",
                exc_info=True,
            )
            return internal_err_resp()

    # --- CREATE (Admin only for now) ---
    @staticmethod
    def create_parent(data, current_user_role):
        """Create a new parent (Admin only)"""
        if current_user_role != "admin":
            return err_resp(
                "Forbidden: Only administrators can create parent accounts.",
                "create_forbidden",
                403,
            )

        try:
            # 1. Schema Validation
            validated_data = parent_create_schema.load(data)

            # 2. Hash Password
            password_plain = validated_data.pop("password")
            password_hash = generate_password_hash(password_plain)

            # 3. Create Instance & Commit
            # Use explicit __init__ or set attributes
            new_parent = Parent(
                email=validated_data["email"],
                password=password_hash,  # Pass the HASHED password to __init__
                phone_number=validated_data["phone_number"],
                first_name=validated_data.get("first_name"),
                last_name=validated_data.get("last_name"),
                # address=validated_data.get('address'), # Add if needed
                # profile_picture=validated_data.get('profile_picture') # Add if needed
            )
            # Verification flags default to False in model

            db.session.add(new_parent)
            db.session.commit()

            # 4. Serialize & Respond (Excluding password)
            parent_data = load_data(new_parent)
            resp = message(True, "Parent created successfully.")
            resp["parent"] = parent_data
            return resp, 201

        except ValidationError as err:
            current_app.logger.warning(
                f"Validation error creating parent: {err.messages}"
            )
            return validation_error(False, err.messages), 400
        except IntegrityError as error:  # Catch duplicate email
            db.session.rollback()
            current_app.logger.warning(
                f"Integrity error creating parent: {error}", exc_info=True
            )
            if "parent_email_key" in str(
                error
            ) or "UNIQUE constraint failed: parent.email" in str(error):
                return err_resp(
                    f"Email '{data.get('email')}' already exists.",
                    "duplicate_email",
                    409,
                )
            # Add check for phone number if it needs to be unique
            return internal_err_resp()
        except SQLAlchemyError as error:
            db.session.rollback()
            current_app.logger.error(
                f"Database error creating parent: {error}", exc_info=True
            )
            return internal_err_resp()
        except Exception as error:
            db.session.rollback()
            current_app.logger.error(f"Error creating parent: {error}", exc_info=True)
            return internal_err_resp()

    # --- UPDATE (Admin Perspective) ---
    @staticmethod
    def update_parent_by_admin(parent_id, data, current_user_role):
        """Update an existing parent by ID (Admin only)"""
        if current_user_role != "admin":
            return err_resp(
                "Forbidden: Only administrators can update parent details.",
                "update_forbidden",
                403,
            )

        parent = Parent.query.get(parent_id)
        if not parent:
            return err_resp("Parent not found!", "parent_404", 404)

        if not data:
            return err_resp(
                "Request body cannot be empty for update.", "empty_update_data", 400
            )

        try:
            # Use the specific admin update schema
            validated_data = parent_admin_update_schema.load(data)

            # Update Instance Fields & Commit
            for key, value in validated_data.items():
                setattr(parent, key, value)
            # parent.updated_at handled by onupdate

            db.session.add(parent)
            db.session.commit()

            # Serialize & Respond
            parent_data = load_data(parent)
            resp = message(True, "Parent updated successfully by admin.")
            resp["parent"] = parent_data
            return resp, 200

        except ValidationError as err:
            db.session.rollback()
            current_app.logger.warning(
                f"Validation error updating parent {parent_id} by admin: {err.messages}"
            )
            return validation_error(False, err.messages), 400
        except (
            IntegrityError
        ) as error:  # Catch potential unique constraint violations (e.g., phone if unique)
            db.session.rollback()
            current_app.logger.warning(
                f"Integrity error updating parent {parent_id} by admin: {error}",
                exc_info=True,
            )
            return internal_err_resp()
        except SQLAlchemyError as error:
            db.session.rollback()
            current_app.logger.error(
                f"Database error updating parent {parent_id} by admin: {error}",
                exc_info=True,
            )
            return internal_err_resp()
        except Exception as error:
            db.session.rollback()
            current_app.logger.error(
                f"Error updating parent {parent_id} by admin: {error}", exc_info=True
            )
            return internal_err_resp()

    # --- UPDATE (Parent updating own profile) ---
    @staticmethod
    def update_own_profile(current_user_id, data):
        """Update the currently logged-in parent's own profile"""
        parent = Parent.query.get(current_user_id)
        if not parent:
            # Should not happen if JWT is valid, but handle defensively
            return err_resp("Parent profile not found.", "self_not_found", 404)

        if not data:
            return err_resp(
                "Request body cannot be empty for update.", "empty_update_data", 400
            )

        try:
            # Use the specific self update schema
            validated_data = parent_self_update_schema.load(data)

            # Update Instance Fields & Commit
            for key, value in validated_data.items():
                setattr(parent, key, value)
            # parent.updated_at handled by onupdate

            db.session.add(parent)
            db.session.commit()

            # Serialize & Respond
            parent_data = load_data(parent)
            resp = message(True, "Your profile has been updated successfully.")
            resp["parent"] = parent_data
            return resp, 200

        except ValidationError as err:
            db.session.rollback()
            current_app.logger.warning(
                f"Validation error updating own profile for parent {current_user_id}: {err.messages}"
            )
            return validation_error(False, err.messages), 400
        except (
            IntegrityError
        ) as error:  # Catch potential unique constraint violations (e.g., phone if unique)
            db.session.rollback()
            current_app.logger.warning(
                f"Integrity error updating own profile for parent {current_user_id}: {error}",
                exc_info=True,
            )
            return internal_err_resp()
        except SQLAlchemyError as error:
            db.session.rollback()
            current_app.logger.error(
                f"Database error updating own profile for parent {current_user_id}: {error}",
                exc_info=True,
            )
            return internal_err_resp()
        except Exception as error:
            db.session.rollback()
            current_app.logger.error(
                f"Error updating own profile for parent {current_user_id}: {error}",
                exc_info=True,
            )
            return internal_err_resp()

    # --- DELETE (Admin only) ---
    @staticmethod
    def delete_parent(parent_id, current_user_role):
        """Delete a parent by ID (Admin only)"""
        if current_user_role != "admin":
            return err_resp(
                "Forbidden: Only administrators can delete parents.",
                "delete_forbidden",
                403,
            )

        parent = Parent.query.get(parent_id)
        if not parent:
            return err_resp("Parent not found!", "parent_404", 404)

        try:
            # IMPORTANT: Cascade delete is defined on Student, Fee, Notification relationships.
            # Deleting a parent WILL delete all associated students, fees, notifications.
            # Add checks here if this needs to be prevented under certain conditions.
            # Example: if parent.students: return err_resp("Cannot delete parent with associated students. Reassign students first.", "delete_conflict_students", 409)

            current_app.logger.warning(
                f"Attempting to delete parent {parent_id} by admin {current_user_role}. This will cascade delete associated students, fees, and notifications."
            )

            db.session.delete(parent)
            db.session.commit()

            current_app.logger.info(
                f"Parent {parent_id} and associated data deleted successfully."
            )
            return None, 204  # 204 No Content

        except SQLAlchemyError as error:
            db.session.rollback()
            current_app.logger.error(
                f"Database error deleting parent {parent_id}: {error}", exc_info=True
            )
            return err_resp(
                f"Could not delete parent due to a database constraint or error.",
                "delete_error_db",
                500,
            )
        except Exception as error:
            db.session.rollback()
            current_app.logger.error(
                f"Error deleting parent {parent_id}: {error}", exc_info=True
            )
            return internal_err_resp()
