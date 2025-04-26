from flask import request
from flask_restx import Resource
from flask_jwt_extended import jwt_required

# Import shared extensions/decorators
from app.extensions import limiter
from app.api.decorators import roles_required  # Adjust path if necessary

# Import session-specific modules
from .service import SessionService
from .dto import SessionDto

# Get the API namespace and DTOs
api = SessionDto.api
data_resp = SessionDto.data_resp
list_data_resp = SessionDto.list_data_resp
session_create_dto = SessionDto.session_create
session_update_dto = SessionDto.session_update
session_filter_parser = SessionDto.session_filter_parser  # Get the filter parser


# --- Route for listing/creating sessions ---
@api.route("/")
class SessionList(Resource):

    @api.doc(
        "List sessions",
        security="Bearer",
        parser=session_filter_parser,  # Add parser for filter documentation
        description="Get a list of sessions. Optionally filter by group_id or teacher_id.",
        responses={
            200: ("Success", list_data_resp),
            401: "Unauthorized",
            429: "Too Many Requests",
            500: "Internal Server Error",
        },
    )
    @jwt_required()
    @roles_required(
        "admin", "teacher", "student", "parent"
    )  # Adjust roles - who needs to see schedules?
    @limiter.limit("100/minute")
    def get(self):
        """Get a list of sessions, optionally filtered"""
        args = session_filter_parser.parse_args()
        group_id_filter = args.get("group_id")
        teacher_id_filter = args.get("teacher_id")

        return SessionService.get_all_sessions(
            group_id=group_id_filter, teacher_id=teacher_id_filter
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
    @roles_required(
        "admin", "teacher"
    )  # Typically admins or teachers schedule sessions
    @limiter.limit("20/minute")
    def post(self):
        """Create a new class session"""
        data = request.get_json()
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
            404: "Not Found",
            429: "Too Many Requests",
            500: "Internal Server Error",
        },
    )
    @jwt_required()
    @roles_required("admin", "teacher", "student", "parent")  # Adjust roles
    @limiter.limit("100/minute")
    def get(self, session_id):
        """Get a specific session's data by its ID"""
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
    @roles_required("admin", "teacher")  # Roles who can modify schedules
    @limiter.limit("30/minute")
    def put(self, session_id):
        """Update an existing class session"""
        data = request.get_json()
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
    @roles_required("admin", "teacher")  # Roles who can delete schedules
    @limiter.limit("10/minute")
    def delete(self, session_id):
        """Delete a class session"""
        return SessionService.delete_session(session_id)
