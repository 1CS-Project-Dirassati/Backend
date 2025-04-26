from flask import request
from flask_restx import Resource
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt

# Import shared extensions/decorators
from app.extensions import limiter
from app.api.decorators import roles_required  # Adjust path if necessary

# Import parent-specific modules
from .service import ParentService
from .dto import ParentDto

# Get the API namespace and DTOs
api = ParentDto.api
data_resp = ParentDto.data_resp
list_data_resp = ParentDto.list_data_resp
parent_create_input = ParentDto.parent_create_input
parent_admin_update_input = ParentDto.parent_admin_update_input
parent_self_update_input = ParentDto.parent_self_update_input
parent_filter_parser = ParentDto.parent_filter_parser


# --- Helper to get current user info ---
def get_current_user_info():
    user_id = get_jwt_identity()
    claims = get_jwt()
    role = claims.get("role")
    return user_id, role


# --- Route for listing/creating parents (Admin focused) ---
@api.route("/")
class ParentList(Resource):

    @api.doc(
        "List parents (Admin only)",
        security="Bearer",
        parser=parent_filter_parser,
        description="Get a list of all parents. Filterable by verification status. (Admin access required)",
        responses={
            200: ("Success", list_data_resp),
            401: "Unauthorized",
            403: "Forbidden",
            429: "Too Many Requests",
            500: "Internal Server Error",
        },
    )
    @jwt_required()
    @roles_required("admin")  # Only admins can list all parents
    @limiter.limit("50/minute")
    def get(self):
        """Get a list of all parents (Admin only)"""
        user_id, role = get_current_user_info()
        args = parent_filter_parser.parse_args()

        return ParentService.get_all_parents(
            is_email_verified=args.get("is_email_verified"),
            is_phone_verified=args.get("is_phone_verified"),
            current_user_role=role,
        )

    @api.doc(
        "Create a new parent (Admin only)",
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
    @api.expect(parent_create_input, validate=True)
    @jwt_required()
    @roles_required("admin")  # Only admins can create parents directly
    @limiter.limit("10/minute")
    def post(self):
        """Create a new parent account (Admin only)"""
        user_id, role = get_current_user_info()
        data = request.get_json()
        return ParentService.create_parent(data, role)


# --- Route for specific parent operations ---
@api.route("/<int:parent_id>")
@api.param("parent_id", "The unique identifier of the parent")
class ParentResource(Resource):

    @api.doc(
        "Get a specific parent by ID",
        security="Bearer",
        description="Get data for a specific parent. Access restricted to Admins or the parent themselves.",
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
    @roles_required("admin", "parent")  # Roles allowed to access this endpoint
    @limiter.limit("100/minute")
    def get(self, parent_id):
        """Get a specific parent's data by ID (Admin or self)"""
        user_id, role = get_current_user_info()
        # Service layer handles the authorization check (is user_id == parent_id or role == admin)
        return ParentService.get_parent_data(parent_id, user_id, role)

    @api.doc(
        "Update a parent (Admin only)",
        security="Bearer",
        description="Update limited fields for a parent (Admin access required).",
        responses={
            200: ("Success", data_resp),
            400: "Validation Error/Empty Body",
            401: "Unauthorized",
            403: "Forbidden",
            404: "Not Found",
            429: "Too Many Requests",
            500: "Internal Server Error",
        },
    )
    @api.expect(parent_admin_update_input, validate=True)
    @jwt_required()
    @roles_required("admin")  # Only Admin can use this endpoint
    @limiter.limit("30/minute")
    def put(self, parent_id):
        """Update an existing parent (Admin only)"""
        user_id, role = get_current_user_info()
        data = request.get_json()
        return ParentService.update_parent_by_admin(parent_id, data, role)

    @api.doc(
        "Delete a parent (Admin only)",
        security="Bearer",
        description="Delete a parent and ALL associated students, fees, notifications (Admin access required). USE WITH CAUTION.",
        responses={
            204: "No Content - Success",
            401: "Unauthorized",
            403: "Forbidden",
            404: "Not Found",
            409: "Conflict (Pre-delete checks failed)",
            429: "Too Many Requests",
            500: "Internal Server Error",
        },
    )
    @jwt_required()
    @roles_required("admin")  # Only Admin can delete
    @limiter.limit("5/minute")  # Lower limit due to destructive nature
    def delete(self, parent_id):
        """Delete a parent (Admin only) - WARNING: Cascades to students etc."""
        user_id, role = get_current_user_info()
        return ParentService.delete_parent(parent_id, role)


# --- Route specifically for parent managing their own profile ---
@api.route("/me")  # Endpoint like /api/parents/me
class ParentProfile(Resource):

    @api.doc(
        "Get own parent profile",
        security="Bearer",
        description="Get the profile data for the currently logged-in parent.",
        responses={
            200: ("Success", data_resp),
            401: "Unauthorized",
            404: "Not Found",
            500: "Internal Server Error",
        },
    )
    @jwt_required()
    @roles_required("parent")  # Only parents can access this
    @limiter.limit("100/minute")
    def get(self):
        """Get own parent profile"""
        user_id, role = get_current_user_info()
        # Use the same get_parent_data service method, passing own ID
        return ParentService.get_parent_data(user_id, user_id, role)

    @api.doc(
        "Update own parent profile",
        security="Bearer",
        description="Update profile details for the currently logged-in parent.",
        responses={
            200: ("Success", data_resp),
            400: "Validation Error/Empty Body",
            401: "Unauthorized",
            404: "Not Found",
            500: "Internal Server Error",
        },
    )
    @api.expect(parent_self_update_input, validate=True)
    @jwt_required()
    @roles_required("parent")  # Only parents can access this
    @limiter.limit("30/minute")
    def put(self):
        """Update own parent profile"""
        user_id, role = get_current_user_info()
        data = request.get_json()
        # Call the specific service method for self-update
        return ParentService.update_own_profile(user_id, data)
