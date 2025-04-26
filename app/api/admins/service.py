from flask import current_app
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from marshmallow import ValidationError
from werkzeug.security import generate_password_hash

# Import DB instance and models
from app import db
from app.models import Admin

# Import shared utilities and the schema CLASS
# Ensure AdminSchema exists, handles password load/dump correctly
from app.models.Schemas import AdminSchema
from app.utils import err_resp, message, internal_err_resp, validation_error

# --- Schema instances FOR VALIDATION (.load) ---
# Ensure password field in AdminSchema has load_only=True
admin_create_schema = AdminSchema()
# Define schemas for specific update scenarios
admin_super_update_schema = AdminSchema(partial=True, exclude=("email", "password"))
admin_self_update_schema = AdminSchema(
    partial=True, exclude=("email", "password", "is_super_admin")
)


# --- Utility for SERIALIZATION (.dump) ---
from .utils import load_data


class AdminService:

    # --- Check Super Admin Status ---
    @staticmethod
    def _is_super_admin(current_user_is_super):
        """Helper to check if the current user has super admin privileges"""
        if not current_user_is_super:
            return False
        return True

    # --- GET Single ---
    @staticmethod
    def get_admin_data(admin_id, current_user_id, current_user_is_super):
        """Get admin data by ID, with authorization check"""
        admin = Admin.query.get(admin_id)
        if not admin:
            return err_resp("Admin not found!", "admin_404", 404)

        # --- Authorization Check ---
        # Super Admins can see anyone, Admins can only see themselves
        if not current_user_is_super and current_user_id != admin.id:
            return err_resp(
                "Forbidden: You do not have access to this admin's data.",
                "access_denied",
                403,
            )

        try:
            admin_data = load_data(admin)  # Excludes password via schema
            resp = message(True, "Admin data sent successfully")
            resp["admin"] = admin_data
            return resp, 200
        except Exception as error:
            current_app.logger.error(
                f"Error getting admin data for ID {admin_id}: {error}", exc_info=True
            )
            return internal_err_resp()

    # --- GET List with Filters (Super Admin only) ---
    @staticmethod
    def get_all_admins(is_super_admin_filter=None, current_user_is_super=None):
        """Get a list of admins, filtered (Super Admin only view)"""
        if not AdminService._is_super_admin(current_user_is_super):
            return err_resp(
                "Forbidden: Only Super Administrators can list admin accounts.",
                "list_forbidden",
                403,
            )

        try:
            query = Admin.query

            # Apply filters
            if is_super_admin_filter is not None:
                query = query.filter(Admin.is_super_admin == is_super_admin_filter)

            # Add ordering
            admins = query.order_by(Admin.last_name).order_by(Admin.first_name).all()

            admins_data = load_data(admins, many=True)  # Excludes password
            resp = message(True, "Admins list retrieved successfully")
            resp["admins"] = admins_data
            return resp, 200
        except Exception as error:
            filters_applied = {
                k: v
                for k, v in locals().items()
                if k in ["is_super_admin_filter"] and v is not None
            }
            current_app.logger.error(
                f"Error getting all admins with filters {filters_applied}: {error}",
                exc_info=True,
            )
            return internal_err_resp()

    # --- CREATE (Super Admin only) ---
    @staticmethod
    def create_admin(data, current_user_is_super):
        """Create a new admin (Super Admin only)"""
        if not AdminService._is_super_admin(current_user_is_super):
            return err_resp(
                "Forbidden: Only Super Administrators can create admin accounts.",
                "create_forbidden",
                403,
            )

        try:
            # 1. Schema Validation
            validated_data = admin_create_schema.load(data)

            # 2. Hash Password
            password_plain = validated_data.pop("password")
            password_hash = generate_password_hash(password_plain)

            # 3. Create Instance & Commit
            # Use Admin model's default __init__ or set attributes
            new_admin = Admin(
                email=validated_data["email"],
                # password=password_hash, # Pass HASHED password if __init__ expects it
                phone_number=validated_data["phone_number"],
                first_name=validated_data.get("first_name"),
                last_name=validated_data.get("last_name"),
                is_super_admin=validated_data.get(
                    "is_super_admin", False
                ),  # Default to False if not provided
                password_hash=password_hash,  # Set hashed password directly
            )

            db.session.add(new_admin)
            db.session.commit()

            # 4. Serialize & Respond
            admin_data = load_data(new_admin)
            resp = message(True, "Admin created successfully.")
            resp["admin"] = admin_data
            return resp, 201

        except ValidationError as err:
            current_app.logger.warning(
                f"Validation error creating admin: {err.messages}"
            )
            return validation_error(False, err.messages), 400
        except IntegrityError as error:  # Catch duplicate email
            db.session.rollback()
            current_app.logger.warning(
                f"Integrity error creating admin: {error}", exc_info=True
            )
            if "admin_email_key" in str(
                error
            ) or "UNIQUE constraint failed: admin.email" in str(error):
                return err_resp(
                    f"Email '{data.get('email')}' already exists.",
                    "duplicate_email",
                    409,
                )
            return internal_err_resp()
        except SQLAlchemyError as error:
            db.session.rollback()
            current_app.logger.error(
                f"Database error creating admin: {error}", exc_info=True
            )
            return internal_err_resp()
        except Exception as error:
            db.session.rollback()
            current_app.logger.error(f"Error creating admin: {error}", exc_info=True)
            return internal_err_resp()

    # --- UPDATE (Super Admin updating another Admin) ---
    @staticmethod
    def update_admin_by_superadmin(
        admin_id, data, current_user_id, current_user_is_super
    ):
        """Update an existing admin by ID (Super Admin only)"""
        if not AdminService._is_super_admin(current_user_is_super):
            return err_resp(
                "Forbidden: Only Super Administrators can update other admin accounts.",
                "update_forbidden",
                403,
            )

        # Prevent super admin from accidentally de-promoting the last super admin?
        target_admin = Admin.query.get(admin_id)
        if not target_admin:
            return err_resp("Admin not found!", "admin_404", 404)

        if not data:
            return err_resp(
                "Request body cannot be empty for update.", "empty_update_data", 400
            )

        try:
            # Check if trying to remove last super admin status
            is_last_super_admin = False
            if (
                target_admin.is_super_admin
                and "is_super_admin" in data
                and not data["is_super_admin"]
            ):
                super_admin_count = Admin.query.filter_by(is_super_admin=True).count()
                if super_admin_count <= 1:
                    is_last_super_admin = True
                    # Prevent removing the last super admin status
                    return err_resp(
                        "Cannot remove Super Admin status from the last Super Administrator.",
                        "last_super_admin_demote",
                        409,
                    )  # 409 Conflict

            validated_data = admin_super_update_schema.load(data)

            for key, value in validated_data.items():
                setattr(target_admin, key, value)
            # target_admin.updated_at handled by onupdate

            db.session.add(target_admin)
            db.session.commit()

            admin_data = load_data(target_admin)
            resp = message(True, "Admin updated successfully by Super Admin.")
            resp["admin"] = admin_data
            return resp, 200

        except ValidationError as err:
            db.session.rollback()
            current_app.logger.warning(
                f"Validation error updating admin {admin_id} by superadmin: {err.messages}"
            )
            return validation_error(False, err.messages), 400
        except (
            IntegrityError
        ) as error:  # Catch potential unique constraint violations (e.g., phone if unique)
            db.session.rollback()
            current_app.logger.warning(
                f"Integrity error updating admin {admin_id} by superadmin: {error}",
                exc_info=True,
            )
            return internal_err_resp()
        except SQLAlchemyError as error:
            db.session.rollback()
            current_app.logger.error(
                f"Database error updating admin {admin_id} by superadmin: {error}",
                exc_info=True,
            )
            return internal_err_resp()
        except Exception as error:
            db.session.rollback()
            current_app.logger.error(
                f"Error updating admin {admin_id} by superadmin: {error}", exc_info=True
            )
            return internal_err_resp()

    # --- UPDATE (Admin updating own profile) ---
    @staticmethod
    def update_own_profile(current_user_id, data):
        """Update the currently logged-in admin's own profile"""
        admin = Admin.query.get(current_user_id)
        if not admin:
            return err_resp("Admin profile not found.", "self_not_found", 404)

        if not data:
            return err_resp(
                "Request body cannot be empty for update.", "empty_update_data", 400
            )

        try:
            # Use the specific self update schema (excludes is_super_admin)
            validated_data = admin_self_update_schema.load(data)

            for key, value in validated_data.items():
                setattr(admin, key, value)
            # admin.updated_at handled by onupdate

            db.session.add(admin)
            db.session.commit()

            admin_data = load_data(admin)
            resp = message(True, "Your profile has been updated successfully.")
            resp["admin"] = admin_data
            return resp, 200

        except ValidationError as err:
            db.session.rollback()
            current_app.logger.warning(
                f"Validation error updating own profile for admin {current_user_id}: {err.messages}"
            )
            return validation_error(False, err.messages), 400
        except (
            IntegrityError
        ) as error:  # Catch potential unique constraint violations (e.g., phone if unique)
            db.session.rollback()
            current_app.logger.warning(
                f"Integrity error updating own profile for admin {current_user_id}: {error}",
                exc_info=True,
            )
            return internal_err_resp()
        except SQLAlchemyError as error:
            db.session.rollback()
            current_app.logger.error(
                f"Database error updating own profile for admin {current_user_id}: {error}",
                exc_info=True,
            )
            return internal_err_resp()
        except Exception as error:
            db.session.rollback()
            current_app.logger.error(
                f"Error updating own profile for admin {current_user_id}: {error}",
                exc_info=True,
            )
            return internal_err_resp()

    # --- DELETE (Super Admin only) ---
    @staticmethod
    def delete_admin(admin_id_to_delete, current_user_id, current_user_is_super):
        """Delete an admin by ID (Super Admin only)"""
        if not AdminService._is_super_admin(current_user_is_super):
            return err_resp(
                "Forbidden: Only Super Administrators can delete admin accounts.",
                "delete_forbidden",
                403,
            )

        # Prevent deleting self
        if admin_id_to_delete == current_user_id:
            return err_resp(
                "Action not allowed: Cannot delete your own account.",
                "delete_self_forbidden",
                403,
            )

        admin_to_delete = Admin.query.get(admin_id_to_delete)
        if not admin_to_delete:
            return err_resp("Admin to delete not found!", "admin_404", 404)

        # Prevent deleting the last super admin
        if admin_to_delete.is_super_admin:
            super_admin_count = Admin.query.filter_by(is_super_admin=True).count()
            if super_admin_count <= 1:
                return err_resp(
                    "Cannot delete the last Super Administrator account.",
                    "last_super_admin_delete",
                    409,
                )  # 409 Conflict

        try:
            # No complex dependencies to check based on the model provided
            current_app.logger.warning(
                f"Super Admin {current_user_id} attempting to delete admin {admin_id_to_delete}."
            )

            db.session.delete(admin_to_delete)
            db.session.commit()

            current_app.logger.info(
                f"Admin {admin_id_to_delete} deleted successfully by Super Admin {current_user_id}."
            )
            return None, 204  # 204 No Content

        except SQLAlchemyError as error:
            db.session.rollback()
            current_app.logger.error(
                f"Database error deleting admin {admin_id_to_delete}: {error}",
                exc_info=True,
            )
            return err_resp(
                f"Could not delete admin due to a database constraint or error.",
                "delete_error_db",
                500,
            )
        except Exception as error:
            db.session.rollback()
            current_app.logger.error(
                f"Error deleting admin {admin_id_to_delete}: {error}", exc_info=True
            )
            return internal_err_resp()
