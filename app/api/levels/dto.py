from flask_restx import Namespace, fields
from flask_restx.reqparse import RequestParser  # Added RequestParser


class LevelDto:
    """Data Transfer Objects and Request Parsers for the Level API."""  # Updated docstring

    # Define the namespace for level operations
    api = Namespace("levels", description="Academic level (grade) related operations.")

    # Request parser for pagination parameters in GET requests
    level_filter_parser = RequestParser(bundle_errors=True)
    level_filter_parser.add_argument(
        "page",
        type=int,
        location="args",
        required=False,
        default=1,
        help="Page number for pagination (default: 1).",
    )
    level_filter_parser.add_argument(
        "per_page",
        type=int,
        location="args",
        required=False,
        default=10,  # Default items per page
        help="Number of items per page (default: 10).",
    )

    # Define the core 'level' object model based on the Level SQLAlchemy model
    level = api.model(
        "Level Object",
        {
            "id": fields.Integer(readonly=True, description="Level unique identifier"),
            "name": fields.String(
                required=True,
                description="Name of the level (max 50 chars, unique)",
                max_length=50,
            ),
            "description": fields.String(
                required=False,  # Make optional consistent
                description="Optional description of the level (max 255 chars)",
                max_length=255,
            ),
        },
    )

    # Define the standard response structure for a single level
    data_resp = api.model(
        "Level Data Response",
        {
            "status": fields.Boolean(description="Indicates success or failure"),
            "message": fields.String(description="Response message"),
            "level": fields.Nested(level, description="The level data"),
        },
    )

    # Define the standard response structure for a list of levels (includes pagination)
    list_data_resp = api.model(
        "Level List Response",
        {
            "status": fields.Boolean(description="Indicates success or failure"),
            "message": fields.String(description="Response message"),
            "levels": fields.List(
                fields.Nested(level),
                description="List of level data for the current page",  # Updated description
            ),
            # Pagination metadata fields
            "total": fields.Integer(
                description="Total number of levels matching the query"
            ),
            "pages": fields.Integer(description="Total number of pages"),
            "current_page": fields.Integer(description="The current page number"),
            "per_page": fields.Integer(description="Number of items per page"),
            "has_next": fields.Boolean(description="True if there is a next page"),
            "has_prev": fields.Boolean(description="True if there is a previous page"),
        },
    )

    # --- DTOs for POST/PUT ---
    # DTO for creating a level (omitting read-only 'id')
    level_create = api.model(
        "Level Create Input",
        {
            "name": fields.String(
                required=True,
                description="Name of the level (max 50 chars, unique)",
                max_length=50,
            ),
            "description": fields.String(
                required=False,  # Explicitly false
                description="Optional description of the level (max 255 chars)",
                max_length=255,
            ),
        },
    )
    # DTO for updating a level (fields are optional for PUT/PATCH)
    level_update = api.model(
        "Level Update Input",
        {
            "name": fields.String(
                description="New name for the level (max 50 chars, unique)",
                max_length=50,
            ),
            "description": fields.String(
                description="New optional description for the level (max 255 chars)",
                max_length=255,
            ),
        },
    )
