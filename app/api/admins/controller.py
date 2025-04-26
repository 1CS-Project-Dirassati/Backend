from flask import request
from flask_restx import Resource
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt

# Import shared extensions/decorators
from app.extensions import limiter
from app.api.decorators import roles_required  # Should check for 'admin' role

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
admin_filter_parser = AdminDto.admin_filter_parser


# --- Helper to get current user info (including super admin status) ---
def get_current_user_info():
    user_id = get_jwt_identity()
    claims = get_jwt()
    role = claims.get("role")
    # IMPORTANT: Assumes 'is_super_admin' boolean claim exists in JWT
    is_super = claims.get("is_super_admin", False)
    return user_id, role, is_super


# --- Route for listing/creating admins (Super Admin focused) ---
@api.route("/")
class AdminList(Resource):

    @api.doc(
        "List admins (Super Admin only)",
        security="Bearer",
        parser=admin_filter_parser,
        description="Get a list of all admins. Filterable by super admin status. (Super Admin access required)",
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
    @limiter.limit("50/minute")
    def get(self):
        """Get a list of all admins (Super Admin only)"""
        user_id, role, is_super = get_current_user_info()
        args = admin_filter_parser.parse_args()

        # Service layer performs the super admin check
        return AdminService.get_all_admins(
            is_super_admin_filter=args.get("is_super_admin"),
            current_user_is_super=is_super,
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
    @limiter.limit("10/minute")
    def post(self):
        """Create a new admin account (Super Admin only)"""
        user_id, role, is_super = get_current_user_info()
        data = request.get_json()
        # Service layer performs the super admin check
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
    @limiter.limit("100/minute")
    def get(self, admin_id):
        """Get a specific admin's data by ID (Super Admin or self)"""
        user_id, role, is_super = get_current_user_info()
        # Service layer handles the authorization check
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
    @limiter.limit("30/minute")
    def put(self, admin_id):
        """Update an existing admin (Super Admin only)"""
        user_id, role, is_super = get_current_user_info()
        data = request.get_json()
        # Service layer handles the authorization check
        return AdminService.update_admin_by_superadmin(
            admin_id, data, user_id, is_super
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
    @limiter.limit("5/minute")
    def delete(self, admin_id):
        """Delete an admin (Super Admin only) - Cannot delete self or last Super Admin"""
        user_id, role, is_super = get_current_user_info()
        # Service layer handles authorization and safety checks
        return AdminService.delete_admin(admin_id, user_id, is_super)


# --- Route specifically for admin managing their own profile ---
@api.route("/me")  # Endpoint like /api/admins/me
class AdminProfile(Resource):

    @api.doc(
        "Get own admin profile",
        security="Bearer",
        description="Get the profile data for the currently logged-in admin.",
        responses={
            200: ("Success", data_resp),
            401: "Unauthorized",
            404: "Not Found",
            500: "Internal Server Error",
        },
    )
    @jwt_required()
    @roles_required("admin")  # Any admin can get their own profile
    @limiter.limit("100/minute")
    def get(self):
        """Get own admin profile"""
        user_id, role, is_super = get_current_user_info()
        # Use the standard get_admin_data service method, passing own ID
        # The service allows self-access even if not super admin
        return AdminService.get_admin_data(user_id, user_id, is_super)

    @api.doc(
        "Update own admin profile",
        security="Bearer",
        description="Update profile details for the currently logged-in admin. Cannot change Super Admin status.",
        responses={
            200: ("Success", data_resp),
            400: "Validation Error/Empty Body",
            401: "Unauthorized",
            404: "Not Found",
            500: "Internal Server Error",
        },
    )
    @api.expect(admin_self_update_input, validate=True)
    @jwt_required()
    @roles_required("admin")  # Any admin can update their own profile
    @limiter.limit("30/minute")
    def put(self):
        """Update own admin profile"""
        user_id, role, is_super = get_current_user_info()
        data = request.get_json()
        # Call the specific service method for self-update
        return AdminService.update_own_profile(user_id, data)
