from flask_restx import Namespace, fields
from flask_restx.reqparse import RequestParser
from app.models.TimeSlot import TimeSlot # Assuming TimeSlot enum is here

class SessionDto:
    """Data Transfer Objects and Request Parsers for the Session API."""

    api = Namespace(
        "sessions", description="Class session scheduling related operations."
    )

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
        help="Filter sessions by the ID of the semester.",
    )
    session_filter_parser.add_argument( # ADDED semester_index filter
        "semester_index",
        type=int,
        location="args",
        required=False,
        help="Filter sessions by the semester index (e.g., 1 for 1st semester, 2 for 2nd).",
    )
    session_filter_parser.add_argument(
        "week", # Assuming 'weeks' in the model refers to a specific week number for filtering
        type=int,
        location="args",
        required=False,
        help="Filter sessions by the specific week number of the session.",
    )
    session_filter_parser.add_argument(
        'page',
        type=int,
        location='args',
        required=False,
        default=1,
        help='Page number for pagination (default: 1).'
    )
    session_filter_parser.add_argument(
         'per_page',
         type=int,
         location='args',
         required=False,
         default=10,
         help='Number of items per page (default: 10).'
     )

    session = api.model(
        "Session Object",
        {
            "id": fields.Integer(
                readonly=True, description="Session unique identifier"
            ),
            "teacher_id": fields.Integer(
                required=True, description="ID of the teacher conducting the session"
            ),
            "teacher_name": fields.String(
                readonly=True, description="Name of the teacher"
            ),
            "module_id": fields.Integer(
                required=True, description="ID of the module being taught"
            ),
            "module_name": fields.String(
                readonly=True, description="Name of the module"
            ),
            "group_id": fields.Integer(
                required=True, description="ID of the group attending the session"
            ),
            "group_name": fields.String(
                readonly=True, description="Name of the group"
            ),
            "semester_id": fields.Integer(
                required=True, description="ID of the semester the session belongs to"
            ),
            "semester_name": fields.String(
                readonly=True, description="Name of the semester"
            ),
            "semester_index": fields.Integer( # ADDED semester_index to response
                required=True, description="Index of the semester (e.g., 1st, 2nd) this session belongs to"
            ),
            "salle_id": fields.Integer(
                required=False,
                description="ID of the room (salle) where the session takes place, if assigned"
            ),
            "salle_name": fields.String(
                readonly=True, description="Name of the room (salle)"
            ),
            "time_slot": fields.String(
                required=True,
                description="Time slot for the session (e.g., 'd1h8-10' for Monday 8:00-10:00)",
                enum=[slot.value for slot in TimeSlot]
            ),
            "weeks": fields.Integer( # This 'weeks' field in the model seems to be for specific week of a session
                required=True, # Assuming a session is for a specific week, making it required
                description="The specific week number this session instance refers to (e.g., week 1 of the semester)"
            ),
        },
    )

    time_slot_pair = api.model('TimeSlotPair', {
        'teacher_id': fields.Integer(description='ID of the teacher'),
        'teacher_name': fields.String(description='Name of the teacher'),
        'module_id': fields.Integer(description='ID of the module'),
        'module_name': fields.String(description='Name of the module')
    })

    time_slots_response = api.model('TimeSlotsResponse', {
        'message': fields.String(description='Response message'),
        'time_slots': fields.Raw(description='Map of time slots to teacher-module pairs')
    })

    data_resp = api.model(
        "Session Data Response",
        {
            "status": fields.Boolean(description="Indicates success or failure"),
            "message": fields.String(description="Response message"),
            "session": fields.Nested(session, description="The session data"),
        },
    )

    list_data_resp = api.model(
        "Session List Response",
        {
            "status": fields.Boolean(description="Indicates success or failure"),
            "message": fields.String(description="Response message"),
            "sessions": fields.List(
                fields.Nested(session), description="List of session data for the current page"
            ),
            "total": fields.Integer(description="Total number of sessions matching the query"),
            "pages": fields.Integer(description="Total number of pages"),
            "current_page": fields.Integer(description="The current page number"),
            "per_page": fields.Integer(description="Number of items per page"),
            "has_next": fields.Boolean(description="True if there is a next page"),
            "has_prev": fields.Boolean(description="True if there is a previous page"),
        }
    )

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
            "semester_index": fields.Integer( # ADDED semester_index (required for creation)
                required=True, description="Index of the semester (e.g., 1 for 1st, 2 for 2nd)"
            ),
            "salle_id": fields.Integer(required=False, description="ID of the room (salle), optional"),
            "time_slot": fields.String(
                required=True,
                description="Time slot for the session (e.g., 'd1h8-10' for Monday 8:00-10:00)",
                enum=[slot.value for slot in TimeSlot]
            ),
            # "weeks" field: Clarification needed.
            # If creating sessions for *all* weeks of a semester_index, this field might not be needed here.
            # If creating a *single* session instance for a *specific week*, then it's needed.
            # The current service.create_session iterates through semester.duration.
            # If `Session.weeks` is meant to store *which specific week* this Session instance is for,
            # then it should be part of the model and DTO, but likely set by the service, not direct input here.
            # For now, I'll assume the service handles setting the 'weeks' for each created session instance.
            # If 'weeks' in the model means "duration of this specific session if it's a block", that's different.
            # Given the model has `Session.weeks`, I'll keep it in update DTO.
        },
    )
    session_update = api.model(
        "Session Update Input",
        {
            "teacher_id": fields.Integer(description="New ID of the teacher", required=False),
            "module_id": fields.Integer(description="New ID of the module", required=False),
            "group_id": fields.Integer(description="New ID of the group", required=False),
            "semester_id": fields.Integer(description="New ID of the semester", required=False),
            "semester_index": fields.Integer(description="New index of the semester", required=False), # ADDED
            "salle_id": fields.Integer(description="New ID of the room (salle)", required=False),
            "time_slot": fields.String(
                description="New time slot for the session",
                enum=[slot.value for slot in TimeSlot],
                required=False
            ),
            "weeks": fields.Integer( # If 'weeks' is the specific week number of this session instance
                description="New specific week number for this session instance",
                required=False
            ),
        },
    )
