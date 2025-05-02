# Added current_app
from flask import request, current_app
from flask_restx import Resource
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt

# Import shared extensions/decorators
from app.extensions import limiter
from app.api.decorators import roles_required

# Import teacher-specific modules
from .service import TeacherService
from .dto import TeacherDto

# Get the API namespace and DTOs
api = TeacherDto.api
data_resp = TeacherDto.data_resp
list_data_resp = TeacherDto.list_data_resp
teacher_create_input = TeacherDto.teacher_create_input
teacher_admin_update_input = TeacherDto.teacher_admin_update_input
teacher_self_update_input = TeacherDto.teacher_self_update_input
# Get the filter/pagination parser
teacher_filter_parser = TeacherDto.teacher_filter_parser


# --- Helper to get current user info ---
def get_current_user_info():
    user_id = get_jwt_identity()
    claims = get_jwt()
    role = claims.get("role")
    current_app.logger.debug(
        f"Current user info: ID={user_id}, Role={role}"
    )  # Log user info
    return user_id, role

# --- Route for listing/creating teachers (Admin focused) ---
@api.route("/")
class TeacherList(Resource):

    @api.doc(
        "List teachers (Admin only)",
        security="Bearer",
        parser=teacher_filter_parser,
        # Updated description
        description="Get a paginated list of all teachers. Filterable by module_key. (Admin access required)",
        responses={
            200: ("Success", list_data_resp),
            401: "Unauthorized",
            403: "Forbidden",
            429: "Too Many Requests",
            500: "Internal Server Error",
        },
    )
    @jwt_required()

    @roles_required("admin","parent","teacher")  # Only admins can list all teachers
    @limiter.limit("50/minute")
    def get(self):
        """Get a paginated list of all teachers (Admin only)"""
        user_id, role = (
            get_current_user_info()
        )  # Role needed for service check (belt-and-suspenders)
        args = teacher_filter_parser.parse_args()
        # Add logging
        current_app.logger.debug(
            f"Received GET request for teachers list with args: {args}"
        )

        # Pass pagination args and role
        return TeacherService.get_all_teachers(
            module_key=args.get("module_key"),
            page=args.get("page"),
            per_page=args.get("per_page"),
            current_user_role=role,
        )

    @api.doc(
        "Create a new teacher (Admin only)",
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
    @api.expect(teacher_create_input, validate=True)
    @jwt_required()

    @roles_required("admin","parent")  # Only admins can create teachers
    @limiter.limit("10/minute")
    def post(self):
        """Create a new teacher account (Admin only)"""
        # No need to get user info, decorator handles role
        data = request.get_json()
        # Add logging
        current_app.logger.debug(
            f"Received POST request to create teacher with data: {data}"
        )
        # Service method no longer needs role
        return TeacherService.create_teacher(data)


# --- Route for specific teacher operations ---
@api.route("/<int:teacher_id>")
@api.param("teacher_id", "The unique identifier of the teacher")
class TeacherResource(Resource):

    @api.doc(
        "Get a specific teacher by ID",
        security="Bearer",
        description="Get data for a specific teacher. Access restricted to Admins or the teacher themselves.",
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
    @roles_required("admin", "teacher")  # Decorator handles role check
    # Use config for rate limit
    @limiter.limit(
        lambda: current_app.config.get("RATE_LIMIT_TEACHER_GET", "100/minute")
    )
    # Add type hint
    def get(self, teacher_id: int):
        """Get a specific teacher's data by ID (Admin or self)"""
        # Get user info for record-level access check in service
        # Add logging
        current_app.logger.debug(f"Received GET request for teacher ID: {teacher_id}")
        # Pass user info for record-level check
        user_id = get_jwt_identity()  # Get the user ID from the JWT token
        role = get_jwt()["role"]  # Get the role from the JWT token
        return TeacherService.get_teacher_data(teacher_id, user_id, role)

    @api.doc(
        "Update a teacher (Admin only)",
        security="Bearer",
        description="Update limited fields for a teacher (Admin access required).",
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
    @api.expect(teacher_admin_update_input, validate=True)
    @jwt_required()

    @roles_required("admin","parent")  # Only Admin can use this endpoint
    @limiter.limit("30/minute")
    def put(self, teacher_id):
        """Update an existing teacher (Admin only)"""
        # No need to get user info, decorator handles role
        data = request.get_json()
        # Add logging
        current_app.logger.debug(
            f"Received PUT request by admin for teacher ID {teacher_id} with data: {data}"
        )
        # Service method no longer needs role
        return TeacherService.update_teacher_by_admin(teacher_id, data)

    @api.doc(
        "Delete a teacher (Admin only)",
        security="Bearer",
        description="Delete a teacher (Admin access required). Fails if teacher has associated modules or sessions. Cascades delete to Teachings, Cours, Notes.",
        responses={
            204: "No Content - Success",
            401: "Unauthorized",
            403: "Forbidden",
            404: "Not Found",
            409: "Conflict (Dependencies exist)",
            429: "Too Many Requests",
            500: "Internal Server Error",
        },
    )
    @jwt_required()

    @roles_required("admin","parent","teacher")  # Only Admin can delete
    @limiter.limit("5/minute")  # Lower limit due to destructive nature & checks
    def delete(self, teacher_id):
        """Delete a teacher (Admin only) - Fails on dependencies"""
        # No need to get user info, decorator handles role
        # Add logging
        current_app.logger.debug(
            f"Received DELETE request by admin for teacher ID: {teacher_id}"
        )
        # Service method no longer needs role
        return TeacherService.delete_teacher(teacher_id)


# --- Route specifically for teacher managing their own profile ---
@api.route("/me")
class TeacherProfile(Resource):

    @api.doc(
        "Get own teacher profile",
        security="Bearer",
        description="Get the profile data for the currently logged-in teacher.",
        responses={
            200: ("Success", data_resp),
            401: "Unauthorized",
            403: "Forbidden",  # Added 403
            404: "Not Found",
            500: "Internal Server Error",
        },
    )
    @jwt_required()
    @roles_required("teacher",)  # Decorator handles role check
    # Use config for rate limit
    @limiter.limit(
        lambda: current_app.config.get("RATE_LIMIT_TEACHER_ME_GET", "100/minute")
    )
    def get(self):
        """Get own teacher profile"""
        # Add logging
        # Use the same get_teacher_data service method, passing own ID and role
        user_id = get_jwt_identity()  # Get the user ID from the JWT token
        role = get_jwt()["role"]  # Get the role from the JWT token
        current_app.logger.debug(
            f"Received GET request for own teacher profile (ID: {user_id})"
        )
        return TeacherService.get_teacher_data(user_id, user_id, role)

    @api.doc(
        "Update own teacher profile",
        security="Bearer",
        description="Update profile details for the currently logged-in teacher.",
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
    @api.expect(teacher_self_update_input, validate=True)
    @jwt_required()
    @roles_required("teacher")  # Decorator handles role check
    # Use config for rate limit
    @limiter.limit(
        lambda: current_app.config.get("RATE_LIMIT_TEACHER_ME_UPDATE", "30/minute")
    )
    def put(self):
        """Update own teacher profile"""
        user_id, _ = get_current_user_info()  # Don't need role here
        data = request.get_json()
        # Add logging
        current_app.logger.debug(
            f"Received PUT request for own teacher profile (ID: {user_id}) with data: {data}"
        )
        # Call the specific service method for self-update
        return TeacherService.update_own_profile(user_id, data)
