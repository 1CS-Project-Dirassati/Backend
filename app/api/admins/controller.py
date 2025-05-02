# Added current_app
from flask import request, current_app
from flask_restx import Resource
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt

# Import shared extensions/decorators
from app.extensions import limiter
from app.api.decorators import roles_required

# Import admin-specific modules
from .service import AdminService
from .dto import AdminDto

# Get the API namespace and DTOs
api = AdminDto.api
data_resp = AdminDto.data_resp
list_data_resp = AdminDto.list_data_resp
admin_create_input = AdminDto.admin_create_input
admin_super_update_input = AdminDto.admin_super_update_input
admin_self_update_input = AdminDto.admin_self_update_input
# Get the filter/pagination parser
admin_filter_parser = AdminDto.admin_filter_parser


# --- Helper to get current user info (including super admin status) ---
def get_current_user_info():
    user_id = get_jwt_identity()
    claims = get_jwt()
    role = claims.get("role")  # Still 'admin'
    # IMPORTANT: Assumes 'is_super_admin' boolean claim exists in JWT
    is_super = claims.get("is_super_admin", True)    # Log user info including super admin status
    current_app.logger.debug(
        f"Current user info: ID={user_id}, Role={role}, IsSuperAdmin={is_super}"
    )
    return user_id, role, is_super


# --- Route for listing/creating admins (Super Admin focused) ---
@api.route("/")
class AdminList(Resource):

    @api.doc(
        "List admins (Super Admin only)",
        security="Bearer",
        parser=admin_filter_parser,
        # Updated description
        description="Get a paginated list of all admins. Filterable by super admin status. (Super Admin access required)",
        responses={
            200: ("Success", list_data_resp),
            401: "Unauthorized",
            403: "Forbidden",
            429: "Too Many Requests",
            500: "Internal Server Error",
        },
    )
    @jwt_required()
    @roles_required("admin")  # Base role check
    # Use config for rate limit
    @limiter.limit(lambda: current_app.config.get("RATE_LIMIT_ADMIN_LIST", "50/minute"))
    def get(self):
        """Get a paginated list of all admins (Super Admin only)"""
        user_id, role, is_super = get_current_user_info()  # Get super admin status
        args = admin_filter_parser.parse_args()
        # Add logging
        current_app.logger.debug(
            f"Received GET request for admins list with args: {args}"
        )

        # Service layer performs the super admin check using is_super
        return AdminService.get_all_admins(
            is_super_admin_filter=args.get("is_super_admin"),
            page=args.get("page"),  # Pass pagination arg
            per_page=args.get("per_page"),  # Pass pagination arg
            current_user_is_super=is_super,  # Pass super admin status
        )

    @api.doc(
        "Create a new admin (Super Admin only)",
        security="Bearer",
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
    @roles_required("admin")  # Base role check
    # Use config for rate limit
    @limiter.limit(
        lambda: current_app.config.get("RATE_LIMIT_ADMIN_CREATE", "10/minute")
    )
    def post(self):
        """Create a new admin account (Super Admin only)"""
        user_id, role, is_super = get_current_user_info()  # Get super admin status
        data = request.get_json()
        # Add logging
        current_app.logger.debug(
            f"Received POST request to create admin with data: {data}"
        )
        # Service layer performs the super admin check using is_super
        return AdminService.create_admin(data, is_super)


# --- Route for specific admin operations ---
@api.route("/<int:admin_id>")
@api.param("admin_id", "The unique identifier of the admin")
class AdminResource(Resource):

    @api.doc(
        "Get a specific admin by ID",
        security="Bearer",
        description="Get data for a specific admin. Access restricted to Super Admins or the admin themselves.",
        responses={
            200: ("Success", data_resp),
            401: "Unauthorized",
            403: "Forbidden",
            404: "Not Found",
            429: "Too Many Requests",
            500: "Internal Server Error",
        },
    )
    @jwt_required()
    @roles_required("admin")  # Base role check
    # Use config for rate limit
    @limiter.limit(lambda: current_app.config.get("RATE_LIMIT_ADMIN_GET", "100/minute"))
    # Add type hint
    def get(self, admin_id: int):
        """Get a specific admin's data by ID (Super Admin or self)"""
        # Get user info for record-level access check in service
        user_id, role, is_super = get_current_user_info()
        # Add logging
        current_app.logger.debug(f"Received GET request for admin ID: {admin_id}")
        # Pass user info for record-level check (is_super OR user_id matches admin_id)
        return AdminService.get_admin_data(admin_id, user_id, is_super)

    @api.doc(
        "Update an admin (Super Admin only)",
        security="Bearer",
        description="Update fields for an admin (Super Admin access required). Cannot remove last Super Admin status.",
        responses={
            200: ("Success", data_resp),
            400: "Validation Error/Empty Body",
            401: "Unauthorized",
            403: "Forbidden",
            404: "Not Found",
            409: "Conflict (e.g. last super admin)",
            429: "Too Many Requests",
            500: "Internal Server Error",
        },
    )
    @api.expect(admin_super_update_input, validate=True)
    @jwt_required()
    @roles_required("admin")  # Base role check
    # Use config for rate limit
    @limiter.limit(
        lambda: current_app.config.get("RATE_LIMIT_ADMIN_SUPER_UPDATE", "30/minute")
    )
    # Add type hint
    def put(self, admin_id: int):
        """Update an existing admin (Super Admin only)"""
        user_id, role, is_super = get_current_user_info()  # Get super admin status
        data = request.get_json()
        # Add logging
        current_app.logger.debug(
            f"Received PUT request by super admin for admin ID {admin_id} with data: {data}"
        )
        # Service layer handles the super admin check and last super admin logic
        return AdminService.update_admin_by_superadmin(
            admin_id,
            data,
            user_id,
            is_super,  # Pass current user_id for logging/context if needed
        )

    @api.doc(
        "Delete an admin (Super Admin only)",
        security="Bearer",
        description="Delete an admin (Super Admin access required). Cannot delete self or the last Super Admin.",
        responses={
            204: "No Content - Success",
            401: "Unauthorized",
            403: "Forbidden (Not Super Admin / Deleting self)",
            404: "Not Found",
            409: "Conflict (Last Super Admin)",
            429: "Too Many Requests",
            500: "Internal Server Error",
        },
    )
    @jwt_required()
    @roles_required("admin")  # Base role check
    # Use config for rate limit
    @limiter.limit(
        lambda: current_app.config.get("RATE_LIMIT_ADMIN_DELETE", "5/minute")
    )
    # Add type hint
    def delete(self, admin_id: int):
        """Delete an admin (Super Admin only) - Cannot delete self or last Super Admin"""
        user_id, role, is_super = (
            get_current_user_info()
        )  # Get super admin status and user ID
        # Add logging
        current_app.logger.debug(
            f"Received DELETE request by super admin for admin ID: {admin_id}"
        )
        # Service layer handles authorization (is_super) and safety checks (self, last super admin)
        return AdminService.delete_admin(admin_id, user_id, is_super)


# --- Route specifically for admin managing their own profile ---
@api.route("/me")
class AdminProfile(Resource):

    @api.doc(
        "Get own admin profile",
        security="Bearer",
        description="Get the profile data for the currently logged-in admin.",
        responses={
            200: ("Success", data_resp),
            401: "Unauthorized",
            403: "Forbidden",  # Added 403
            404: "Not Found",
            500: "Internal Server Error",
        },
    )
    @jwt_required()
    @roles_required("admin")  # Base role check sufficient
    # Use config for rate limit
    @limiter.limit(
        lambda: current_app.config.get("RATE_LIMIT_ADMIN_ME_GET", "100/minute")
    )
    def get(self):
        """Get own admin profile"""
        user_id, role, is_super = get_current_user_info()  # Get user_id
        # Add logging
        current_app.logger.debug(
            f"Received GET request for own admin profile (ID: {user_id})"
        )
        # Service allows self-access regardless of is_super
        return AdminService.get_admin_data(user_id, user_id, is_super)

    @api.doc(
        "Update own admin profile",
        security="Bearer",
        description="Update profile details for the currently logged-in admin. Cannot change Super Admin status.",
        responses={
            200: ("Success", data_resp),
            400: "Validation Error/Empty Body",
            401: "Unauthorized",
            403: "Forbidden",  # Added 403
            404: "Not Found",
            409: "Conflict",  # Added 409
            500: "Internal Server Error",
        },
    )
    @api.expect(admin_self_update_input, validate=True)
    @jwt_required()
    @roles_required("admin")  # Base role check sufficient
    # Use config for rate limit
    @limiter.limit(
        lambda: current_app.config.get("RATE_LIMIT_ADMIN_ME_UPDATE", "30/minute")
    )
    def put(self):
        """Update own admin profile"""
        user_id, _, _ = get_current_user_info()  # Only need user_id
        data = request.get_json()
        # Add logging
        current_app.logger.debug(
            f"Received PUT request for own admin profile (ID: {user_id}) with data: {data}"
        )
        # Call the specific service method for self-update
        return AdminService.update_own_profile(user_id, data)
