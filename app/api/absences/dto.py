from flask_restx import Namespace, fields
from flask_restx.reqparse import RequestParser


class AbsenceDto:
    """Data Transfer Objects and Request Parsers for the Absence API."""

    # Define the namespace
    api = Namespace("absences", description="Student absence related operations.")

    # --- Parser for Query Parameters (Filters and Pagination) ---
    absence_filter_parser = RequestParser(bundle_errors=True)
    absence_filter_parser.add_argument(
        "student_id",
        type=int,
        location="args",
        required=False,
        help="Filter absences by the ID of the student.",
    )
    absence_filter_parser.add_argument(
        "session_id",
        type=int,
        location="args",
        required=False,
        help="Filter absences by the ID of the session.",
    )
    absence_filter_parser.add_argument(
        "justified",
        type=bool,
        location="args",
        required=False,
        help="Filter absences by justification status (true/false).",
    )
    absence_filter_parser.add_argument(
        "start_date",
        type=str,  # Expecting YYYY-MM-DD string
        location="args",
        required=False,
        help="Filter absences for sessions occurring on or after this date (YYYY-MM-DD).",
    )
    absence_filter_parser.add_argument(
        "end_date",
        type=str,  # Expecting YYYY-MM-DD string
        location="args",
        required=False,
        help="Filter absences for sessions occurring on or before this date (YYYY-MM-DD).",
    )
    absence_filter_parser.add_argument(
        "page",
        type=int,
        location="args",
        required=False,
        default=1,
        help="Page number for pagination (default: 1).",
    )
    absence_filter_parser.add_argument(
        "per_page",
        type=int,
        location="args",
        required=False,
        default=10,
        help="Number of items per page (default: 10).",
    )

    # Define the core 'absence' object model
    absence = api.model(
        "Absence Object",
        {
            "id": fields.Integer(
                readonly=True, description="Absence record unique identifier"
            ),
            "student_id": fields.Integer(
                required=True, description="ID of the absent student"
            ),
            "session_id": fields.Integer(
                required=True, description="ID of the session missed"
            ),
            "justified": fields.Boolean(
                required=True, description="Indicates if the absence is justified"
            ),
            "reason": fields.String(
                required=False, description="Reason for justification (if any)"
            ),
            "recorded_at": fields.DateTime(
                readonly=True,
                description="Timestamp when the absence was recorded (UTC)",
            ),
            # Consider adding related info (names, session time) via service enrichment if needed
            # "student_name": fields.String(attribute="student.user.name", readonly=True),
            # "session_start_time": fields.DateTime(attribute="session.start_time", readonly=True),
            # "module_name": fields.String(attribute="session.module.name", readonly=True),
        },
    )

    # Standard response for a single absence record
    data_resp = api.model(
        "Absence Data Response",
        {
            "status": fields.Boolean(description="Indicates success or failure"),
            "message": fields.String(description="Response message"),
            "absence": fields.Nested(absence, description="The absence record data"),
        },
    )

    # Standard response for a list of absence records (includes pagination)
    list_data_resp = api.model(
        "Absence List Response",
        {
            "status": fields.Boolean(description="Indicates success or failure"),
            "message": fields.String(description="Response message"),
            "absences": fields.List(
                fields.Nested(absence), description="List of absence record data"
            ),
            "total": fields.Integer(
                description="Total number of absence records matching the query"
            ),
            "pages": fields.Integer(description="Total number of pages"),
            "current_page": fields.Integer(description="The current page number"),
            "per_page": fields.Integer(description="Number of items per page"),
            "has_next": fields.Boolean(description="True if there is a next page"),
            "has_prev": fields.Boolean(description="True if there is a previous page"),
        },
    )

    # --- DTOs for POST/PATCH ---
    absence_create_input = api.model(
        "Absence Create Input",
        {
            "student_id": fields.Integer(
                required=True, description="ID of the absent student"
            ),
            "session_id": fields.Integer(
                required=True, description="ID of the session missed"
            ),
            "justified": fields.Boolean(
                required=False,
                default=False,
                description="Is the absence justified? (default: false)",
            ),
            "reason": fields.String(
                required=False,
                description="Reason for justification (required if justified=true, optional otherwise)",
            ),
        },
    )

    absence_update_input = api.model(
        "Absence Update Input",
        {
            "justified": fields.Boolean(
                required=False, description="Updated justification status"
            ),
            "reason": fields.String(
                required=False,
                description="Updated reason for justification (can be empty string to clear)",
            ),
            # student_id and session_id cannot be changed
        },
    )
