from flask import request, current_app  # Added current_app
from flask_restx import Resource
from flask_jwt_extended import jwt_required

# Import shared extensions/decorators
from app.extensions import limiter
from app.api.decorators import roles_required

# Import level-specific modules
from .service import LevelService
from .dto import LevelDto

# Get the API namespace and DTOs
api = LevelDto.api
data_resp = LevelDto.data_resp
list_data_resp = LevelDto.list_data_resp
level_create_dto = LevelDto.level_create
level_update_dto = LevelDto.level_update
level_filter_parser = (
    LevelDto.level_filter_parser  # Use the parser for query parameters
)


# Define endpoint for listing all levels and creating new ones
@api.route("/")
class LevelList(Resource):

    @api.doc(
        "List all levels",
        security="Bearer",
        responses={
            200: ("Success", list_data_resp),
            401: "Unauthorized",
            403: "Forbidden",
            429: "Too Many Requests",
            500: "Internal Server Error",
        },
        parser=level_filter_parser,  # Add query parameter parser
    )
    @jwt_required()
    @roles_required("admin", "teacher", "student", "parent")
    @limiter.limit(
        lambda: current_app.config.get("RATE_LIMIT_LEVEL_LIST", "100/minute")
    )  # Use config
    def get(self):
        """Get a list of all academic levels (paginated)"""
        args = level_filter_parser.parse_args()
        page = args.get("page")
        per_page = args.get("per_page")
        current_app.logger.debug(
            f"Received GET request for levels with args: {args}"
        )  # Add logging
        return LevelService.get_all_levels(
            page=page, per_page=per_page
        )  # Pass pagination args

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
    @roles_required("admin","parent")
    @limiter.limit(
        lambda: current_app.config.get("RATE_LIMIT_LEVEL_CREATE", "10/minute")
    )  # Use config
    def post(self):
        """Create a new academic level"""
        data = request.get_json()
        current_app.logger.debug(
            f"Received POST request to create level with data: {data}"
        )  # Add logging
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
            403: "Forbidden",  # Added 403
            404: "Not Found",
            429: "Too Many Requests",
            500: "Internal Server Error",
        },
    )
    @jwt_required()
    @roles_required("admin", "teacher", "student", "parent")
    @limiter.limit(
        lambda: current_app.config.get("RATE_LIMIT_LEVEL_GET", "100/minute")
    )  # Use config
    def get(
        self, level_id: int
    ):  # -> Tuple[Dict[str, Any], int]: # Suggestion: Add type hints
        """Get a specific level's data by its ID"""
        current_app.logger.debug(
            f"Received GET request for level ID: {level_id}"
        )  # Add logging
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
    @api.expect(level_update_dto, validate=True)
    @jwt_required()
    @roles_required("admin","parent")
    @limiter.limit(
        lambda: current_app.config.get("RATE_LIMIT_LEVEL_UPDATE", "30/minute")
    )  # Use config
    def put(
        self, level_id: int
    ):  # -> Tuple[Dict[str, Any], int]: # Suggestion: Add type hints
        """Update an existing academic level (full update)"""
        data = request.get_json()
        current_app.logger.debug(
            f"Received PUT request for level ID {level_id} with data: {data}"
        )  # Add logging
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
    @roles_required("admin","parent")
    @limiter.limit(
        lambda: current_app.config.get("RATE_LIMIT_LEVEL_DELETE", "10/minute")
    )  # Use config
    def delete(
        self, level_id: int
    ):  # -> Tuple[None, int]: # Suggestion: Add type hints
        """Delete an academic level"""
        current_app.logger.debug(
            f"Received DELETE request for level ID: {level_id}"
        )  # Add logging
        return LevelService.delete_level(level_id)
