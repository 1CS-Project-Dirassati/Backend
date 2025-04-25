from flask_restx import Namespace, fields

class GroupDto:
    # Define the namespace for group operations
    api = Namespace("groups", description="School group related operations.")

    # Define the core 'group' object model based on the Group SQLAlchemy model
    group = api.model(
        "Group Object",
        {
            "id": fields.Integer(readonly=True, description="Group unique identifier"),
            "name": fields.String(required=True, description="Name of the group (max 50 chars)", max_length=50),
            "level_id": fields.Integer(required=True, description="ID of the level this group belongs to"),
            # You could add fields representing relationships later if needed,
            # e.g., by querying counts or specific related IDs in the service layer.
            # "student_count": fields.Integer(readonly=True, description="Number of students in the group"),
        },
    )

    # Define the standard response structure for a single group
    data_resp = api.model(
        "Group Data Response",
        {
            "status": fields.Boolean(description="Indicates success or failure"),
            "message": fields.String(description="Response message"),
            "group": fields.Nested(group, description="The group data"),
        },
    )

    # Define the standard response structure for a list of groups
    list_data_resp = api.model(
        "Group List Response",
        {
            "status": fields.Boolean(description="Indicates success or failure"),
            "message": fields.String(description="Response message"),
            "groups": fields.List(fields.Nested(group), description="List of group data"),
            # Add pagination fields here if you implement pagination later
            # "page": fields.Integer(),
            # "per_page": fields.Integer(),
            # "total": fields.Integer(),
        }
    )

    # --- Add DTOs for POST/PUT if needed ---
    # Example for creating a group (omitting read-only 'id')
    group_create = api.model(
        "Group Create Input",
        {
             "name": fields.String(required=True, description="Name of the group (max 50 chars)", max_length=50),
             "level_id": fields.Integer(required=True, description="ID of the level this group belongs to"),
             # Add other writable fields as necessary
        }
    )
    # Example for updating a group (fields might be optional)
    group_update = api.model(
         "Group Update Input",
        {
             "name": fields.String(description="New name for the group (max 50 chars)", max_length=50),
             "level_id": fields.Integer(description="New ID of the level this group belongs to"),
             # Add other updatable fields as necessary
        }
    )

