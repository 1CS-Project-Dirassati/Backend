from flask_restx import Namespace, fields


class LevelDto:
    # Define the namespace for level operations
    api = Namespace("levels", description="Academic level (grade) related operations.")

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

    # Define the standard response structure for a list of levels
    list_data_resp = api.model(
        "Level List Response",
        {
            "status": fields.Boolean(description="Indicates success or failure"),
            "message": fields.String(description="Response message"),
            "levels": fields.List(
                fields.Nested(level), description="List of level data"
            ),
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
