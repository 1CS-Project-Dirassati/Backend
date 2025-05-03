from flask_restx import Namespace, fields
from flask_restx.reqparse import RequestParser


class SessionDto:
    """Data Transfer Objects and Request Parsers for the Session API.""" # Updated docstring

    # Define the namespace for session operations
    api = Namespace(
        "sessions", description="Class session scheduling related operations."
    )

    # --- Parser for Query Parameters (Filters and Pagination) ---
    session_filter_parser = RequestParser(bundle_errors=True)
    session_filter_parser.add_argument(
        "group_id",
        type=int,
        location="args",
        required=False,
        help="Filter sessions by the ID of the group attending.",
    )
    session_filter_parser.add_argument(
        "teacher_id",
        type=int,
        location="args",
        required=False,
        help="Filter sessions by the ID of the teacher conducting.",
    )
    session_filter_parser.add_argument(
        "semester_id",
        type=int,
        location="args",
        required=False,
        help="Filter sessions by the ID of the semester .",
    )
    session_filter_parser.add_argument( # Added page
        'page',
        type=int,
        location='args',
        required=False,
        default=1,
        help='Page number for pagination (default: 1).'
    )
    session_filter_parser.add_argument( # Added per_page
         'per_page',
         type=int,
         location='args',
         required=False,
         default=10,
         help='Number of items per page (default: 10).'
     )
    # Add other potential filters like semester_id, module_id, date ranges later if needed

    # Define the core 'session' object model
    session = api.model(
        "Session Object",
        {
            "id": fields.Integer(
                readonly=True, description="Session unique identifier"
            ),
            "teacher_id": fields.Integer(
                required=True, description="ID of the teacher conducting the session" # Clarified description
            ),
            "module_id": fields.Integer(
                required=True, description="ID of the module being taught"
            ),
            "group_id": fields.Integer(
                required=True, description="ID of the group attending the session" # Clarified description
            ),
            "semester_id": fields.Integer(
                required=True, description="ID of the semester the session belongs to" # Clarified description
            ),
            "salle_id": fields.Integer(
                required=False, # Explicitly False
                description="ID of the room (salle) where the session takes place, if assigned" # Clarified description
            ),
            "start_time": fields.DateTime(
                required=True,
                description="Start date and time of the session (UTC, ISO 8601 format)", # Added UTC
                dt_format="iso8601",
            ),
            "weeks": fields.Integer(
                required=False, # Explicitly False
                description="Number of consecutive weeks the session repeats (e.g., 1 for a single session)" # Clarified description
            ),
            # Consider adding nested fields for related objects if needed for display
            # "teacher_name": fields.String(attribute="teacher.user.name", readonly=True), # Example using User relation
            # "group_name": fields.String(attribute="group.name", readonly=True), # Example
            # "module_name": fields.String(attribute="module.name", readonly=True), # Example
        },
    )

    # Define the standard response structure for a single session
    data_resp = api.model(
        "Session Data Response",
        {
            "status": fields.Boolean(description="Indicates success or failure"),
            "message": fields.String(description="Response message"),
            "session": fields.Nested(session, description="The session data"),
        },
    )

    # Define the standard response structure for a list of sessions (includes pagination)
    list_data_resp = api.model(
        "Session List Response",
        {
            "status": fields.Boolean(description="Indicates success or failure"),
            "message": fields.String(description="Response message"),
            "sessions": fields.List(
                fields.Nested(session), description="List of session data for the current page" # Updated description
            ),
            # Pagination metadata fields
            "total": fields.Integer(description="Total number of sessions matching the query"),
            "pages": fields.Integer(description="Total number of pages"),
            "current_page": fields.Integer(description="The current page number"),
            "per_page": fields.Integer(description="Number of items per page"),
            "has_next": fields.Boolean(description="True if there is a next page"),
            "has_prev": fields.Boolean(description="True if there is a previous page"),
        }
    )

    # --- DTOs for POST/PUT ---
    session_create = api.model(
        "Session Create Input",
        {
            "teacher_id": fields.Integer(
                required=True, description="ID of the teacher"
            ),
            "module_id": fields.Integer(required=True, description="ID of the module"),
            "group_id": fields.Integer(required=True, description="ID of the group"),
            "semester_id": fields.Integer(
                required=True, description="ID of the semester"
            ),
            "salle_id": fields.Integer(required=False, description="ID of the room (salle), optional"), # Required=False
            "start_time": fields.DateTime(
                required=True,
                description="Start date and time (UTC, ISO 8601 format)", # Added UTC
                dt_format="iso8601",
            ),
            "weeks": fields.Integer(required=False, description="Number of weeks the session repeats, optional"), # Required=False
        },
    )
    session_update = api.model(
        "Session Update Input",
        {
            "teacher_id": fields.Integer(description="New ID of the teacher"),
            "module_id": fields.Integer(description="New ID of the module"),
            "group_id": fields.Integer(description="New ID of the group"),
            "semester_id": fields.Integer(description="New ID of the semester"),
            "salle_id": fields.Integer(description="New ID of the room (salle)"),
            "start_time": fields.DateTime(
                description="New start date and time (UTC, ISO 8601 format)", # Added UTC
                dt_format="iso8601",
            ),
            "weeks": fields.Integer(
                description="New number of weeks the session repeats"
            ),
        },
    )
