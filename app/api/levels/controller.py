from flask import request
from flask_restx import Resource
from flask_jwt_extended import jwt_required

# Import shared extensions/decorators
from app.extensions import limiter
from app.api.decorators import roles_required  # Assuming this is the correct path

# Import level-specific modules
from .service import LevelService
from .dto import LevelDto

# Get the API namespace and DTOs
api = LevelDto.api
data_resp = LevelDto.data_resp
list_data_resp = LevelDto.list_data_resp
level_create_dto = LevelDto.level_create
level_update_dto = LevelDto.level_update


# Define endpoint for listing all levels and creating new ones
@api.route("/")
class LevelList(Resource):

    @api.doc(
        "List all levels",
        security="Bearer",  # Apply security if needed, even for GET
        responses={
            200: ("Success", list_data_resp),
            401: "Unauthorized",
            429: "Too Many Requests",
            500: "Internal Server Error",
        },
    )
    @jwt_required()  # Most likely all users need to see levels
    @roles_required("admin", "teacher", "student", "parent")  # Adjust roles as needed
    @limiter.limit("100/minute")  # Allow frequent access
    def get(self):
        """Get a list of all academic levels"""
        return LevelService.get_all_levels()

    @api.doc(
        "Create a new level",
        security="Bearer",
        responses={
            201: ("Created", data_resp),
            400: "Validation Error",
            401: "Unauthorized",
            403: "Forbidden",
            409: "Conflict (e.g., duplicate name)",
            429: "Too Many Requests",
            500: "Internal Server Error",
        },
    )
    @api.expect(level_create_dto, validate=True)
    @jwt_required()
    @roles_required("admin")  # Only admins can create levels
    @limiter.limit("10/minute")
    def post(self):
        """Create a new academic level"""
        data = request.get_json()
        return LevelService.create_level(data)


# Define endpoint for accessing a specific level by ID
@api.route("/<int:level_id>")
@api.param("level_id", "The unique identifier of the level")
class LevelResource(Resource):

    @api.doc(
        "Get a specific level by ID",
        security="Bearer",
        responses={
            200: ("Success", data_resp),
            401: "Unauthorized",
            404: "Not Found",
            429: "Too Many Requests",
            500: "Internal Server Error",
        },
    )
    @jwt_required()  # Most likely all users need to see specific levels
    @roles_required("admin", "teacher", "student", "parent")  # Adjust roles as needed
    @limiter.limit("100/minute")
    def get(self, level_id):
        """Get a specific level's data by its ID"""
        return LevelService.get_level_data(level_id)

    @api.doc(
        "Update a level",
        security="Bearer",
        responses={
            200: ("Success", data_resp),
            400: "Validation Error/Empty Body",
            401: "Unauthorized",
            403: "Forbidden",
            404: "Not Found",
            409: "Conflict (e.g., duplicate name)",
            429: "Too Many Requests",
            500: "Internal Server Error",
        },
    )
    @api.expect(level_update_dto, validate=True)  # Use validate=True for basic checks
    @jwt_required()
    @roles_required("admin")  # Only admins can update levels
    @limiter.limit("30/minute")
    def put(self, level_id):
        """Update an existing academic level"""
        data = request.get_json()
        return LevelService.update_level(level_id, data)

    @api.doc(
        "Delete a level",
        security="Bearer",
        responses={
            204: "No Content - Success",
            401: "Unauthorized",
            403: "Forbidden",
            404: "Not Found",
            409: "Conflict (Cannot delete, associated items exist)",
            429: "Too Many Requests",
            500: "Internal Server Error",
        },
    )
    @jwt_required()
    @roles_required("admin")  # Only admins can delete levels
    @limiter.limit("10/minute")
    def delete(self, level_id):
        """Delete an academic level"""
        return LevelService.delete_level(level_id)  # Returns (None, 204) on success
