from flask_restx import Namespace, fields
from flask_restx.reqparse import RequestParser


class NoteDto:
    # Define the namespace
    api = Namespace("notes", description="Student grade (note) related operations.")

    # --- Parser for Query Parameters ---
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
        help="Filter notes by the ID of the teacher who gave the grade (Admin/Teacher view).",
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
                required=True, description="ID of the teacher who gave the grade"
            ),
            "value": fields.Float(
                required=True, description="The numerical value of the grade"
            ),
            "comment": fields.String(description="Optional comment from the teacher"),
            "created_at": fields.DateTime(
                readonly=True, description="Timestamp of creation"
            ),
            # Include related info for context (can be enriched in service)
            # "student_name": fields.String(readonly=True, description="Student's full name"),
            # "module_name": fields.String(readonly=True, description="Module name"),
            # "teacher_name": fields.String(readonly=True, description="Teacher's full name"),
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

    # Standard response for a list of notes
    list_data_resp = api.model(
        "Note List Response",
        {
            "status": fields.Boolean(description="Indicates success or failure"),
            "message": fields.String(description="Response message"),
            "notes": fields.List(
                fields.Nested(note), description="List of note (grade) data"
            ),
        },
    )

    # --- DTOs for POST/PUT ---
    # Input for creating a new grade
    note_create_input = api.model(
        "Note Create Input",
        {
            "student_id": fields.Integer(
                required=True, description="ID of the student"
            ),
            "module_id": fields.Integer(required=True, description="ID of the module"),
            # teacher_id will likely be derived from the logged-in user (teacher)
            "value": fields.Float(
                required=True, description="The numerical grade value (e.g., 0-20)"
            ),
            "comment": fields.String(description="Optional comment"),
        },
    )

    # Input for updating an existing grade (usually only value and comment)
    note_update_input = api.model(
        "Note Update Input",
        {
            "value": fields.Float(description="The updated numerical grade value"),
            "comment": fields.String(description="Updated optional comment"),
            # student_id, module_id, teacher_id are typically not changed
        },
    )
