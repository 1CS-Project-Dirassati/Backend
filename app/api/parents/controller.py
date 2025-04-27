# Added current_app
from flask import request, current_app
from flask_restx import Resource
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt

# Import shared extensions/decorators
from app.extensions import limiter
from app.api.decorators import roles_required

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
# Get the filter/pagination parser
parent_filter_parser = ParentDto.parent_filter_parser


# --- Helper to get current user info ---
def get_current_user_info():
    user_id = get_jwt_identity()
    claims = get_jwt()
    role = claims.get("role")
    current_app.logger.debug(
        f"Current user info: ID={user_id}, Role={role}"
    )  # Log user info
    return user_id, role


# --- Route for listing/creating parents (Admin focused) ---
@api.route("/")
class ParentList(Resource):

    @api.doc(
        "List parents (Admin only)",
        security="Bearer",
        parser=parent_filter_parser,
        # Updated description
        description="Get a paginated list of all parents. Filterable by verification status. (Admin access required)",
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
    # Use config for rate limit
    @limiter.limit(
        lambda: current_app.config.get("RATE_LIMIT_PARENT_LIST", "50/minute")
    )
    def get(self):
        """Get a paginated list of all parents (Admin only)"""
        user_id, role = (
            get_current_user_info()
        )  # Role needed for service check (though redundant here due to decorator)
        args = parent_filter_parser.parse_args()
        # Add logging
        current_app.logger.debug(
            f"Received GET request for parents list with args: {args}"
        )

        # Pass pagination args and role
        return ParentService.get_all_parents(
            is_email_verified=args.get("is_email_verified"),
            is_phone_verified=args.get("is_phone_verified"),
            page=args.get("page"),
            per_page=args.get("per_page"),
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
    @roles_required("admin")  # Decorator handles role check
    # Use config for rate limit
    @limiter.limit(
        lambda: current_app.config.get("RATE_LIMIT_PARENT_CREATE", "10/minute")
    )
    def post(self):
        """Create a new parent account (Admin only)"""
        # No need to get user info, decorator handles role
        data = request.get_json()
        # Add logging
        current_app.logger.debug(
            f"Received POST request to create parent with data: {data}"
        )
        # Service method no longer needs role
        return ParentService.create_parent(data)


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
    @roles_required("admin", "parent")  # Decorator handles role check
    # Use config for rate limit
    @limiter.limit(
        lambda: current_app.config.get("RATE_LIMIT_PARENT_GET", "100/minute")
    )
    # Add type hint
    def get(self, parent_id: int):
        """Get a specific parent's data by ID (Admin or self)"""
        # Get user info for record-level access check in service
        # Add logging
        current_app.logger.debug(f"Received GET request for parent ID: {parent_id}")
        user_id = get_jwt_identity()
        role = get_jwt()["role"]
        # Pass user info for record-level check
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
            409: "Conflict",  # Added 409
            429: "Too Many Requests",
            500: "Internal Server Error",
        },
    )
    @api.expect(parent_admin_update_input, validate=True)
    @jwt_required()
    @roles_required("admin")  # Decorator handles role check
    # Use config for rate limit
    @limiter.limit(
        lambda: current_app.config.get("RATE_LIMIT_PARENT_ADMIN_UPDATE", "30/minute")
    )
    # Add type hint
    def put(self, parent_id: int):
        """Update an existing parent (Admin only)"""
        # No need to get user info, decorator handles role
        data = request.get_json()
        # Add logging
        current_app.logger.debug(
            f"Received PUT request by admin for parent ID {parent_id} with data: {data}"
        )
        # Service method no longer needs role
        return ParentService.update_parent_by_admin(parent_id, data)

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
    @roles_required("admin")  # Decorator handles role check
    # Use config for rate limit
    @limiter.limit(
        lambda: current_app.config.get("RATE_LIMIT_PARENT_DELETE", "5/minute")
    )
    # Add type hint
    def delete(self, parent_id: int):
        """Delete a parent (Admin only) - WARNING: Cascades to students etc."""
        # No need to get user info, decorator handles role
        # Add logging
        current_app.logger.debug(
            f"Received DELETE request by admin for parent ID: {parent_id}"
        )
        # Service method no longer needs role
        return ParentService.delete_parent(parent_id)


# --- Route specifically for parent managing their own profile ---
@api.route("/me")
class ParentProfile(Resource):

    @api.doc(
        "Get own parent profile",
        security="Bearer",
        description="Get the profile data for the currently logged-in parent.",
        responses={
            200: ("Success", data_resp),
            401: "Unauthorized",
            403: "Forbidden",  # Added 403 (if somehow non-parent gets here)
            404: "Not Found",
            500: "Internal Server Error",
        },
    )
    @jwt_required()
    @roles_required("parent")  # Decorator handles role check
    # Use config for rate limit
    @limiter.limit(
        lambda: current_app.config.get("RATE_LIMIT_PARENT_ME_GET", "100/minute")
    )
    def get(self):
        """Get own parent profile"""
        # Add logging
        user_id = get_jwt_identity()
        role = get_jwt()["role"]  # Get the role from the JWT token
        current_app.logger.debug(
            f"Received GET request for own parent profile (ID: {user_id})"
        )
        # Use the same get_parent_data service method, passing own ID and role
        return ParentService.get_parent_data(user_id, user_id, role)

    @api.doc(
        "Update own parent profile",
        security="Bearer",
        description="Update profile details for the currently logged-in parent.",
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
    @api.expect(parent_self_update_input, validate=True)
    @jwt_required()
    @roles_required("parent")  # Decorator handles role check
    # Use config for rate limit
    @limiter.limit(
        lambda: current_app.config.get("RATE_LIMIT_PARENT_ME_UPDATE", "30/minute")
    )
    def put(self):
        """Update own parent profile"""
        user_id, _ = get_current_user_info()  # Don't need role here
        data = request.get_json()
        # Add logging
        current_app.logger.debug(
            f"Received PUT request for own parent profile (ID: {user_id}) with data: {data}"
        )
        # Call the specific service method for self-update
        return ParentService.update_own_profile(user_id, data)
