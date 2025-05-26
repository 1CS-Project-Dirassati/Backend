from flask import request, current_app
from flask_restx import Resource
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt

from app.extensions import limiter
from app.api.decorators import roles_required

from .service import TeacherService
from .dto import TeacherDto

api = TeacherDto.api
data_resp = TeacherDto.data_resp
list_data_resp = TeacherDto.list_data_resp
teacher_create_input = TeacherDto.teacher_create_input
teacher_admin_update_input = TeacherDto.teacher_admin_update_input
teacher_self_update_input = TeacherDto.teacher_self_update_input
teacher_filter_parser = TeacherDto.teacher_filter_parser

def get_current_user_info():
    user_id = get_jwt_identity()
    claims = get_jwt()
    role = claims.get("role")
    current_app.logger.debug(f"Current user info: ID={user_id}, Role={role}")
    return user_id, role

@api.route("/")
class TeacherList(Resource):

    @api.doc(
        "List teachers",
        security="Bearer",
        parser=teacher_filter_parser,
        description="Get a paginated list of teachers. Filterable by module and archived status. Access restricted by role. Non-admins typically see only active teachers.",
        responses={
            200: ("Success", list_data_resp),
            401: "Unauthorized",
            403: "Forbidden",
            429: "Too Many Requests",
            500: "Internal Server Error",
        },
    )
    @jwt_required()
    @roles_required("admin", "teacher", "parent")
    @limiter.limit("50/minute")
    def get(self):
        """Get a paginated list of all teachers, respecting archive status and user role."""
        user_id, role = get_current_user_info()
        args = teacher_filter_parser.parse_args()
        current_app.logger.debug(
            f"Received GET request for teachers list with args: {args} by User {user_id} ({role})"
        )
        return TeacherService.get_all_teachers(
            module_id=args.get("module_id"),
            archived=args.get("archived",0),
            page=args.get("page"),
            per_page=args.get("per_page"),
            current_user_role=role,
            current_user_id=user_id
        )

    @api.doc(
        "Create a new teacher (Admin only)",
        security="Bearer",
        description="Create a new teacher account (Admin only). Teacher will be active (not archived) by default.",
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
    @roles_required("admin")
    @limiter.limit("10/minute")
    def post(self):
        """Create a new teacher account (Admin only)."""
        data = request.get_json()
        current_app.logger.debug(
            f"Received POST request to create teacher with data: {data}"
        )
        return TeacherService.create_teacher(data)


@api.route("/<int:teacher_id>")
@api.param("teacher_id", "The unique identifier of the teacher")
class TeacherResource(Resource):

    @api.doc(
        "Get a specific teacher by ID",
        security="Bearer",
        description="Get data for a specific teacher. Access restricted. Admins and the teacher themselves can view their profile even if archived. Other roles typically only see active teachers.",
        responses={
            200: ("Success", data_resp),
            401: "Unauthorized",
            403: "Forbidden",
            404: "Not Found (or archived and not permitted)",
            429: "Too Many Requests",
            500: "Internal Server Error",
        },
    )
    @jwt_required()
    @roles_required("admin", "teacher", "parent")
    @limiter.limit(
        lambda: current_app.config.get("RATE_LIMIT_TEACHER_GET", "100/minute")
    )
    def get(self, teacher_id: int):
        """Get a specific teacher's data by ID, respecting archive status and user role."""
        user_id = get_jwt_identity()
        role = get_jwt()["role"]
        current_app.logger.debug(f"Received GET request for teacher ID: {teacher_id} by User {user_id} ({role})")
        return TeacherService.get_teacher_data(teacher_id, user_id, role)

    @api.doc(
        "Update a teacher (Admin only)",
        security="Bearer",
        description="Update limited fields for an active teacher (Admin access required). This endpoint cannot be used to change archive status.",
        responses={
            200: ("Success", data_resp),
            400: "Validation Error/Empty Body",
            401: "Unauthorized",
            403: "Forbidden",
            404: "Not Found (or teacher is archived)",
            409: "Conflict",
            429: "Too Many Requests",
            500: "Internal Server Error",
        },
    )
    @api.expect(teacher_admin_update_input, validate=True)
    @jwt_required()
    @roles_required("admin")
    @limiter.limit("30/minute")
    def put(self, teacher_id: int):
        """Update an existing active teacher's profile (Admin only)."""
        data = request.get_json()
        current_app.logger.debug(
            f"Received PUT request by admin for teacher ID {teacher_id} with data: {data}"
        )
        return TeacherService.update_teacher_by_admin(teacher_id, data)

    @api.doc(
        "Archive a teacher (Admin only)",
        security="Bearer",
        description="Archive a teacher's profile (Admin access required). This performs a soft delete, marking the teacher as archived.",
        responses={
            200: ("Success - Teacher Archived", data_resp),
            401: "Unauthorized",
            403: "Forbidden",
            404: "Not Found",
            429: "Too Many Requests",
            500: "Internal Server Error",
        },
    )
    @jwt_required()
    @roles_required("admin")
    @limiter.limit( lambda: current_app.config.get("RATE_LIMIT_TEACHER_ARCHIVE", "5/minute"))
    def delete(self, teacher_id: int):
        """Archive a teacher's profile (Admin only) - Soft Delete."""
        current_app.logger.warning(
            f"Received DELETE (archive) request by admin for teacher ID: {teacher_id}"
        )
        return TeacherService.archive_teacher(teacher_id)

@api.route("/<int:teacher_id>/unarchive")
@api.param("teacher_id", "The unique identifier of the teacher to unarchive")
class TeacherUnarchive(Resource):
    @api.doc(
        "Unarchive a teacher (Admin only)",
        security="Bearer",
        description="Unarchive a teacher's profile, making them active again (Admin access required).",
        responses={
            200: ("Success - Teacher Unarchived", data_resp),
            400: "Bad Request (e.g., teacher not archived or email conflict)",
            401: "Unauthorized",
            403: "Forbidden",
            404: "Not Found",
            429: "Too Many Requests",
            500: "Internal Server Error",
        },
    )
    @jwt_required()
    @roles_required("admin")
    @limiter.limit( lambda: current_app.config.get("RATE_LIMIT_TEACHER_UNARCHIVE", "5/minute"))
    def post(self, teacher_id: int):
        """Unarchive a teacher's profile (Admin only)."""
        current_app.logger.info(
            f"Received POST (unarchive) request by Admin for teacher ID: {teacher_id}"
        )
        return TeacherService.unarchive_teacher(teacher_id)


@api.route("/me")
class TeacherProfile(Resource):

    @api.doc(
        "Get own teacher profile",
        security="Bearer",
        description="Get the profile data for the currently logged-in teacher. Accessible even if the profile is archived (for self-view).",
        responses={
            200: ("Success", data_resp),
            401: "Unauthorized",
            403: "Forbidden", # Should not happen if role is 'teacher'
            404: "Not Found", # If somehow user ID from token does not match a teacher
            500: "Internal Server Error",
        },
    )
    @jwt_required()
    @roles_required("teacher")
    @limiter.limit(
        lambda: current_app.config.get("RATE_LIMIT_TEACHER_ME_GET", "100/minute")
    )
    def get(self):
        """Get the currently logged-in teacher's own profile data."""
        user_id = get_jwt_identity()
        role = get_jwt()["role"] # Role is 'teacher' due to decorator
        current_app.logger.debug(
            f"Received GET request for own teacher profile (ID: {user_id})"
        )
        return TeacherService.get_teacher_data(user_id, user_id, role)

    @api.doc(
        "Update own teacher profile",
        security="Bearer",
        description="Update profile details for the currently logged-in, active teacher. Cannot be used if profile is archived.",
        responses={
            200: ("Success", data_resp),
            400: "Validation Error/Empty Body",
            401: "Unauthorized",
            403: "Forbidden (e.g., if teacher is archived)",
            404: "Not Found", # Should not happen if JWT is valid
            409: "Conflict",
            500: "Internal Server Error",
        },
    )
    @api.expect(teacher_self_update_input, validate=True)
    @jwt_required()
    @roles_required("teacher")
    @limiter.limit(
        lambda: current_app.config.get("RATE_LIMIT_TEACHER_ME_UPDATE", "30/minute")
    )
    def put(self):
        """Update the currently logged-in teacher's own profile details."""
        user_id, _ = get_current_user_info()
        data = request.get_json()
        current_app.logger.debug(
            f"Received PUT request for own teacher profile (ID: {user_id}) with data: {data}"
        )
        return TeacherService.update_own_profile(user_id, data)

@api.route("/<int:teacher_id>/modules/<int:module_id>")
@api.param("teacher_id", "The Teacher's unique identifier")
@api.param("module_id", "The Module's unique identifier")
class TeacherModuleManagement(Resource):
    @api.doc(
        "Assign module to teacher (Admin only)",
        security="Bearer",
        description="Assign a module to an active teacher (Admin access required)."
    )
    @jwt_required()
    @roles_required("admin")
    @limiter.limit("20/minute")
    def post(self, teacher_id: int, module_id: int):
        """Assign a module to an active teacher."""
        current_app.logger.info(f"Admin assigning module {module_id} to teacher {teacher_id}")
        return TeacherService.assign_module(teacher_id, module_id)

    @api.doc(
        "Remove module from teacher (Admin only)",
        security="Bearer",
        description="Remove a module assignment from a teacher (Admin access required). This can be done for active or archived teachers as a cleanup action."
    )
    @jwt_required()
    @roles_required("admin")
    @limiter.limit("20/minute")
    def delete(self, teacher_id: int, module_id: int):
        """Remove a module assignment from a teacher."""
        current_app.logger.info(f"Admin removing module {module_id} from teacher {teacher_id}")
        return TeacherService.remove_module(teacher_id, module_id)
