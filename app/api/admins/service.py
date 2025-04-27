# Added current_app
from flask import current_app
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from marshmallow import ValidationError
from werkzeug.security import generate_password_hash

# Import DB instance and models
from app import db
from app.models import Admin

# Import shared utilities
from app.utils import (
    err_resp,
    message,
    internal_err_resp,
    validation_error,
)

# Import serialization/deserialization utilities from local utils.py
from .utils import dump_data, load_data


class AdminService:

    # --- Check Super Admin Status ---
    @staticmethod
    def _is_super_admin(current_user_is_super: bool) -> bool:  # Added type hint
        """Helper to check if the current user has super admin privileges"""
        return bool(current_user_is_super)  # Ensure boolean return

    # --- GET Single ---
    @staticmethod
    # Add type hints
    def get_admin_data(
        admin_id: int, current_user_id: int, current_user_is_super: bool
    ):
        """Get admin data by ID, with record-level authorization check"""
        admin = Admin.query.get(admin_id)
        if not admin:
            current_app.logger.info(
                f"Admin with ID {admin_id} not found."
            )  # Add logging
            return err_resp("Admin not found!", "admin_404", 404)

        # --- Record-Level Authorization Check ---
        # Super Admins can see anyone, Admins can only see themselves
        can_access = AdminService._is_super_admin(current_user_is_super) or (
            current_user_id == admin.id
        )

        if not can_access:
            current_app.logger.warning(
                f"Forbidden: User {current_user_id} (IsSuper: {current_user_is_super}) attempted to access admin record {admin_id}."
            )  # Add logging
            return err_resp(
                "Forbidden: You do not have permission to access this admin's data.",
                "record_access_denied",
                403,
            )
        current_app.logger.debug(
            f"Record access granted for user {current_user_id} to admin {admin_id}."
        )  # Add logging

        try:
            # Use dump_data for serialization (excludes password via schema)
            admin_data = dump_data(admin)
            resp = message(True, "Admin data sent successfully")
            resp["admin"] = admin_data
            current_app.logger.debug(
                f"Successfully retrieved admin ID {admin_id}"
            )  # Add logging
            return resp, 200
        except Exception as error:
            current_app.logger.error(
                f"Error serializing admin data for ID {admin_id}: {error}",  # Update log message
                exc_info=True,
            )
            return internal_err_resp()

    # --- GET List with Filters and Pagination (Super Admin only) ---
    @staticmethod
    # Add type hints
    def get_all_admins(
        is_super_admin_filter=None,
        page=None,
        per_page=None,
        current_user_is_super=False,  # Keep for explicit check
    ):
        """Get a paginated list of admins, filtered (Super Admin only view)"""
        if not AdminService._is_super_admin(current_user_is_super):
            current_app.logger.error(
                f"Non-super admin user attempted to list all admins."
            )  # Add logging
            return err_resp(
                "Forbidden: Only Super Administrators can list admin accounts.",
                "list_forbidden",
                403,
            )

        page = page or 1
        per_page = per_page or 10

        try:
            query = Admin.query
            filters_applied = {}

            # Apply filters
            if is_super_admin_filter is not None:
                filters_applied["is_super_admin"] = is_super_admin_filter
                query = query.filter(Admin.is_super_admin == is_super_admin_filter)

            if filters_applied:
                current_app.logger.debug(
                    f"Applying admin list filters: {filters_applied}"
                )

            # Add ordering
            query = query.order_by(Admin.last_name).order_by(Admin.first_name)

            # Implement pagination
            current_app.logger.debug(
                f"Paginating admins: page={page}, per_page={per_page}"
            )
            paginated_admins = query.paginate(
                page=page, per_page=per_page, error_out=False
            )
            current_app.logger.debug(
                f"Paginated admins items count: {len(paginated_admins.items)}"
            )

            # Serialize results using dump_data (excludes password)
            admins_data = dump_data(paginated_admins.items, many=True)

            current_app.logger.debug(f"Serialized {len(admins_data)} admins")
            resp = message(True, "Admins list retrieved successfully")
            # Add pagination metadata
            resp["admins"] = admins_data
            resp["total"] = paginated_admins.total
            resp["pages"] = paginated_admins.pages
            resp["current_page"] = paginated_admins.page
            resp["per_page"] = paginated_admins.per_page
            resp["has_next"] = paginated_admins.has_next
            resp["has_prev"] = paginated_admins.has_prev

            current_app.logger.debug(
                f"Successfully retrieved admins page {page}. Total: {paginated_admins.total}"
            )
            return resp, 200

        except Exception as error:
            log_msg = f"Error getting admins list"
            if page:
                log_msg += f", page {page}"
            current_app.logger.error(f"{log_msg}: {error}", exc_info=True)
            return internal_err_resp()

    # --- CREATE (Super Admin only) ---
    @staticmethod
    # Add type hints
    def create_admin(data: dict, current_user_is_super: bool):
        """Create a new admin (Super Admin only)"""
        if not AdminService._is_super_admin(current_user_is_super):
            current_app.logger.warning(
                f"Forbidden: Non-super admin attempted to create admin account."
            )  # Add logging
            return err_resp(
                "Forbidden: Only Super Administrators can create admin accounts.",
                "create_forbidden",
                403,
            )

        try:
            # 1. Schema Validation & Deserialization using load_data (assuming dict return)
            # Using temporary manual load until load_data adjusted/confirmed.
            from app.models.Schemas import AdminSchema  # Temp import

            admin_create_schema = AdminSchema()  # Temp instance
            validated_data = admin_create_schema.load(data)
            # End Temporary block

            current_app.logger.debug(
                f"Admin data validated by schema. Proceeding with hash."
            )

            # 2. Hash Password
            password_plain = validated_data.pop("password")
            password_hash = generate_password_hash(password_plain)
            current_app.logger.debug(
                f"Password hashed for admin email: {validated_data.get('email')}"
            )

            # 3. Create Instance & Commit
            new_admin = Admin(
                password_hash=password_hash,  # Pass HASHED password
                is_super_admin=validated_data.get(
                    "is_super_admin", False
                ),  # Default if not provided
                **validated_data,  # Pass remaining validated fields (email, phone, names)
            )

            db.session.add(new_admin)
            db.session.commit()
            current_app.logger.info(
                f"Admin created successfully with ID: {new_admin.id}, SuperAdminStatus: {new_admin.is_super_admin}"
            )  # Add logging

            # 4. Serialize & Respond using dump_data (Excludes password)
            admin_resp_data = dump_data(new_admin)
            resp = message(True, "Admin created successfully.")
            resp["admin"] = admin_resp_data
            return resp, 201

        except ValidationError as err:
            db.session.rollback()
            current_app.logger.warning(
                f"Schema validation error creating admin: {err.messages}. Data: {data}"
            )
            return validation_error(False, err.messages), 400
        except IntegrityError as error:
            db.session.rollback()
            current_app.logger.warning(
                f"Database integrity error creating admin: {error}. Data: {data}",
                exc_info=True,
            )
            if "admin_email_key" in str(
                error.orig  # Access original DBAPI error if needed
            ) or "UNIQUE constraint failed: admin.email" in str(error.orig):
                return err_resp(
                    f"Email '{data.get('email')}' already exists.",
                    "duplicate_email",
                    409,
                )
            # Add check for phone number if unique constraint exists
            return internal_err_resp()
        except SQLAlchemyError as error:
            db.session.rollback()
            current_app.logger.error(
                f"Database error creating admin: {error}. Data: {data}", exc_info=True
            )
            return internal_err_resp()
        except Exception as error:
            db.session.rollback()
            current_app.logger.error(
                f"Unexpected error creating admin: {error}. Data: {data}", exc_info=True
            )
            return internal_err_resp()

    # --- UPDATE (Super Admin updating another Admin) ---
    @staticmethod
    # Add type hints
    def update_admin_by_superadmin(
        admin_id_to_update: int,
        data: dict,
        current_user_id: int,
        current_user_is_super: bool,
    ):
        """Update an existing admin by ID (Super Admin only), with safety checks."""
        if not AdminService._is_super_admin(current_user_is_super):
            current_app.logger.warning(
                f"Forbidden: Non-super admin {current_user_id} attempted to update admin {admin_id_to_update}."
            )  # Add logging
            return err_resp(
                "Forbidden: Only Super Administrators can update other admin accounts.",
                "update_forbidden",
                403,
            )

        target_admin = Admin.query.get(admin_id_to_update)
        if not target_admin:
            current_app.logger.info(
                f"Attempted super admin update for non-existent admin ID: {admin_id_to_update}"
            )  # Add logging
            return err_resp("Admin not found!", "admin_404", 404)

        if not data:
            current_app.logger.warning(
                f"Attempted super admin update for admin {admin_id_to_update} with empty data."
            )  # Add logging
            return err_resp(
                "Request body cannot be empty for update.", "empty_update_data", 400
            )

        try:
            # --- Last Super Admin Check ---
            is_removing_super_status = (
                "is_super_admin" in data and not data["is_super_admin"]
            )
            if target_admin.is_super_admin and is_removing_super_status:
                super_admin_count = Admin.query.filter_by(is_super_admin=True).count()
                if super_admin_count <= 1:
                    current_app.logger.warning(
                        f"Conflict: Super admin {current_user_id} attempted to remove last super admin status from admin {admin_id_to_update}."
                    )  # Add logging
                    return err_resp(
                        "Conflict: Cannot remove Super Admin status from the last Super Administrator.",
                        "last_super_admin_demote",
                        409,
                    )

            # Use load_data with partial=True and instance=target_admin
            # Ensure AdminSchema allows 'is_super_admin' update but excludes email/password
            updated_admin = load_data(data, partial=True, instance=target_admin)
            current_app.logger.debug(
                f"Admin data validated by schema for super admin update. Committing changes for ID: {admin_id_to_update}"
            )  # Add logging

            db.session.commit()
            current_app.logger.info(
                f"Admin updated successfully by super admin for ID: {admin_id_to_update}"
            )  # Add logging

            # Serialize & Respond using dump_data
            admin_resp_data = dump_data(updated_admin)
            resp = message(True, "Admin updated successfully by Super Admin.")
            resp["admin"] = admin_resp_data
            return resp, 200

        except ValidationError as err:
            db.session.rollback()
            current_app.logger.warning(
                f"Schema validation error during super admin update for admin {admin_id_to_update}: {err.messages}. Data: {data}"
            )
            return validation_error(False, err.messages), 400
        except (
            IntegrityError
        ) as error:  # Catch potential unique constraint violations (e.g., phone if unique)
            db.session.rollback()
            current_app.logger.warning(
                f"Database integrity error during super admin update for admin {admin_id_to_update}: {error}. Data: {data}",
                exc_info=True,
            )
            # Add specific checks if needed
            return internal_err_resp()  # Or a specific 409
        except SQLAlchemyError as error:
            db.session.rollback()
            current_app.logger.error(
                f"Database error during super admin update for admin {admin_id_to_update}: {error}. Data: {data}",
                exc_info=True,
            )
            return internal_err_resp()
        except Exception as error:
            db.session.rollback()
            current_app.logger.error(
                f"Unexpected error during super admin update for admin {admin_id_to_update}: {error}. Data: {data}",
                exc_info=True,
            )
            return internal_err_resp()

    # --- UPDATE (Admin updating own profile) ---
    @staticmethod
    # Add type hints
    def update_own_profile(current_user_id: int, data: dict):
        """Update the currently logged-in admin's own profile. Assumes @roles_required('admin') handled authorization."""
        admin = Admin.query.get(current_user_id)
        if not admin:
            current_app.logger.error(
                f"Attempted self-update for non-existent admin ID: {current_user_id}. JWT might be invalid."
            )
            return err_resp("Admin profile not found.", "self_not_found", 404)

        if not data:
            current_app.logger.warning(
                f"Attempted self-update for admin {current_user_id} with empty data."
            )  # Add logging
            return err_resp(
                "Request body cannot be empty for update.", "empty_update_data", 400
            )

        try:
            # Use load_data with partial=True and instance=admin
            # Ensure AdminSchema excludes email, password, is_super_admin for partial self-updates
            updated_admin = load_data(data, partial=True, instance=admin)
            current_app.logger.debug(
                f"Admin data validated by schema for self-update. Committing changes for ID: {current_user_id}"
            )  # Add logging

            db.session.commit()
            current_app.logger.info(
                f"Admin self-profile updated successfully for ID: {current_user_id}"
            )  # Add logging

            # Serialize & Respond using dump_data
            admin_resp_data = dump_data(updated_admin)
            resp = message(True, "Your profile has been updated successfully.")
            resp["admin"] = admin_resp_data
            return resp, 200

        except ValidationError as err:
            db.session.rollback()
            current_app.logger.warning(
                f"Schema validation error during self-update for admin {current_user_id}: {err.messages}. Data: {data}"
            )
            return validation_error(False, err.messages), 400
        except (
            IntegrityError
        ) as error:  # Catch potential unique constraint violations (e.g., phone if unique)
            db.session.rollback()
            current_app.logger.warning(
                f"Database integrity error during self-update for admin {current_user_id}: {error}. Data: {data}",
                exc_info=True,
            )
            # Add specific checks if needed
            return internal_err_resp()  # Or a specific 409
        except SQLAlchemyError as error:
            db.session.rollback()
            current_app.logger.error(
                f"Database error during self-update for admin {current_user_id}: {error}. Data: {data}",
                exc_info=True,
            )
            return internal_err_resp()
        except Exception as error:
            db.session.rollback()
            current_app.logger.error(
                f"Unexpected error during self-update for admin {current_user_id}: {error}. Data: {data}",
                exc_info=True,
            )
            return internal_err_resp()

    # --- DELETE (Super Admin only) ---
    @staticmethod
    # Add type hints
    def delete_admin(
        admin_id_to_delete: int, current_user_id: int, current_user_is_super: bool
    ):
        """Delete an admin by ID (Super Admin only), with safety checks."""
        if not AdminService._is_super_admin(current_user_is_super):
            current_app.logger.warning(
                f"Forbidden: Non-super admin {current_user_id} attempted to delete admin {admin_id_to_delete}."
            )  # Add logging
            return err_resp(
                "Forbidden: Only Super Administrators can delete admin accounts.",
                "delete_forbidden",
                403,
            )

        if admin_id_to_delete == current_user_id:
            current_app.logger.warning(
                f"Forbidden: Admin {current_user_id} attempted to delete own account."
            )  # Add logging
            return err_resp(
                "Forbidden: Cannot delete your own account.",
                "delete_self_forbidden",
                403,
            )

        admin_to_delete = Admin.query.get(admin_id_to_delete)
        if not admin_to_delete:
            current_app.logger.info(
                f"Attempted super admin delete for non-existent admin ID: {admin_id_to_delete}"
            )  # Add logging
            return err_resp("Admin to delete not found!", "admin_404", 404)

        # --- Last Super Admin Check ---
        if admin_to_delete.is_super_admin:
            super_admin_count = Admin.query.filter_by(is_super_admin=True).count()
            if super_admin_count <= 1:
                current_app.logger.warning(
                    f"Conflict: Super admin {current_user_id} attempted to delete the last super admin account (ID: {admin_id_to_delete})."
                )  # Add logging
                return err_resp(
                    "Conflict: Cannot delete the last Super Administrator account.",
                    "last_super_admin_delete",
                    409,
                )

        try:
            current_app.logger.warning(
                f"Super Admin {current_user_id} attempting to delete admin {admin_id_to_delete}."
            )  # Log intent

            db.session.delete(admin_to_delete)
            db.session.commit()

            current_app.logger.info(
                f"Admin {admin_id_to_delete} deleted successfully by Super Admin {current_user_id}."
            )  # Log success
            return None, 204

        except SQLAlchemyError as error:
            db.session.rollback()
            current_app.logger.error(
                f"Database error during super admin delete for admin {admin_id_to_delete}: {error}",
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
                f"Unexpected error during super admin delete for admin {admin_id_to_delete}: {error}",
                exc_info=True,
            )
            return internal_err_resp()
