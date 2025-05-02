from flask_restx import Namespace, fields
from flask_restx.reqparse import RequestParser


class SemesterDto:
    """Data Transfer Objects and Request Parsers for the Semester API."""

    # Define the namespace
    api = Namespace("semesters", description="Academic semester related operations.")

    # --- Parser for Query Parameters (Filters and Pagination) ---
    semester_filter_parser = RequestParser(bundle_errors=True)
    semester_filter_parser.add_argument(
        "level_id",
        type=int,
        location="args",
        required=False,
        help="Filter semesters by the ID of the academic level.",
    )
    semester_filter_parser.add_argument(
        "start_date",
        type=str,
        location="args",
        required=False,
        help="Filter semesters starting on or after this date (YYYY-MM-DD).",
    )
    semester_filter_parser.add_argument(
        "end_date",
        type=str,
        location="args",
        required=False,
        help="Filter semesters ending on or before this date (YYYY-MM-DD).",
    )
    semester_filter_parser.add_argument(
        "page",
        type=int,
        location="args",
        required=False,
        default=1,
        help="Page number for pagination (default: 1).",
    )
    semester_filter_parser.add_argument(
        "per_page",
        type=int,
        location="args",
        required=False,
        default=10,
        help="Number of items per page (default: 10).",
    )

    # Define the core 'semester' object model
    semester = api.model(
        "Semester Object",
        {
            "id": fields.Integer(
                readonly=True, description="Semester unique identifier"
            ),
            "name": fields.String(required=True, description="Name of the semester"),
            "level_id": fields.Integer(
                required=True, description="ID of the associated academic level"
            ),
            "start_date": fields.Date(
                required=True, description="Start date of the semester (YYYY-MM-DD)"
            ),
            "duration": fields.Integer(
                required=True, description="Duration of the semester in weeks"
            ),
            "created_at": fields.DateTime(
                readonly=True, description="Timestamp of semester creation (UTC)"
            ),
            "updated_at": fields.DateTime(
                readonly=True, description="Timestamp of last semester update (UTC)"
            ),
        },
    )

    # Standard response for a single semester
    data_resp = api.model(
        "Semester Data Response",
        {
            "status": fields.Boolean(description="Indicates success or failure"),
            "message": fields.String(description="Response message"),
            "semester": fields.Nested(semester, description="The semester data"),
        },
    )

    # Standard response for a list of semesters (includes pagination)
    list_data_resp = api.model(
        "Semester List Response",
        {
            "status": fields.Boolean(description="Indicates success or failure"),
            "message": fields.String(description="Response message"),
            "semesters": fields.List(
                fields.Nested(semester), description="List of semester data"
            ),
            "total": fields.Integer(
                description="Total number of semesters matching the query"
            ),
            "pages": fields.Integer(description="Total number of pages"),
            "current_page": fields.Integer(description="The current page number"),
            "per_page": fields.Integer(description="Number of items per page"),
            "has_next": fields.Boolean(description="True if there is a next page"),
            "has_prev": fields.Boolean(description="True if there is a previous page"),
        },
    )

    # --- DTOs for POST/PATCH ---
    semester_create_input = api.model(
        "Semester Create Input",
        {
            "name": fields.String(required=True, description="Name of the semester"),
            "level_id": fields.Integer(
                required=True, description="ID of the associated academic level"
            ),
            "start_date": fields.Date(
                required=True, description="Start date of the semester (YYYY-MM-DD)"
            ),
            "duration": fields.Integer(
                required=True, description="Duration of the semester in weeks"
            ),
        },
    )

    semester_update_input = api.model(
        "Semester Update Input",
        {
            "name": fields.String(
                required=False, description="Updated name of the semester"
            ),
            "start_date": fields.Date(
                required=False,
                description="Updated start date of the semester (YYYY-MM-DD)",
            ),
            "duration": fields.Integer(
                required=False, description="Updated duration of the semester in weeks"
            ),
        },
    )
