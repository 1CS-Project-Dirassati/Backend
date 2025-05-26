from flask import request, current_app
from flask_restx import Resource
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt

from app.extensions import limiter
from app.api.decorators import roles_required

from .service import ParentService
from .dto import ParentDto

api = ParentDto.api
data_resp = ParentDto.data_resp
list_data_resp = ParentDto.list_data_resp
parent_create_input = ParentDto.parent_create_input
parent_admin_update_input = ParentDto.parent_admin_update_input
parent_self_update_input = ParentDto.parent_self_update_input
parent_filter_parser = ParentDto.parent_filter_parser


def get_current_user_info():
    user_id = get_jwt_identity()
    claims = get_jwt()
    role = claims.get("role")
    current_app.logger.debug(f"Current user info: ID={user_id}, Role={role}")
    return user_id, role


@api.route("/")
class ParentList(Resource):

    @api.doc(
        "List parents (Admin or Teacher)",
        security="Bearer",
        parser=parent_filter_parser,
        description="Get a paginated list of parents. Filterable by verification status, student ID, teacher ID, and archived status.",  # Updated
        responses={
            200: ("Success", list_data_resp),
            401: "Unauthorized",
            403: "Forbidden",
            429: "Too Many Requests",
            500: "Internal Server Error",
        },
    )
    @jwt_required()
    @roles_required("admin", "teacher")
    @limiter.limit(
        lambda: current_app.config.get("RATE_LIMIT_PARENT_LIST", "50/minute")
    )
    def get(self):
        """Get a paginated list of all parents (Admin and teacher)"""
        user_id, role = get_current_user_info()
        args = parent_filter_parser.parse_args()
        current_app.logger.debug(
            f"Received GET request for parents list with args: {args}"
        )

        return ParentService.get_all_parents(
            is_email_verified=args.get("is_email_verified"),
            is_phone_verified=args.get("is_phone_verified"),
            student_id=args.get("student_id"),
            teacher_id=args.get("teacher_id"),
            archived=args.get("archived", 0),  # ADDED archived argument
            page=args.get("page"),
            per_page=args.get("per_page"),
            current_user_role=role,
        )

    @api.doc(
        "Create a new parent (Admin only)",
        security="Bearer",
        description="Create a new parent account (Admin only). Parent will be active (not archived).",  # Updated
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
    @roles_required("admin")
    @limiter.limit(
        lambda: current_app.config.get("RATE_LIMIT_PARENT_CREATE", "10/minute")
    )
    def post(self):
        """Create a new parent account (Admin only)"""
        data = request.get_json()
        current_app.logger.debug(
            f"Received POST request to create parent with data: {data}"
        )
        return ParentService.create_parent(data)


@api.route("/<int:parent_id>")
@api.param("parent_id", "The unique identifier of the parent")
class ParentResource(Resource):

    @api.doc(
        "Get a specific parent by ID",
        security="Bearer",
        description="Get data for a specific parent. Access restricted. Archived parents might not be directly accessible.",  # Updated
        responses={
            200: ("Success", data_resp),
            401: "Unauthorized",
            403: "Forbidden",
            404: "Not Found (or archived and not permitted to view)",  # Updated
            429: "Too Many Requests",
            500: "Internal Server Error",
        },
    )
    @jwt_required()
    @roles_required("admin", "parent", "teacher")
    @limiter.limit(
        lambda: current_app.config.get("RATE_LIMIT_PARENT_GET", "100/minute")
    )
    def get(self, parent_id: int):
        """Get a specific parent's data by ID (Admin, Teacher, or self)"""
        current_app.logger.debug(f"Received GET request for parent ID: {parent_id}")
        user_id = get_jwt_identity()
        claims = get_jwt()
        role = claims["role"]
        return ParentService.get_parent_data(parent_id, user_id, role)

    @api.doc(
        "Update a parent (Admin only)",
        security="Bearer",
        description="Update limited fields for a parent (Admin access required). Cannot unarchive via this endpoint.",  # Updated
        responses={
            200: ("Success", data_resp),
            400: "Validation Error/Empty Body",
            401: "Unauthorized",
            403: "Forbidden",
            404: "Not Found (or archived)",  # Updated
            409: "Conflict",
            429: "Too Many Requests",
            500: "Internal Server Error",
        },
    )
    @api.expect(parent_admin_update_input, validate=True)
    @jwt_required()
    @roles_required("admin")
    @limiter.limit(
        lambda: current_app.config.get("RATE_LIMIT_PARENT_ADMIN_UPDATE", "30/minute")
    )
    def put(self, parent_id: int):
        """Update an existing parent (Admin only)"""
        data = request.get_json()
        current_app.logger.debug(
            f"Received PUT request by admin for parent ID {parent_id} with data: {data}"
        )
        return ParentService.update_parent_by_admin(parent_id, data)

    @api.doc(
        "Archive a parent (Admin only)",  # CHANGED from Delete to Archive
        security="Bearer",
        description="Archive a parent's profile and all their associated students (Admin access required). This is a soft delete.",  # CHANGED
        responses={
            200: (
                "Success - Parent and associated students archived",
                data_resp,
            ),  # CHANGED to 200 and data_resp
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
        lambda: current_app.config.get(
            "RATE_LIMIT_PARENT_ARCHIVE", "5/minute"
        )  # New limit key
    )
    def delete(self, parent_id: int):  # Method name remains DELETE for REST convention
        """Archive a parent and their students (Admin only) - Soft Delete"""
        current_app.logger.warning(
            f"Received DELETE (archive) request by admin for parent ID: {parent_id}"
        )
        return ParentService.archive_parent(parent_id)  # CHANGED service call


@api.route("/<int:parent_id>/unarchive")  # NEW ROUTE
@api.param("parent_id", "The unique identifier of the parent to unarchive")
class ParentUnarchive(Resource):
    @api.doc(
        "Unarchive a parent (Admin only)",
        security="Bearer",
        description="Unarchive a parent's profile. This does NOT automatically unarchive their students. (Admin access required).",
        responses={
            200: ("Success - Parent Unarchived", data_resp),
            400: "Bad Request (e.g., parent not archived)",
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
        lambda: current_app.config.get(
            "RATE_LIMIT_PARENT_UNARCHIVE", "5/minute"
        )  # New rate limit key
    )
    def post(self, parent_id: int):  # Using POST for action
        """Unarchive a parent (Admin only)."""
        current_app.logger.info(
            f"Received POST (unarchive) request by Admin for parent ID: {parent_id}"
        )
        return ParentService.unarchive_parent(parent_id)


@api.route("/me")
class ParentProfile(Resource):

    @api.doc(
        "Get own parent profile",
        security="Bearer",
        description="Get the profile data for the currently logged-in parent. Returns 404 if parent is archived.",  # Updated
        responses={
            200: ("Success", data_resp),
            401: "Unauthorized",
            403: "Forbidden",
            404: "Not Found (or archived)",  # Updated
            500: "Internal Server Error",
        },
    )
    @jwt_required()
    @roles_required("parent")
    @limiter.limit(
        lambda: current_app.config.get("RATE_LIMIT_PARENT_ME_GET", "100/minute")
    )
    def get(self):
        """Get own parent profile"""
        user_id = get_jwt_identity()
        role = get_jwt()["role"]
        current_app.logger.debug(
            f"Received GET request for own parent profile (ID: {user_id})"
        )
        return ParentService.get_parent_data(
            user_id, user_id, role
        )  # get_parent_data will handle archived check

    @api.doc(
        "Update own parent profile",
        security="Bearer",
        description="Update profile details for the currently logged-in parent. Fails if parent is archived.",  # Updated
        responses={
            200: ("Success", data_resp),
            400: "Validation Error/Empty Body",
            401: "Unauthorized",
            403: "Forbidden (or parent archived)",  # Updated
            404: "Not Found",  # Should be caught by service if archived
            409: "Conflict",
            500: "Internal Server Error",
        },
    )
    @api.expect(parent_self_update_input, validate=True)
    @jwt_required()
    @roles_required("parent")
    @limiter.limit(
        lambda: current_app.config.get("RATE_LIMIT_PARENT_ME_UPDATE", "30/minute")
    )
    def put(self):
        """Update own parent profile"""
        user_id, _ = get_current_user_info()
        data = request.get_json()
        current_app.logger.debug(
            f"Received PUT request for own parent profile (ID: {user_id}) with data: {data}"
        )
        return ParentService.update_own_profile(user_id, data)
