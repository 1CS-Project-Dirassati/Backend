from flask_restx import Namespace, fields
from flask_restx.reqparse import RequestParser

class GroupDto:
    """Data Transfer Objects and Request Parsers for the Group API."""

    api = Namespace("groups", description="School group related operations.")

    # Request parser for filtering and pagination parameters in GET requests
    group_filter_parser = RequestParser(bundle_errors=True)
    group_filter_parser.add_argument(
        'level_id',
        type=int,
        location='args',
        required=False,
        help='Filter groups by the ID of the level they belong to.'
    )
    group_filter_parser.add_argument(
        'page',
        type=int,
        location='args',
        required=False,
        default=1,
        help='Page number for pagination (default: 1).'
    )
    group_filter_parser.add_argument(
         'per_page',
         type=int,
         location='args',
         required=False,
         default=10, # Default items per page, should match config if used
         help='Number of items per page (default: 10).'
     )

    # Core data model for a Group object
    group = api.model(
        "Group Object",
        {
            "id": fields.Integer(readonly=True, description="Group unique identifier"),
            "name": fields.String(required=True, description="Name of the group (max 50 chars)", max_length=50),
            "level_id": fields.Integer(required=True, description="ID of the level this group belongs to"),
        },
    )

    # Standard response model for single group requests
    data_resp = api.model(
        "Group Data Response",
        {
            "status": fields.Boolean(description="Indicates success or failure"),
            "message": fields.String(description="Response message"),
            "group": fields.Nested(group, description="The group data"),
        },
    )

    # Standard response model for list group requests (includes pagination)
    list_data_resp = api.model(
        "Group List Response",
        {
            "status": fields.Boolean(description="Indicates success or failure"),
            "message": fields.String(description="Response message"),
            "groups": fields.List(fields.Nested(group), description="List of group data for the current page"),
            # Pagination metadata fields
            "total": fields.Integer(description="Total number of groups matching the query"),
            "pages": fields.Integer(description="Total number of pages"),
            "current_page": fields.Integer(description="The current page number"),
            "per_page": fields.Integer(description="Number of items per page"),
            "has_next": fields.Boolean(description="True if there is a next page"),
            "has_prev": fields.Boolean(description="True if there is a previous page"),
        }
    )

    # Input model for creating a new group (POST requests)
    group_create = api.model(
        "Group Create Input",
        {
             "name": fields.String(required=True, description="Name of the group (max 50 chars)", max_length=50),
             "level_id": fields.Integer(required=True, description="ID of the level this group belongs to"),
        }
    )

    # Input model for updating an existing group (PUT requests)
    group_update = api.model(
         "Group Update Input",
        {
             "name": fields.String(description="New name for the group (max 50 chars)", max_length=50),
             "level_id": fields.Integer(description="New ID of the level this group belongs to"),
        }
    )
