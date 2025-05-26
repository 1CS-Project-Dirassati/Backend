from flask import current_app
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from marshmallow import ValidationError
from werkzeug.security import generate_password_hash

from app import db
from app.models import Admin

from app.utils import err_resp, message, internal_err_resp, validation_error
from .utils import dump_data, load_data


class AdminService:

    @staticmethod
    def _is_super_admin(current_user_is_super_claim: bool) -> bool:
        return bool(current_user_is_super_claim)

    @staticmethod
    def get_admin_data(
        admin_id_to_get: int, current_user_id: int, current_user_is_super: bool
    ):
        admin = Admin.query.get(admin_id_to_get)
        if not admin:
            return err_resp("Admin not found!", "admin_404", 404)

        # Super Admins can see any admin (active or archived).
        # Regular admins can only see their own profile (active or archived).
        can_access = False
        if AdminService._is_super_admin(current_user_is_super):
            can_access = True
        elif int(current_user_id) == admin.id:  # Admin accessing self
            can_access = True

        if not can_access:
            # If not super admin and not self, and trying to access an archived profile, treat as forbidden/not found
            if admin.archived:
                current_app.logger.warning(
                    f"User {current_user_id} (Super: {current_user_is_super}) attempted to access archived admin {admin_id_to_get} without permission."
                )
                return err_resp(
                    "Admin not found or access denied.",
                    "admin_archived_access_denied",
                    404,
                )  # Mask as 404
            current_app.logger.warning(
                f"User {current_user_id} (Super: {current_user_is_super}) denied access to admin {admin_id_to_get}."
            )
            return err_resp(
                "Forbidden: You do not have permission to access this admin's data.",
                "record_access_denied",
                403,
            )

        try:
            admin_data = dump_data(admin)
            return {
                "status": True,
                "message": "Admin data sent successfully.",
                "admin": admin_data,
            }, 200
        except Exception as e:
            current_app.logger.error(
                f"Error getting admin {admin_id_to_get}: {e}", exc_info=True
            )
            return internal_err_resp()

    @staticmethod
    def get_all_admins(
        is_super_admin_filter=None,
        archived=0,  # Default to 0 (not archived)
        page=None,
        per_page=None,
        current_user_is_super=False,
    ):
        if not AdminService._is_super_admin(current_user_is_super):
            return err_resp(
                "Forbidden: Only Super Administrators can list admin accounts.",
                "list_admins_forbidden",
                403,
            )

        page = page or 1
        per_page = per_page or 10
        archived_bool = bool(archived)

        try:
            query = Admin.query
            filters_applied = {
                "archived": archived_bool
            }  # Always filter by archived status first

            query = query.filter(Admin.archived == archived_bool)

            if is_super_admin_filter is not None:
                filters_applied["is_super_admin"] = is_super_admin_filter
                query = query.filter(Admin.is_super_admin == is_super_admin_filter)

            current_app.logger.debug(f"Applying admin list filters: {filters_applied}")
            query = query.order_by(Admin.last_name, Admin.first_name)
            paginated_admins = query.paginate(
                page=page, per_page=per_page, error_out=False
            )

            admins_data = dump_data(paginated_admins.items, many=True)
            resp = message(True, "Admins list retrieved successfully.")
            resp.update(
                {
                    "admins": admins_data,
                    "total": paginated_admins.total,
                    "pages": paginated_admins.pages,
                    "current_page": paginated_admins.page,
                    "per_page": paginated_admins.per_page,
                    "has_next": paginated_admins.has_next,
                    "has_prev": paginated_admins.has_prev,
                }
            )
            return resp, 200
        except Exception as e:
            current_app.logger.error(f"Error getting all admins: {e}", exc_info=True)
            return internal_err_resp()

    @staticmethod
    def create_admin(data: dict, current_user_is_super: bool):
        if not AdminService._is_super_admin(current_user_is_super):
            return err_resp(
                "Forbidden: Only Super Administrators can create admin accounts.",
                "create_admin_forbidden",
                403,
            )

        try:
            existing_admin = Admin.query.filter_by(email=data.get("email")).first()
            if existing_admin:
                status = "archived" if existing_admin.archived else "active"
                return err_resp(
                    f"Email '{data.get('email')}' already used by an {status} admin.",
                    "duplicate_email_admin",
                    409,
                )

            new_admin = load_data(data)  # AdminSchema used
            new_admin.archived = False  # New admins are active
            new_admin.password = generate_password_hash(
                data["password"]
            )  # Schema should have password as load_only
            # is_super_admin is set from data by load_data if present, or defaults in model/schema
            if "is_super_admin" not in data:  # Ensure default if not provided
                new_admin.is_super_admin = data.get("is_super_admin", False)

            db.session.add(new_admin)
            db.session.commit()
            admin_data = dump_data(new_admin)
            return {
                "status": True,
                "message": "Admin created successfully.",
                "admin": admin_data,
            }, 201
        except ValidationError as err:
            db.session.rollback()
            return validation_error(False, err.messages), 400
        except IntegrityError:
            db.session.rollback()
            return err_resp(f"Integrity error: ", "integrity_error_admin", 400)
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error creating admin: {e}", exc_info=True)
            return internal_err_resp()

    @staticmethod
    def update_admin_by_superadmin(
        admin_id_to_update: int,
        data: dict,
        current_user_id: int,  # ID of the admin performing the update
        current_user_is_super: bool,
    ):
        if not AdminService._is_super_admin(current_user_is_super):
            return err_resp(
                "Forbidden: Only Super Admins can update other admin accounts.",
                "update_admin_forbidden",
                403,
            )

        target_admin = Admin.query.filter_by(
            id=admin_id_to_update, archived=False
        ).first()  # Can only update active admins
        if not target_admin:
            return err_resp(
                "Admin to update not found or is archived.",
                "admin_not_active_update",
                404,
            )

        if not data:
            return err_resp(
                "Request body cannot be empty.", "empty_update_data_admin", 400
            )

        data.pop("archived", None)  # Cannot change archive status here
        data.pop("email", None)
        data.pop("password", None)

        # Last Super Admin Check when changing is_super_admin status
        if (
            "is_super_admin" in data
            and target_admin.is_super_admin
            and not data["is_super_admin"]
        ):
            # If trying to remove super_admin status from an existing super_admin
            super_admin_count = Admin.query.filter_by(
                is_super_admin=True, archived=False
            ).count()
            if super_admin_count <= 1:
                return err_resp(
                    "Conflict: Cannot remove Super Admin status from the last active Super Administrator.",
                    "last_super_admin_demote_conflict",
                    409,
                )

        try:
            updated_admin = load_data(data, partial=True, instance=target_admin)
            db.session.commit()
            return {
                "status": True,
                "message": "Admin updated successfully.",
                "admin": dump_data(updated_admin),
            }, 200
        except ValidationError as err:
            db.session.rollback()
            return validation_error(False, err.messages), 400
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(
                f"Error updating admin (superadmin) {admin_id_to_update}: {e}",
                exc_info=True,
            )
            return internal_err_resp()

    @staticmethod
    def update_own_profile(current_user_id: int, data: dict):
        admin = Admin.query.filter_by(
            id=current_user_id, archived=False
        ).first()  # Can only update own active profile
        if not admin:
            return err_resp(
                "Admin profile not found or is archived.",
                "admin_profile_not_active_self",
                403,
            )
        if not data:
            return err_resp(
                "Request body cannot be empty.", "empty_update_data_self_admin", 400
            )

        data.pop("archived", None)
        data.pop("email", None)
        data.pop("password", None)
        data.pop(
            "is_super_admin", None
        )  # Cannot change own super_admin status via this route

        try:
            updated_admin = load_data(data, partial=True, instance=admin)
            db.session.commit()
            return {
                "status": True,
                "message": "Profile updated successfully.",
                "admin": dump_data(updated_admin),
            }, 200
        except ValidationError as err:
            db.session.rollback()
            return validation_error(False, err.messages), 400
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(
                f"Error admin self-update {current_user_id}: {e}", exc_info=True
            )
            return internal_err_resp()

    @staticmethod
    def archive_admin(
        admin_id_to_archive: int, current_user_id: int, current_user_is_super: bool
    ):
        if not AdminService._is_super_admin(current_user_is_super):
            return err_resp(
                "Forbidden: Only Super Admins can archive admin accounts.",
                "archive_admin_forbidden",
                403,
            )

        if admin_id_to_archive == int(current_user_id):
            return err_resp(
                "Forbidden: Cannot archive your own account.",
                "archive_self_admin_forbidden",
                403,
            )

        admin_to_archive = Admin.query.get(admin_id_to_archive)
        if not admin_to_archive:
            return err_resp("Admin to archive not found!", "admin_to_archive_404", 404)

        if admin_to_archive.archived:
            return {
                "status": True,
                "message": "Admin is already archived.",
                "admin": dump_data(admin_to_archive),
            }, 200

        # Last Super Admin Check before archiving
        if admin_to_archive.is_super_admin:
            super_admin_count = Admin.query.filter_by(
                is_super_admin=True, archived=False
            ).count()  # Count only active super admins
            if super_admin_count <= 1:
                return err_resp(
                    "Conflict: Cannot archive the last active Super Administrator.",
                    "last_super_admin_archive_conflict",
                    409,
                )

        try:
            admin_to_archive.archived = True
            # Optionally, if an archived admin should not retain super_admin status:
            # admin_to_archive.is_super_admin = False
            db.session.commit()
            current_app.logger.info(
                f"Admin archived: ID {admin_id_to_archive} by User {current_user_id}"
            )
            return {
                "status": True,
                "message": "Admin archived successfully.",
                "admin": dump_data(admin_to_archive),
            }, 200
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(
                f"Error archiving admin {admin_id_to_archive}: {e}", exc_info=True
            )
            return internal_err_resp()

    @staticmethod
    def unarchive_admin(admin_id_to_unarchive: int, current_user_is_super: bool):
        if not AdminService._is_super_admin(current_user_is_super):
            return err_resp(
                "Forbidden: Only Super Admins can unarchive admin accounts.",
                "unarchive_admin_forbidden",
                403,
            )

        admin_to_unarchive = Admin.query.get(admin_id_to_unarchive)
        if not admin_to_unarchive:
            return err_resp(
                "Admin to unarchive not found!", "admin_to_unarchive_404", 404
            )

        if not admin_to_unarchive.archived:
            return {
                "status": True,
                "message": "Admin is already active.",
                "admin": dump_data(admin_to_unarchive),
            }, 200

        try:
            # Safety check: if another active admin uses this email
            existing_active_admin = Admin.query.filter(
                Admin.email == admin_to_unarchive.email,
                Admin.archived == False,
                Admin.id != admin_id_to_unarchive,
            ).first()
            if existing_active_admin:
                return err_resp(
                    f"Cannot unarchive. Email '{admin_to_unarchive.email}' is in use by another active admin.",
                    "email_conflict_unarchive_admin",
                    409,
                )

            admin_to_unarchive.archived = False
            # Super_admin status remains as it was before archiving unless explicitly changed by an update later.
            db.session.commit()
            current_app.logger.info(f"Admin unarchived: ID {admin_id_to_unarchive}")
            return {
                "status": True,
                "message": "Admin unarchived successfully.",
                "admin": dump_data(admin_to_unarchive),
            }, 200
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(
                f"Error unarchiving admin {admin_id_to_unarchive}: {e}", exc_info=True
            )
            return internal_err_resp()

    # delete_admin from your original code was a hard delete. Replaced by archive_admin.
    # If hard delete is ever needed, it would be a separate, highly restricted function.
