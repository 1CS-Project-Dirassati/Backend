from flask import request, current_app
from flask_restx import Resource
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt

# Import shared extensions/decorators
from app.extensions import limiter
from app.api.decorators import roles_required

# Import module-specific modules
from .service import ModuleService
from .dto import ModuleDto

# Get the API namespace and DTOs
api = ModuleDto.api
data_resp = ModuleDto.data_resp
list_data_resp = ModuleDto.list_data_resp
module_create_input = ModuleDto.module_create_input
module_update_input = ModuleDto.module_update_input
module_filter_parser = ModuleDto.module_filter_parser


# --- Helper to get current user info ---
def get_current_user_info():
    user_id = get_jwt_identity()
    claims = get_jwt()
    role = claims.get("role")
    current_app.logger.debug(
        f"Current user info: ID={user_id}, Role={role}"
    )  # Log user info
    return user_id, role


# --- Route for listing/creating modules ---
@api.route("/")
class ModuleList(Resource):

    @api.doc(
        "List modules",
        security="Bearer",
        parser=module_filter_parser,
        description="Get a list of modules. Filterable by name, description, teacher_id, and level_id.",
        responses={
            200: ("Success", list_data_resp),
            401: "Unauthorized",
            403: "Forbidden",
            429: "Too Many Requests",
            500: "Internal Server Error",
        },
    )
    @jwt_required()
    @roles_required("admin", "teacher")  # Example roles allowed
    @limiter.limit("60/minute")
    def get(self):
        """Get a list of modules, filtered by query params"""
        user_id, role = get_current_user_info()
        args = module_filter_parser.parse_args()
        current_app.logger.debug(
            f"Received GET request for modules list with args: {args}"
        )
        return ModuleService.get_all_modules(
            name=args.get("name"),
            description=args.get("description"),
            teacher_id=args.get("teacher_id"),
            level_id=args.get("level_id"),
            page=args.get("page"),
            per_page=args.get("per_page"),
            current_user_id=user_id,
            current_user_role=role,
        )

    @api.doc(
        "Create a new module",
        security="Bearer",
        description="Create a new module (Admin only).",
        responses={
            201: ("Created", data_resp),
            400: "Validation Error/Invalid Data",
            401: "Unauthorized",
            403: "Forbidden",
            429: "Too Many Requests",
            500: "Internal Server Error",
        },
    )
    @api.expect(module_create_input, validate=True)
    @jwt_required()
    @roles_required("admin")  # Only admins can create
    @limiter.limit("30/minute")
    def post(self):
        """Create a new module"""
        user_id, role = get_current_user_info()
        data = request.get_json()
        current_app.logger.debug(
            f"Received POST request to create module with data: {data}"
        )
        return ModuleService.create_module(data, user_id, role)


# --- Route for specific module operations ---
@api.route("/<int:module_id>")
@api.param("module_id", "The unique identifier of the module")
class ModuleResource(Resource):

    @api.doc(
        "Get a specific module by ID",
        security="Bearer",
        description="Get data for a specific module.",
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
    @roles_required("admin", "teacher")  # Example roles allowed
    @limiter.limit("100/minute")
    def get(self, module_id):
        """Get a specific module's data by ID"""
        user_id, role = get_current_user_info()
        current_app.logger.debug(f"Received GET request for module ID: {module_id}")
        return ModuleService.get_module_data(module_id, user_id, role)

    @api.doc(
        "Update a module",
        security="Bearer",
        description="Update details of a module (Admin only).",
        responses={
            200: ("Success", data_resp),
            400: "Validation Error/Invalid Data",
            401: "Unauthorized",
            403: "Forbidden",
            404: "Not Found",
            429: "Too Many Requests",
            500: "Internal Server Error",
        },
    )
    @api.expect(module_update_input, validate=True)
    @jwt_required()
    @roles_required("admin")  # Only admins can update
    @limiter.limit("40/minute")
    def put(self, module_id):
        """Update details of a module"""
        user_id, role = get_current_user_info()
        data = request.get_json()
        current_app.logger.debug(
            f"Received PUT request for module ID {module_id} with data: {data}"
        )
        return ModuleService.update_module(module_id, data, user_id, role)

    @api.doc(
        "Delete a module",
        security="Bearer",
        description="Delete a module (Admin only).",
        responses={
            204: "No Content - Success",
            401: "Unauthorized",
            403: "Forbidden",
            404: "Not Found",
            429: "Too Many Requests",
            500: "Internal Server Error",
        },
    )
    @jwt_required()
    @roles_required("admin")  # Only admins can delete
    @limiter.limit("20/minute")
    def delete(self, module_id):
        """Delete a module"""
        user_id, role = get_current_user_info()
        current_app.logger.debug(f"Received DELETE request for module ID: {module_id}")
        return ModuleService.delete_module(module_id, user_id, role)


# --- Route for teacher assignment operations ---
@api.route("/<int:module_id>/teachers/<int:teacher_id>")
@api.param("module_id", "The unique identifier of the module")
@api.param("teacher_id", "The unique identifier of the teacher")
class ModuleTeacherAssignment(Resource):

    @api.doc(
        "Assign a teacher to a module",
        security="Bearer",
        description="Assign a teacher to a module (Admin only).",
        responses={
            201: "Created - Success",
            401: "Unauthorized",
            403: "Forbidden",
            404: "Not Found",
            409: "Conflict - Teacher already assigned",
            429: "Too Many Requests",
            500: "Internal Server Error",
        },
    )
    @jwt_required()
    @roles_required("admin")
    @limiter.limit("30/minute")
    def post(self, module_id, teacher_id):
        """Assign a teacher to a module (Admin only)"""
        return ModuleService.assign_teacher(module_id, teacher_id)

    @api.doc(
        "Remove a teacher from a module",
        security="Bearer",
        description="Remove a teacher from a module (Admin only).",
        responses={
            204: "No Content - Success",
            401: "Unauthorized",
            403: "Forbidden",
            404: "Not Found",
            429: "Too Many Requests",
            500: "Internal Server Error",
        },
    )
    @jwt_required()
    @roles_required("admin")
    @limiter.limit("30/minute")
    def delete(self, module_id, teacher_id):
        """Remove a teacher from a module (Admin only)"""
        return ModuleService.remove_teacher(module_id, teacher_id)
