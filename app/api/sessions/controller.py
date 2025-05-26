from flask import request, current_app
from flask_restx import Resource, fields
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt

from app.extensions import limiter
from app.api.decorators import roles_required

from .service import SessionService
from .dto import SessionDto

api = SessionDto.api
data_resp = SessionDto.data_resp
list_data_resp = SessionDto.list_data_resp
session_create_dto = SessionDto.session_create
session_update_dto = SessionDto.session_update
session_filter_parser = SessionDto.session_filter_parser

time_slot_pair = api.model( # This seems to be a duplicate from DTO, ensure it's defined once
    "TimeSlotPair",
    {
        "teacher_name": fields.String(description="Name of the teacher"),
        "module_name": fields.String(description="Name of the module"),
    },
)

time_slots_response = api.model( # Duplicate from DTO
    "TimeSlotsResponse",
    {
        "message": fields.String(description="Response message"),
        "time_slots": fields.Raw(
            description="Map of time slots to teacher-module pairs"
        ),
    },
)


@api.route("/")
class SessionList(Resource):

    @api.doc(
        "List sessions",
        security="Bearer",
        parser=session_filter_parser,
        description="Get a paginated list of sessions. Filterable by group_id, teacher_id, semester_id, semester_index, or week.", # Updated description
        responses={
            200: ("Success", list_data_resp),
            401: "Unauthorized",
            403: "Forbidden",
            429: "Too Many Requests",
            500: "Internal Server Error",
        },
    )
    @jwt_required()
    @roles_required("admin", "teacher", "student", "parent")
    @limiter.limit(
        lambda: current_app.config.get("RATE_LIMIT_SESSION_LIST", "100/minute")
    )
    def get(self):
        """Get a list of sessions, optionally filtered and paginated"""
        args = session_filter_parser.parse_args()
        # group_id_filter = args.get("group_id") # Redundant, directly use args.get
        # teacher_id_filter = args.get("teacher_id")
        # semester_id_filter = args.get("semester_id")
        # week_filter = args.get("week")
        # page = args.get("page")
        # per_page = args.get("per_page")

        current_user_id = get_jwt_identity()
        current_user_role = get_jwt()["role"]

        current_app.logger.debug(
            f"Received GET request for sessions with args: {args} by user {current_user_id} ({current_user_role})"
        )

        return SessionService.get_all_sessions(
            group_id=args.get("group_id"),
            teacher_id=args.get("teacher_id"),
            semester_id=args.get("semester_id"),
            semester_index=args.get("semester_index"), # ADDED semester_index
            week=args.get("week"),
            page=args.get("page"),
            per_page=args.get("per_page"),
            current_user_id=current_user_id,
            current_user_role=current_user_role,
        )

    @api.doc(
        "Create new session(s)", # Updated description to reflect multiple creations
        security="Bearer",
        description="Create new session instances for each week of the specified semester based on its duration. Requires 'semester_index'.", # Updated
        responses={
            201: ("Created", list_data_resp), # Changed to list_data_resp if multiple are created
            400: "Validation Error/FK Not Found",
            401: "Unauthorized",
            403: "Forbidden",
            429: "Too Many Requests",
            500: "Internal Server Error",
        },
    )
    @api.expect(session_create_dto, validate=True)
    @jwt_required()
    @roles_required("admin") # Typically admin or a coordinator role
    @limiter.limit(
        lambda: current_app.config.get("RATE_LIMIT_SESSION_CREATE", "20/minute")
    )
    def post(self):
        """Create new class session instances for a semester"""
        data = request.get_json()
        current_app.logger.debug(
            f"Received POST request to create session(s) with data: {data}"
        )
        # The service method `create_session` now handles the semester_index from `data`
        return SessionService.create_session(data)


@api.route("/<int:session_id>")
@api.param("session_id", "The unique identifier of the session")
class SessionResource(Resource):

    @api.doc(
        "Get a specific session by ID",
        security="Bearer",
        responses={
            200: ("Success", data_resp),
            401: "Unauthorized",
            403: "Forbidden",
            404: "Not Found",
            429: "Too Many Requests",
            500: "Internal Server Error",
        },
    )
    @jwt_required()
    @roles_required("admin", "teacher", "student", "parent")
    @limiter.limit(
        lambda: current_app.config.get("RATE_LIMIT_SESSION_GET", "100/minute")
    )
    def get(self, session_id: int):
        """Get a specific session's data by its ID"""
        current_app.logger.debug(
            f"Received GET request for session ID: {session_id}"
        )
        # user_id and role can be fetched if needed for service layer authorization
        # user_id = get_jwt_identity()
        # role = get_jwt()['role']
        return SessionService.get_session_data(session_id)

    @api.doc(
        "Update a session",
        security="Bearer",
        description="Update an existing class session. Can include 'semester_index'.", # Updated
        responses={
            200: ("Success", data_resp),
            400: "Validation Error/FK Not Found/Empty Body",
            401: "Unauthorized",
            403: "Forbidden",
            404: "Not Found",
            429: "Too Many Requests",
            500: "Internal Server Error",
        },
    )
    @api.expect(session_update_dto, validate=True)
    @jwt_required()
    @roles_required("admin") # Typically admin or coordinator
    @limiter.limit(
        lambda: current_app.config.get("RATE_LIMIT_SESSION_UPDATE", "30/minute")
    )
    def put(self, session_id: int): # Changed to PUT for full update, PATCH for partial
        """Update an existing class session"""
        data = request.get_json()
        current_app.logger.debug(
            f"Received PUT request for session ID {session_id} with data: {data}"
        )
        return SessionService.update_session(session_id, data)

    @api.doc(
        "Delete a session",
        security="Bearer",
        responses={
            204: "No Content - Success",
            401: "Unauthorized",
            403: "Forbidden",
            404: "Not Found",
            409: "Conflict (e.g., cannot delete due to dependencies)",
            429: "Too Many Requests",
            500: "Internal Server Error",
        },
    )
    @jwt_required()
    @roles_required("admin") # Typically admin or coordinator
    @limiter.limit(
        lambda: current_app.config.get("RATE_LIMIT_SESSION_DELETE", "10/minute")
    )
    def delete(self, session_id: int):
        """Delete a class session"""
        current_app.logger.debug(
            f"Received DELETE request for session ID: {session_id}"
        )
        return SessionService.delete_session(session_id)


@api.route("/group/<int:group_id>/time-slots")
class GroupTimeSlots(Resource):
    @api.doc(
        "Get time slot map for a group",
        security="Bearer",
        description="Get a map of time slots with teacher-module pairs for a specific group. This is a utility endpoint.", # Added clarification
        responses={
            200: ("Success", SessionDto.time_slots_response), # Using DTO for response model
            401: "Unauthorized",
            403: "Forbidden",
            404: "Group not found",
            429: "Too Many Requests",
            500: "Internal Server Error",
        },
    )
    @jwt_required()
    @roles_required("admin", "teacher") # Typically admin or teacher planning
    @limiter.limit(
        lambda: current_app.config.get("RATE_LIMIT_GROUP_TIMESLOTS", "60/minute") # New rate limit key
    )
    def get(self, group_id: int): # Added type hint
        """Get a map of time slots with teacher-module pairs for a specific group"""
        current_app.logger.debug(f"Received GET request for time slots for group ID: {group_id}")
        return SessionService.get_group_time_slots(group_id)

