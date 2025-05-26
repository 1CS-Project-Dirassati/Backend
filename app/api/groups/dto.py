from flask_restx import Namespace, fields
from flask_restx.reqparse import RequestParser


class GroupDto:
    """Data Transfer Objects and Request Parsers for the Group API."""

    api = Namespace("groups", description="School group related operations.")

    group_filter_parser = RequestParser(bundle_errors=True)
    group_filter_parser.add_argument(
        "level_id",
        type=int,
        location="args",
        required=False,
        help="Filter groups by the ID of the level they belong to.",
    )
    group_filter_parser.add_argument(  # ADDED teacher_id filter
        "teacher_id",
        type=int,
        location="args",
        required=False,
        help="Filter groups by the ID of a teacher associated with the group through sessions.",
    )
    group_filter_parser.add_argument(
        "page",
        type=int,
        location="args",
        required=False,
        default=1,
        help="Page number for pagination (default: 1).",
    )
    group_filter_parser.add_argument(
        "per_page",
        type=int,
        location="args",
        required=False,
        default=10,
        help="Number of items per page (default: 10).",
    )

    group = api.model(
        "Group Object",
        {
            "id": fields.Integer(readonly=True, description="Group unique identifier"),
            "name": fields.String(
                required=True,
                description="Name of the group (max 50 chars)",
                max_length=50,
            ),
            "level_id": fields.Integer(
                required=True, description="ID of the level this group belongs to"
            ),
            # You might also want to include 'level_name' here if you enrich it in the service
            # "level_name": fields.String(readonly=True, description="Name of the level"),
        },
    )

    data_resp = api.model(
        "Group Data Response",
        {
            "status": fields.Boolean(description="Indicates success or failure"),
            "message": fields.String(description="Response message"),
            "group": fields.Nested(group, description="The group data"),
        },
    )

    list_data_resp = api.model(
        "Group List Response",
        {
            "status": fields.Boolean(description="Indicates success or failure"),
            "message": fields.String(description="Response message"),
            "groups": fields.List(
                fields.Nested(group),
                description="List of group data for the current page",
            ),
            "total": fields.Integer(
                description="Total number of groups matching the query"
            ),
            "pages": fields.Integer(description="Total number of pages"),
            "current_page": fields.Integer(description="The current page number"),
            "per_page": fields.Integer(description="Number of items per page"),
            "has_next": fields.Boolean(description="True if there is a next page"),
            "has_prev": fields.Boolean(description="True if there is a previous page"),
        },
    )

    group_create = api.model(
        "Group Create Input",
        {
            "name": fields.String(
                required=True,
                description="Name of the group (max 50 chars)",
                max_length=50,
            ),
            "level_id": fields.Integer(
                required=True, description="ID of the level this group belongs to"
            ),
        },
    )

    group_update = api.model(
        "Group Update Input",
        {
            "name": fields.String(
                description="New name for the group (max 50 chars)", max_length=50
            ),
            "level_id": fields.Integer(
                description="New ID of the level this group belongs to"
            ),
        },
    )
