from flask import request, current_app
from flask_restx import Resource
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt

from app.extensions import limiter
from app.api.decorators import roles_required

from .service import GroupService
from .dto import GroupDto
from app.models import User

# Get the API namespace and DTOs
api = GroupDto.api
data_resp = GroupDto.data_resp
list_data_resp = GroupDto.list_data_resp
# Add input DTOs if defined
group_create_dto = GroupDto.group_create
group_update_dto = GroupDto.group_update
group_filter_parser = (
    GroupDto.group_filter_parser  # Use the parser for query parameters
)


# Define endpoint for listing all groups and creating new ones
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
        parser=group_filter_parser,  # Add query parameter parser
    )
    @jwt_required()
    @roles_required("admin", "teacher", "student", "parent")
    @limiter.limit(lambda: current_app.config.get("RATE_LIMIT_GROUP_LIST", "50/minute"))
    def get(self):
        """Get a list of all groups"""
        args = group_filter_parser.parse_args()
        level_id = args.get("level_id")  # Extract the level_id from the parsed arguments
        page = args.get("page")  # Extract the page number for pagination
        per_page = args.get("per_page")  # Extract the number of items per page
        
        # Get current user's role and ID
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)
        current_user_role = get_jwt().get("role")
        
        current_app.logger.debug(f"Received GET request for groups with args: {args}")
        
        # Get teacher_id if current user is a teacher
        teacher_id = None
        if current_user and current_user_role == "teacher":
            teacher_id = current_user.id
            current_app.logger.debug(f"Current user is a teacher with ID: {teacher_id}")
            
        return GroupService.get_all_groups(
            level_id=level_id,
            page=page,
            per_page=per_page,
            teacher_id=teacher_id
        )

    @api.doc(
        "Create a new group",
        security="Bearer",
        responses={
            201: ("Created", data_resp),
            400: "Validation Error",
            401: "Unauthorized",
            403: "Forbidden",
            429: "Too Many Requests",
            500: "Internal Server Error",
        },
    )
    @api.expect(group_create_dto, validate=True)
    @jwt_required()
    @roles_required("admin", "teacher", "parent")
    @limiter.limit(lambda: current_app.config.get("RATE_LIMIT_GROUP_CREATE", "10/minute"))
    def post(self):
        """Create a new group"""
        data = request.get_json()
        current_app.logger.debug(f"Received POST request to create group with data: {data}") # Suggestion: Add logging
        return GroupService.create_group(data)


# Define endpoint for accessing a specific group by ID
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
    def get(self, group_id: int): # -> Tuple[Dict[str, Any], int]: # Suggestion: Add type hints
        """Get a specific group's data by its ID"""
        current_app.logger.debug(f"Received GET request for group ID: {group_id}") # Suggestion: Add logging
        return GroupService.get_group_data(group_id)

    @api.doc(
        "Update a group",
        security="Bearer",
        responses={
            200: ("Success", data_resp),
            400: "Validation Error",
            401: "Unauthorized",
            403: "Forbidden",
            404: "Not Found",
            429: "Too Many Requests",
            500: "Internal Server Error",
        },
    )
    @api.expect(
        group_update_dto, validate=True
    )
    @jwt_required()
    @roles_required("admin", "teacher", "parent")
    @limiter.limit(lambda: current_app.config.get("RATE_LIMIT_GROUP_UPDATE", "30/minute"))
    def put(self, group_id: int): # -> Tuple[Dict[str, Any], int]: # Suggestion: Add type hints
        """Update an existing group (full update)"""
        data = request.get_json()
        current_app.logger.debug(f"Received PUT request for group ID {group_id} with data: {data}") # Suggestion: Add logging
        return GroupService.update_group(group_id, data)

    @api.doc(
        "Delete a group",
        security="Bearer",
        responses={
            204: "No Content - Success",
            401: "Unauthorized",
            403: "Forbidden",
            404: "Not Found",
            409: "Conflict (e.g., cannot delete if students exist)",
            429: "Too Many Requests",
            500: "Internal Server Error",
        },
    )
    @jwt_required()
    @roles_required("admin", "teacher", "parent")
    @limiter.limit(lambda: current_app.config.get("RATE_LIMIT_GROUP_DELETE", "10/minute"))
    def delete(self, group_id: int): # -> Tuple[None, int]: # Suggestion: Add type hints
        """Delete a group"""
        current_app.logger.debug(f"Received DELETE request for group ID: {group_id}") # Suggestion: Add logging
        return GroupService.delete_group(group_id)  # Returns (None, 204) on success

