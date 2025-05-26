from flask import request, current_app
from flask_restx import Resource
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt

from app.extensions import limiter
from app.api.decorators import roles_required

from .service import GroupService
from .dto import GroupDto
# Removed User import, assuming teacher_id from query param is used directly by service if provided.

api = GroupDto.api
data_resp = GroupDto.data_resp
list_data_resp = GroupDto.list_data_resp
group_create_dto = GroupDto.group_create
group_update_dto = GroupDto.group_update
group_filter_parser = GroupDto.group_filter_parser


@api.route("/")
class GroupList(Resource):

    @api.doc(
        "List all groups",
        security="Bearer",
        responses={
            200: ("Success", list_data_resp),
            401: "Unauthorized",
            403: "Forbidden",
            429: "Too Many Requests",
            500: "Internal Server Error",
        },
        parser=group_filter_parser,
    )
    @jwt_required()
    @roles_required("admin", "teacher", "student", "parent")
    @limiter.limit(lambda: current_app.config.get("RATE_LIMIT_GROUP_LIST", "50/minute"))
    def get(self):
        """Get a list of all groups, optionally filtered by level_id, teacher_id, and module_id."""
        args = group_filter_parser.parse_args()
        level_id = args.get("level_id")
        teacher_id_filter = args.get("teacher_id")
        module_id_filter = args.get("module_id") # Extract module_id
        page = args.get("page")
        per_page = args.get("per_page")

        current_user_id = get_jwt_identity()
        current_user_role = get_jwt().get("role")

        current_app.logger.debug(
            f"User {current_user_id} ({current_user_role}) GET request for groups with args: {args}"
        )

        # The controller now simply passes all filter arguments.
        # The service layer will handle the logic of applying them.
        # If a teacher is logged in, and they want to see groups for their modules,
        # the client would provide teacher_id (their own) and optionally module_id.
        return GroupService.get_all_groups(
            level_id=level_id,
            teacher_id=teacher_id_filter,
            module_id=module_id_filter, # Pass module_id to the service
            page=page,
            per_page=per_page,
        )

    @api.doc(
        "Create a new group (Admin only)",
        security="Bearer",
        responses={
            201: ("Created", data_resp),
            400: "Validation Error",
            401: "Unauthorized",
            403: "Forbidden",
            409: "Conflict (e.g. duplicate group name in level)",
            429: "Too Many Requests",
            500: "Internal Server Error",
        },
    )
    @api.expect(group_create_dto, validate=True)
    @jwt_required()
    @roles_required("admin")
    @limiter.limit(lambda: current_app.config.get("RATE_LIMIT_GROUP_CREATE", "10/minute"))
    def post(self):
        """Create a new group (Admin only)."""
        data = request.get_json()
        current_app.logger.debug(f"Received POST request to create group with data: {data}")
        return GroupService.create_group(data)


@api.route("/<int:group_id>")
@api.param("group_id", "The unique identifier of the group")
class GroupResource(Resource):

    @api.doc(
        "Get a specific group by ID",
        security="Bearer",
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
    @roles_required("admin", "teacher", "parent", "student")
    @limiter.limit(lambda: current_app.config.get("RATE_LIMIT_GROUP_GET", "100/minute"))
    def get(self, group_id: int):
        """Get a specific group's data by its ID."""
        current_user_id = get_jwt_identity()
        current_user_role = get_jwt()["role"]
        current_app.logger.debug(f"User {current_user_id} ({current_user_role}) GET request for group ID: {group_id}")
        return GroupService.get_group_data(group_id , current_user_id, current_user_role)


    @api.doc(
        "Update a group (Admin only)",
        security="Bearer",
        responses={
            200: ("Success", data_resp),
            400: "Validation Error",
            401: "Unauthorized",
            403: "Forbidden",
            404: "Not Found",
            409: "Conflict (e.g. duplicate group name in level)",
            429: "Too Many Requests",
            500: "Internal Server Error",
        },
    )
    @api.expect(group_update_dto, validate=True)
    @jwt_required()
    @roles_required("admin")
    @limiter.limit(lambda: current_app.config.get("RATE_LIMIT_GROUP_UPDATE", "30/minute"))
    def put(self, group_id: int):
        """Update an existing group (Admin only)."""
        data = request.get_json()
        current_app.logger.debug(f"Received PUT request for group ID {group_id} with data: {data}")
        return GroupService.update_group(group_id, data)

    @api.doc(
        "Delete a group (Admin only)",
        security="Bearer",
        responses={
            204: "No Content - Success",
            401: "Unauthorized",
            403: "Forbidden",
            404: "Not Found",
            409: "Conflict (e.g., cannot delete if students/sessions exist)",
            429: "Too Many Requests",
            500: "Internal Server Error",
        },
    )
    @jwt_required()
    @roles_required("admin")
    @limiter.limit(lambda: current_app.config.get("RATE_LIMIT_GROUP_DELETE", "10/minute"))
    def delete(self, group_id: int):
        """Delete a group (Admin only)."""
        current_app.logger.debug(f"Received DELETE request for group ID: {group_id}")
        return GroupService.delete_group(group_id)
