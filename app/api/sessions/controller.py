from flask import request, current_app  # Added current_app
from flask_restx import Resource
from flask_jwt_extended import jwt_required

# Import shared extensions/decorators
from app.extensions import limiter
from app.api.decorators import roles_required

# Import session-specific modules
from .service import SessionService
from .dto import SessionDto

# Get the API namespace and DTOs
api = SessionDto.api
data_resp = SessionDto.data_resp
list_data_resp = SessionDto.list_data_resp
session_create_dto = SessionDto.session_create
session_update_dto = SessionDto.session_update
session_filter_parser = (
    SessionDto.session_filter_parser
)  # Get the filter/pagination parser


# --- Route for listing/creating sessions ---
@api.route("/")
class SessionList(Resource):

    @api.doc(
        "List sessions",
        security="Bearer",
        parser=session_filter_parser,
        description="Get a paginated list of sessions. Optionally filter by group_id or teacher_id.",  # Updated description
        responses={
            200: ("Success", list_data_resp),
            401: "Unauthorized",
            403: "Forbidden",  # Added 403
            429: "Too Many Requests",
            500: "Internal Server Error",
        },
    )
    @jwt_required()
    @roles_required("admin", "teacher", "student", "parent")
    @limiter.limit(
        lambda: current_app.config.get("RATE_LIMIT_SESSION_LIST", "100/minute")
    )  # Use config
    def get(self):
        """Get a list of sessions, optionally filtered and paginated"""
        args = session_filter_parser.parse_args()
        group_id_filter = args.get("group_id")
        teacher_id_filter = args.get("teacher_id")
        semester_id_filter=args.get("semester_id")
        page = args.get("page")
        per_page = args.get("per_page")
        current_app.logger.debug(
            f"Received GET request for sessions with args: {args}"
        )  # Add logging

        return SessionService.get_all_sessions(
            group_id=group_id_filter,
            teacher_id=teacher_id_filter,
            semester_id=semester_id_filter,
            page=page,  # Pass pagination args
            per_page=per_page,  # Pass pagination args
        )

    @api.doc(
        "Create a new session",
        security="Bearer",
        responses={
            201: ("Created", data_resp),
            400: "Validation Error/FK Not Found",
            401: "Unauthorized",
            403: "Forbidden",
            429: "Too Many Requests",
            500: "Internal Server Error",
        },
    )
    @api.expect(session_create_dto, validate=True)
    @jwt_required()
    @roles_required("admin", "teacher","parent")
    @limiter.limit(
        lambda: current_app.config.get("RATE_LIMIT_SESSION_CREATE", "20/minute")
    )  # Use config
    def post(self):
        """Create a new class session"""
        data = request.get_json()
        current_app.logger.debug(
            f"Received POST request to create session with data: {data}"
        )  # Add logging
        return SessionService.create_session(data)


# --- Route for specific session operations ---
@api.route("/<int:session_id>")
@api.param("session_id", "The unique identifier of the session")
class SessionResource(Resource):

    @api.doc(
        "Get a specific session by ID",
        security="Bearer",
        responses={
            200: ("Success", data_resp),
            401: "Unauthorized",
            403: "Forbidden",  # Added 403
            404: "Not Found",
            429: "Too Many Requests",
            500: "Internal Server Error",
        },
    )
    @jwt_required()
    @roles_required("admin", "teacher", "student", "parent")
    @limiter.limit(
        lambda: current_app.config.get("RATE_LIMIT_SESSION_GET", "100/minute")
    )  # Use config
    def get(
        self, session_id: int
    ):  # -> Tuple[Dict[str, Any], int]: # Suggestion: Add type hints
        """Get a specific session's data by its ID"""
        current_app.logger.debug(
            f"Received GET request for session ID: {session_id}"
        )  # Add logging
        return SessionService.get_session_data(session_id)

    @api.doc(
        "Update a session",
        security="Bearer",
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
    @roles_required("admin", "teacher","parent")
    @limiter.limit(
        lambda: current_app.config.get("RATE_LIMIT_SESSION_UPDATE", "30/minute")
    )  # Use config
    def put(
        self, session_id: int
    ):  # -> Tuple[Dict[str, Any], int]: # Suggestion: Add type hints
        """Update an existing class session"""
        data = request.get_json()
        current_app.logger.debug(
            f"Received PUT request for session ID {session_id} with data: {data}"
        )  # Add logging
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
    @roles_required("admin", "teacher","parent")
    @limiter.limit(
        lambda: current_app.config.get("RATE_LIMIT_SESSION_DELETE", "10/minute")
    )  # Use config
    def delete(
        self, session_id: int
    ):  # -> Tuple[None, int]: # Suggestion: Add type hints
        """Delete a class session"""
        current_app.logger.debug(
            f"Received DELETE request for session ID: {session_id}"
        )  # Add logging
        return SessionService.delete_session(session_id)
