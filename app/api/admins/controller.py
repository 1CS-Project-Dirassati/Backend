from flask import request, current_app
from flask_restx import Resource
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt

from app.extensions import limiter
from app.api.decorators import roles_required

from .service import AdminService
from .dto import AdminDto

api = AdminDto.api
data_resp = AdminDto.data_resp
list_data_resp = AdminDto.list_data_resp
admin_create_input = AdminDto.admin_create_input
admin_super_update_input = AdminDto.admin_super_update_input
admin_self_update_input = AdminDto.admin_self_update_input
admin_filter_parser = AdminDto.admin_filter_parser


def get_current_user_info():
    user_id = get_jwt_identity()
    claims = get_jwt()
    role = claims.get("role")
    is_super = claims.get("is_super_admin", False)  # Default to False if not present
    current_app.logger.debug(
        f"Current user info: ID={user_id}, Role={role}, IsSuperAdmin={is_super}"
    )
    return user_id, role, is_super


@api.route("/")
class AdminList(Resource):

    @api.doc(
        "List admins (Super Admin only)",
        security="Bearer",
        parser=admin_filter_parser,
        description="Get a paginated list of all admins. Filterable by super admin status and archived status. (Super Admin access required)",  # Updated
        responses={
            200: ("Success", list_data_resp),
            401: "Unauthorized",
            403: "Forbidden",
            429: "Too Many Requests",
            500: "Internal Server Error",
        },
    )
    @jwt_required()
    @roles_required("admin")
    @limiter.limit(lambda: current_app.config.get("RATE_LIMIT_ADMIN_LIST", "50/minute"))
    def get(self):
        """Get a paginated list of all admins (Super Admin only)."""
        user_id, role, is_super = get_current_user_info()
        args = admin_filter_parser.parse_args()
        current_app.logger.debug(
            f"Received GET request for admins list with args: {args} by User {user_id} (Super: {is_super})"
        )
        return AdminService.get_all_admins(
            is_super_admin_filter=args.get("is_super_admin"),
            archived=args.get("archived", 0),  # ADDED archived argument
            page=args.get("page"),
            per_page=args.get("per_page"),
            current_user_is_super=is_super,
        )

    @api.doc(
        "Create a new admin (Super Admin only)",
        security="Bearer",
        description="Create a new admin account (Super Admin only). Admin will be active (not archived) by default.",  # Updated
        responses={
            201: ("Created", data_resp),
            400: "Validation Error",
            401: "Unauthorized",
            403: "Forbidden",
            409: "Conflict (e.g., duplicate email)",
            429: "Too Many Requests",
            500: "Internal Server Error",
        },
    )
    @api.expect(admin_create_input, validate=True)
    @jwt_required()
    @roles_required("admin")
    @limiter.limit(
        lambda: current_app.config.get("RATE_LIMIT_ADMIN_CREATE", "10/minute")
    )
    def post(self):
        """Create a new admin account (Super Admin only)."""
        user_id, role, is_super = get_current_user_info()
        data = request.get_json()
        current_app.logger.debug(
            f"Received POST request by User {user_id} (Super: {is_super}) to create admin with data: {data}"
        )
        return AdminService.create_admin(data, current_user_is_super=is_super)


@api.route("/<int:admin_id>")
@api.param("admin_id", "The unique identifier of the admin")
class AdminResource(Resource):

    @api.doc(
        "Get a specific admin by ID",
        security="Bearer",
        description="Get data for a specific admin. Super Admins see all (active or archived). Regular admins see their own profile (active or archived).",  # Updated
        responses={
            200: ("Success", data_resp),
            401: "Unauthorized",
            403: "Forbidden",
            404: "Not Found (or archived and not permitted)",  # Updated
            429: "Too Many Requests",
            500: "Internal Server Error",
        },
    )
    @jwt_required()
    @roles_required("admin")
    @limiter.limit(lambda: current_app.config.get("RATE_LIMIT_ADMIN_GET", "100/minute"))
    def get(self, admin_id: int):
        """Get a specific admin's data by ID (Super Admin or self)."""
        user_id, role, is_super = get_current_user_info()
        current_app.logger.debug(
            f"Received GET request for admin ID: {admin_id} by User {user_id} (Super: {is_super})"
        )
        return AdminService.get_admin_data(
            admin_id_to_get=admin_id,
            current_user_id=user_id,
            current_user_is_super=is_super,
        )

    @api.doc(
        "Update an admin (Super Admin only)",
        security="Bearer",
        description="Update fields for an active admin (Super Admin access required). Cannot remove last Super Admin status. Cannot change archive status here.",  # Updated
        responses={
            200: ("Success", data_resp),
            400: "Validation Error/Empty Body",
            401: "Unauthorized",
            403: "Forbidden",
            404: "Not Found (or admin is archived)",  # Updated
            409: "Conflict (e.g. last super admin)",
            429: "Too Many Requests",
            500: "Internal Server Error",
        },
    )
    @api.expect(admin_super_update_input, validate=True)
    @jwt_required()
    @roles_required("admin")
    @limiter.limit(
        lambda: current_app.config.get("RATE_LIMIT_ADMIN_SUPER_UPDATE", "30/minute")
    )
    def put(self, admin_id: int):
        """Update an existing admin (Super Admin only)."""
        user_id, role, is_super = get_current_user_info()
        data = request.get_json()
        current_app.logger.debug(
            f"Received PUT request by User {user_id} (Super: {is_super}) for admin ID {admin_id} with data: {data}"
        )
        return AdminService.update_admin_by_superadmin(
            admin_id_to_update=admin_id,
            data=data,
            current_user_id=user_id,  # For logging or if needed for "cannot update self's super_admin status"
            current_user_is_super=is_super,
        )

    @api.doc(
        "Archive an admin (Super Admin only)",  # CHANGED
        security="Bearer",
        description="Archive an admin's profile (Super Admin access required). Cannot archive self or the last Super Admin. This is a soft delete.",  # CHANGED
        responses={
            200: ("Success - Admin Archived", data_resp),  # CHANGED to 200
            401: "Unauthorized",
            403: "Forbidden (Not Super Admin / Archiving self / Last Super Admin)",  # Updated
            404: "Not Found",
            409: "Conflict (e.g. Last Super Admin if trying to archive)",
            429: "Too Many Requests",
            500: "Internal Server Error",
        },
    )
    @jwt_required()
    @roles_required("admin")
    @limiter.limit(
        lambda: current_app.config.get("RATE_LIMIT_ADMIN_ARCHIVE", "5/minute")
    )  # New limit key
    def delete(self, admin_id: int):  # HTTP DELETE for archival action
        """Archive an admin (Super Admin only) - Soft Delete."""
        user_id, role, is_super = get_current_user_info()
        current_app.logger.warning(
            f"Received DELETE (archive) request by User {user_id} (Super: {is_super}) for admin ID: {admin_id}"
        )
        return AdminService.archive_admin(
            admin_id_to_archive=admin_id,
            current_user_id=user_id,
            current_user_is_super=is_super,
        )  # CHANGED service call


@api.route("/<int:admin_id>/unarchive")  # NEW ROUTE
@api.param("admin_id", "The unique identifier of the admin to unarchive")
class AdminUnarchive(Resource):
    @api.doc(
        "Unarchive an admin (Super Admin only)",
        security="Bearer",
        description="Unarchive an admin's profile (Super Admin access required).",
        responses={
            200: ("Success - Admin Unarchived", data_resp),
            400: "Bad Request (e.g., admin not archived or email conflict)",
            401: "Unauthorized",
            403: "Forbidden",
            404: "Not Found",
            429: "Too Many Requests",
            500: "Internal Server Error",
        },
    )
    @jwt_required()
    @roles_required("admin")
    @limiter.limit(
        lambda: current_app.config.get("RATE_LIMIT_ADMIN_UNARCHIVE", "5/minute")
    )  # New limit key
    def post(self, admin_id: int):  # Using POST for action
        """Unarchive an admin (Super Admin only)."""
        user_id, role, is_super = get_current_user_info()
        current_app.logger.info(
            f"Received POST (unarchive) request by User {user_id} (Super: {is_super}) for admin ID: {admin_id}"
        )
        return AdminService.unarchive_admin(
            admin_id_to_unarchive=admin_id, current_user_is_super=is_super
        )


@api.route("/me")
class AdminProfile(Resource):

    @api.doc(
        "Get own admin profile",
        security="Bearer",
        description="Get the profile data for the currently logged-in admin. Accessible even if profile is archived (for self-view).",  # Updated
        responses={
            200: ("Success", data_resp),
            401: "Unauthorized",
            403: "Forbidden",  # Should not happen if role is 'admin'
            404: "Not Found",  # If user_id from token does not match an admin
            500: "Internal Server Error",
        },
    )
    @jwt_required()
    @roles_required("admin")
    @limiter.limit(
        lambda: current_app.config.get("RATE_LIMIT_ADMIN_ME_GET", "100/minute")
    )
    def get(self):
        """Get own admin profile."""
        user_id, role, is_super = get_current_user_info()
        current_app.logger.debug(
            f"Received GET request for own admin profile (ID: {user_id}, Super: {is_super})"
        )
        return AdminService.get_admin_data(
            admin_id_to_get=user_id,
            current_user_id=user_id,
            current_user_is_super=is_super,
        )

    @api.doc(
        "Update own admin profile",
        security="Bearer",
        description="Update profile details for the currently logged-in, active admin. Cannot change Super Admin status or archive status.",  # Updated
        responses={
            200: ("Success", data_resp),
            400: "Validation Error/Empty Body",
            401: "Unauthorized",
            403: "Forbidden (e.g. if admin is archived)",  # Updated
            404: "Not Found",  # Should not happen if JWT is valid
            409: "Conflict",
            500: "Internal Server Error",
        },
    )
    @api.expect(admin_self_update_input, validate=True)
    @jwt_required()
    @roles_required("admin")
    @limiter.limit(
        lambda: current_app.config.get("RATE_LIMIT_ADMIN_ME_UPDATE", "30/minute")
    )
    def put(self):
        """Update own admin profile."""
        user_id, _, is_super = (
            get_current_user_info()
        )  # is_super might be useful for logging or context
        data = request.get_json()
        current_app.logger.debug(
            f"Received PUT request for own admin profile (ID: {user_id}, Super: {is_super}) with data: {data}"
        )
        return AdminService.update_own_profile(current_user_id=user_id, data=data)
