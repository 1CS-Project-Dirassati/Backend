from flask_restx import Namespace, fields
from flask_restx.reqparse import RequestParser # Import ArgumentParser

class GroupDto:
    # Define the namespace for group operations
    api = Namespace("groups", description="School group related operations.")

    # --- Parser for Query Parameters ---
    level_filter_parser = RequestParser(bundle_errors=True)
    level_filter_parser.add_argument(
        'level_id',
        type=int,
        location='args', # Specify query string location
        required=False,  # Make the parameter optional
        help='Filter groups by the ID of the level they belong to.'
    )

    # Define the core 'group' object model
    group = api.model(
        "Group Object",
        {
            "id": fields.Integer(readonly=True, description="Group unique identifier"),
            "name": fields.String(required=True, description="Name of the group (max 50 chars)", max_length=50),
            "level_id": fields.Integer(required=True, description="ID of the level this group belongs to"),
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
        }
    )

    # --- DTOs for POST/PUT ---
    group_create = api.model(
        "Group Create Input",
        {
             "name": fields.String(required=True, description="Name of the group (max 50 chars)", max_length=50),
             "level_id": fields.Integer(required=True, description="ID of the level this group belongs to"),
        }
    )
    group_update = api.model(
         "Group Update Input",
        {
             "name": fields.String(description="New name for the group (max 50 chars)", max_length=50),
             "level_id": fields.Integer(description="New ID of the level this group belongs to"),
        }
    )
