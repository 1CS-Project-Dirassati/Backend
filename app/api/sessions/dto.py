from flask_restx import Namespace, fields
from flask_restx.reqparse import RequestParser  # Import RequestParser


class SessionDto:
    # Define the namespace for session operations
    api = Namespace(
        "sessions", description="Class session scheduling related operations."
    )

    # --- Parser for Query Parameters ---
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
    # Add other potential filters like semester_id, module_id, date ranges later if needed

    # Define the core 'session' object model
    session = api.model(
        "Session Object",
        {
            "id": fields.Integer(
                readonly=True, description="Session unique identifier"
            ),
            "teacher_id": fields.Integer(
                required=True, description="ID of the teacher"
            ),
            "module_id": fields.Integer(
                required=True, description="ID of the module being taught"
            ),
            "group_id": fields.Integer(
                required=True, description="ID of the group attending"
            ),
            "semester_id": fields.Integer(
                required=True, description="ID of the semester"
            ),
            "salle_id": fields.Integer(
                description="ID of the room (salle), if assigned"
            ),
            # Use DateTime with format for clarity in Swagger UI
            "start_time": fields.DateTime(
                required=True,
                description="Start date and time of the session (ISO 8601 format)",
                dt_format="iso8601",
            ),
            "weeks": fields.Integer(
                description="Number of weeks the session repeats (if applicable)"
            ),
            # Consider adding nested fields for related objects if needed for display
            # "teacher_name": fields.String(attribute="teacher.name", readonly=True), # Example
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

    # Define the standard response structure for a list of sessions
    list_data_resp = api.model(
        "Session List Response",
        {
            "status": fields.Boolean(description="Indicates success or failure"),
            "message": fields.String(description="Response message"),
            "sessions": fields.List(
                fields.Nested(session), description="List of session data"
            ),
        },
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
            "salle_id": fields.Integer(description="ID of the room (salle)"),
            "start_time": fields.DateTime(
                required=True,
                description="Start date and time (ISO 8601 format)",
                dt_format="iso8601",
            ),
            "weeks": fields.Integer(description="Number of weeks the session repeats"),
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
                description="New start date and time (ISO 8601 format)",
                dt_format="iso8601",
            ),
            "weeks": fields.Integer(
                description="New number of weeks the session repeats"
            ),
        },
    )
