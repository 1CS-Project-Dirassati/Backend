from flask import request # Import request for POST/PUT
from flask_restx import Resource
from flask_jwt_extended import jwt_required

# Import shared extensions/decorators
from app.extensions import limiter
from app.auth.decorators import roles_required

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


# Define endpoint for listing all groups and creating new ones
@api.route("/")
class GroupList(Resource):
    # Add decorators directly to the methods (get, post, etc.)

    @api.doc(
        "List all groups",
        security="Bearer", # Indicate JWT is required for Swagger UI
        responses={
            200: ("List of groups successfully sent", list_data_resp),
            401: "Unauthorized - Invalid or missing JWT.",
            403: "Forbidden - Insufficient role privileges.",
            429: "Too Many Requests - Rate limit exceeded.",
            500: "Internal Server Error.",
        },
    )
    @jwt_required() # Ensures user is logged in
    @roles_required('admin', 'teacher', 'parent', 'student') # Define who can list groups
    @limiter.limit("50/minute") # Example rate limit
    def get(self):
        """ Get a list of all groups """
        return GroupService.get_all_groups()

    @api.doc(
        "Create a new group",
        security="Bearer",
        responses={
             201: ("Group successfully created", data_resp), # Use data_resp if returning the created group
             400: "Input payload validation failed",
             401: "Unauthorized - Invalid or missing JWT.",
             403: "Forbidden - Insufficient role privileges.",
             429: "Too Many Requests - Rate limit exceeded.",
             500: "Internal Server Error.",
        }
    )
    @api.expect(group_create_dto, validate=True) # Expect group data in request body
    @jwt_required()
    @roles_required('admin', 'teacher') # Define who can create groups
    @limiter.limit("10/minute")
    def post(self):
        """ Create a new group """
        data = request.get_json()
        # return GroupService.create_group(data) # Uncomment when service method is implemented
        return {"status": False, "message": "POST method not implemented yet"}, 501


# Define endpoint for accessing a specific group by ID
@api.route("/<int:group_id>")
@api.param('group_id', 'The unique identifier of the group') # Document path parameter
class GroupResource(Resource):
    # Add decorators directly to the methods (get, put, delete, etc.)

    @api.doc(
        "Get a specific group by ID",
        security="Bearer",
        responses={
            200: ("Group data successfully sent", data_resp),
            401: "Unauthorized - Invalid or missing JWT.",
            403: "Forbidden - Insufficient role privileges.",
            404: "Group not found!",
            429: "Too Many Requests - Rate limit exceeded.",
            500: "Internal Server Error.",
        },
    )
    @jwt_required() # Ensures user is logged in
    @roles_required('admin', 'teacher', 'parent', 'student') # Define who can view a specific group
    @limiter.limit("100/minute") # Example rate limit
    def get(self, group_id):
        """ Get a specific group's data by its ID """
        return GroupService.get_group_data(group_id)

    @api.doc(
        "Update a group",
        security="Bearer",
         responses={
             200: ("Group successfully updated", data_resp),
             400: "Input payload validation failed",
             401: "Unauthorized - Invalid or missing JWT.",
             403: "Forbidden - Insufficient role privileges.",
             404: "Group not found!",
             429: "Too Many Requests - Rate limit exceeded.",
             500: "Internal Server Error.",
        }
    )
    @api.expect(group_update_dto, validate=True) # Use update DTO, allow partial updates if using PATCH
    @jwt_required()
    @roles_required('admin', 'teacher') # Define who can update groups
    @limiter.limit("30/minute")
    def put(self, group_id):
        """ Update an existing group (full update) """
        data = request.get_json()
        # return GroupService.update_group(group_id, data) # Uncomment when service method is implemented
        return {"status": False, "message": "PUT method not implemented yet"}, 501

    # Consider using PATCH for partial updates: @api.expect(group_update_dto, validate=True, partial=True)

    @api.doc(
        "Delete a group",
        security="Bearer",
        responses={
             204: "Group successfully deleted.", # 204 No Content typically used for successful DELETE
             401: "Unauthorized - Invalid or missing JWT.",
             403: "Forbidden - Insufficient role privileges.",
             404: "Group not found!",
             429: "Too Many Requests - Rate limit exceeded.",
             500: "Internal Server Error.",
        }
    )
    @jwt_required()
    @roles_required('admin') # Define who can delete groups
    @limiter.limit("10/minute")
    def delete(self, group_id):
        """ Delete a group """
        # return GroupService.delete_group(group_id) # Uncomment when service method is implemented
        # Successful delete usually returns no body, status 204
        # return '', 204
        return {"status": False, "message": "DELETE method not implemented yet"}, 501

