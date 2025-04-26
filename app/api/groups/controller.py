from flask import request # Import request for POST/PUT
from flask_restx import Resource
from flask_jwt_extended import jwt_required

# Import shared extensions/decorators
from app.extensions import limiter
from app.api.decorators import roles_required

# Import group-specific modules
from .service import GroupService
from .dto import GroupDto

# Get the API namespace and DTOs
api = GroupDto.api
data_resp = GroupDto.data_resp
list_data_resp = GroupDto.list_data_resp
# Add input DTOs if defined
group_create_dto = GroupDto.group_create
group_update_dto = GroupDto.group_update
level_filter_parser = GroupDto.level_filter_parser  # Import the parser for query parameters


# Define endpoint for listing all groups and creating new ones
@api.route("/")
class GroupList(Resource):

    @api.doc(
        "List all groups",
        security="Bearer",
        responses={200: ("Success", list_data_resp), 401: "Unauthorized", 403: "Forbidden", 429: "Too Many Requests", 500: "Internal Server Error"},
        parser=level_filter_parser # Add query parameter parser
    )
    @jwt_required()
    @roles_required('admin', 'teacher',  'student')
    @limiter.limit("50/minute")
    def get(self):
        """ Get a list of all groups """
        args = level_filter_parser.parse_args()
        return GroupService.get_all_groups(args)  # Pass the parsed arguments to the service method

    @api.doc(
        "Create a new group",
        security="Bearer",
        responses={201: ("Created", data_resp), 400: "Validation Error", 401: "Unauthorized", 403: "Forbidden", 429: "Too Many Requests", 500: "Internal Server Error"}
    )
    @api.expect(group_create_dto, validate=True)
    @jwt_required()
    @roles_required('admin', 'teacher')
    @limiter.limit("10/minute")
    def post(self):
        """ Create a new group """
        data = request.get_json()
        # Call the implemented service method
        return GroupService.create_group(data)


# Define endpoint for accessing a specific group by ID
@api.route("/<int:group_id>")
@api.param('group_id', 'The unique identifier of the group')
class GroupResource(Resource):

    @api.doc(
        "Get a specific group by ID",
        security="Bearer",
        responses={200: ("Success", data_resp), 401: "Unauthorized", 403: "Forbidden", 404: "Not Found", 429: "Too Many Requests", 500: "Internal Server Error"}
    )
    @jwt_required()
    @roles_required('admin', 'teacher', 'parent', 'student')
    @limiter.limit("100/minute")
    def get(self, group_id):
        """ Get a specific group's data by its ID """
        return GroupService.get_group_data(group_id)

    @api.doc(
        "Update a group",
        security="Bearer",
        responses={200: ("Success", data_resp), 400: "Validation Error", 401: "Unauthorized", 403: "Forbidden", 404: "Not Found", 429: "Too Many Requests", 500: "Internal Server Error"}
    )
    @api.expect(group_update_dto, validate=True) # Use PUT for full update, PATCH for partial
    @jwt_required()
    @roles_required('admin', 'teacher')
    @limiter.limit("30/minute")
    def put(self, group_id):
        """ Update an existing group (full update) """
        data = request.get_json()
        # Call the implemented service method
        return GroupService.update_group(group_id, data)

    @api.doc(
        "Delete a group",
        security="Bearer",
        responses={204: "No Content - Success", 401: "Unauthorized", 403: "Forbidden", 404: "Not Found", 409: "Conflict (e.g., cannot delete if students exist)", 429: "Too Many Requests", 500: "Internal Server Error"}
    )
    @jwt_required()
    @roles_required('admin')
    @limiter.limit("10/minute")
    def delete(self, group_id):
        """ Delete a group """
        # Call the implemented service method
        return GroupService.delete_group(group_id) # Returns (None, 204) on success
