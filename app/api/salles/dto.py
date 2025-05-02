from flask_restx import Namespace, fields
from flask_restx.reqparse import RequestParser


class SalleDto:
    """Data Transfer Objects and Request Parsers for the Salle API."""

    # Define the namespace
    api = Namespace("salles", description="Classroom (salle) related operations.")

    # --- Parser for Query Parameters (Filters and Pagination) ---
    salle_filter_parser = RequestParser(bundle_errors=True)
    salle_filter_parser.add_argument(
        "name",
        type=str,
        location="args",
        required=False,
        help="Filter salles by name (partial match).",
    )
    salle_filter_parser.add_argument(
        "min_capacity",
        type=int,
        location="args",
        required=False,
        help="Filter salles with at least this capacity.",
    )
    salle_filter_parser.add_argument(
        "max_capacity",
        type=int,
        location="args",
        required=False,
        help="Filter salles with at most this capacity.",
    )
    salle_filter_parser.add_argument(
        "page",
        type=int,
        location="args",
        required=False,
        default=1,
        help="Page number for pagination (default: 1).",
    )
    salle_filter_parser.add_argument(
        "per_page",
        type=int,
        location="args",
        required=False,
        default=10,
        help="Number of items per page (default: 10).",
    )

    # Define the core 'salle' object model
    salle = api.model(
        "Salle Object",
        {
            "id": fields.Integer(readonly=True, description="Salle unique identifier"),
            "name": fields.String(required=True, description="Name of the salle"),
            "capacity": fields.Integer(
                required=True, description="Capacity of the salle"
            ),
            "location": fields.String(
                required=False, description="Location of the salle"
            ),
        },
    )

    # Standard response for a single salle
    data_resp = api.model(
        "Salle Data Response",
        {
            "status": fields.Boolean(description="Indicates success or failure"),
            "message": fields.String(description="Response message"),
            "salle": fields.Nested(salle, description="The salle data"),
        },
    )

    # Standard response for a list of salles (includes pagination)
    list_data_resp = api.model(
        "Salle List Response",
        {
            "status": fields.Boolean(description="Indicates success or failure"),
            "message": fields.String(description="Response message"),
            "salles": fields.List(
                fields.Nested(salle), description="List of salle data"
            ),
            "total": fields.Integer(
                description="Total number of salles matching the query"
            ),
            "pages": fields.Integer(description="Total number of pages"),
            "current_page": fields.Integer(description="The current page number"),
            "per_page": fields.Integer(description="Number of items per page"),
            "has_next": fields.Boolean(description="True if there is a next page"),
            "has_prev": fields.Boolean(description="True if there is a previous page"),
        },
    )

    # --- DTOs for POST/PATCH ---
    salle_create_input = api.model(
        "Salle Create Input",
        {
            "name": fields.String(required=True, description="Name of the salle"),
            "capacity": fields.Integer(
                required=True, description="Capacity of the salle"
            ),
            "location": fields.String(
                required=False, description="Location of the salle"
            ),
        },
    )

    salle_update_input = api.model(
        "Salle Update Input",
        {
            "name": fields.String(
                required=False, description="Updated name of the salle"
            ),
            "capacity": fields.Integer(
                required=False, description="Updated capacity of the salle"
            ),
            "location": fields.String(
                required=False, description="Updated location of the salle"
            ),
        },
    )
