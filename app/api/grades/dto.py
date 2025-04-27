from flask_restx import Namespace, fields
from flask_restx.reqparse import RequestParser


class NoteDto:
    """Data Transfer Objects and Request Parsers for the Note (Grade) API."""  # Updated docstring

    # Define the namespace
    api = Namespace("notes", description="Student grade (note) related operations.")

    # --- Parser for Query Parameters (Filters and Pagination) ---
    note_filter_parser = RequestParser(bundle_errors=True)
    note_filter_parser.add_argument(
        "student_id",
        type=int,
        location="args",
        required=False,
        help="Filter notes by the ID of the student.",
    )
    note_filter_parser.add_argument(
        "module_id",
        type=int,
        location="args",
        required=False,
        help="Filter notes by the ID of the module.",
    )
    note_filter_parser.add_argument(
        "teacher_id",
        type=int,
        location="args",
        required=False,
        help="Filter notes by the ID of the teacher who gave the grade (Admin view only).",  # Clarified help
    )
    note_filter_parser.add_argument(  # Added page
        "page",
        type=int,
        location="args",
        required=False,
        default=1,
        help="Page number for pagination (default: 1).",
    )
    note_filter_parser.add_argument(  # Added per_page
        "per_page",
        type=int,
        location="args",
        required=False,
        default=10,  # Consider a higher default?
        help="Number of items per page (default: 10).",
    )
    # Consider adding semester/period filters if applicable

    # Define the core 'note' object model
    note = api.model(
        "Note Object",
        {
            "id": fields.Integer(readonly=True, description="Note unique identifier"),
            "student_id": fields.Integer(
                required=True, description="ID of the student receiving the grade"
            ),
            "module_id": fields.Integer(
                required=True, description="ID of the module the grade is for"
            ),
            "teacher_id": fields.Integer(
                required=True,
                readonly=True,
                description="ID of the teacher who gave the grade",  # Readonly usually
            ),
            "value": fields.Float(
                required=True,
                description="The numerical value of the grade (e.g., 0-20)",  # Added range example
            ),
            "comment": fields.String(
                required=False, description="Optional comment from the teacher"
            ),  # Optional
            "created_at": fields.DateTime(
                readonly=True,
                description="Timestamp of grade creation (UTC)",  # Added UTC
            ),
            # Include related info for context (can be enriched in service if NoteSchema supports it)
            # "student_name": fields.String(attribute="student.user.name", readonly=True), # Example
            # "module_name": fields.String(attribute="module.name", readonly=True), # Example
            # "teacher_name": fields.String(attribute="teacher.user.name", readonly=True), # Example
        },
    )

    # Standard response for a single note
    data_resp = api.model(
        "Note Data Response",
        {
            "status": fields.Boolean(description="Indicates success or failure"),
            "message": fields.String(description="Response message"),
            "note": fields.Nested(note, description="The note (grade) data"),
        },
    )

    # Standard response for a list of notes (includes pagination)
    list_data_resp = api.model(
        "Note List Response",
        {
            "status": fields.Boolean(description="Indicates success or failure"),
            "message": fields.String(description="Response message"),
            # Updated description
            "notes": fields.List(
                fields.Nested(note),
                description="List of note (grade) data for the current page",
            ),
            # Pagination metadata fields
            "total": fields.Integer(
                description="Total number of notes matching the query"
            ),
            "pages": fields.Integer(description="Total number of pages"),
            "current_page": fields.Integer(description="The current page number"),
            "per_page": fields.Integer(description="Number of items per page"),
            "has_next": fields.Boolean(description="True if there is a next page"),
            "has_prev": fields.Boolean(description="True if there is a previous page"),
        },
    )

    # --- DTOs for POST/PATCH ---
    # Input for creating a new grade
    note_create_input = api.model(
        "Note Create Input (Teacher/Admin)",  # Clarified title
        {
            "student_id": fields.Integer(
                required=True,
                description="ID of the student receiving the grade",  # Clarified
            ),
            "module_id": fields.Integer(required=True, description="ID of the module"),
            # teacher_id is inferred from the logged-in user by the service
            "value": fields.Float(
                required=True,
                description="The numerical grade value (e.g., 0-20)",  # Added range example
            ),
            "comment": fields.String(
                required=False, description="Optional comment about the grade"
            ),  # Optional, clarified
        },
    )

    # Input for updating an existing grade (PATCH)
    note_update_input = api.model(
        "Note Update Input (Teacher/Admin)",  # Clarified title
        {
            "value": fields.Float(
                required=False,
                description="The updated numerical grade value (e.g., 0-20)",
            ),  # Optional
            "comment": fields.String(
                required=False,
                description="Updated optional comment (can be empty string to clear)",
            ),  # Optional
            # student_id, module_id, teacher_id are not changed via PATCH
        },
    )
