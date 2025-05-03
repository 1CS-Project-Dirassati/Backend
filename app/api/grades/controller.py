# Added current_app
from flask import request, current_app
from flask_restx import Resource
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt

# Import shared extensions/decorators
from app.extensions import limiter
from app.api.decorators import roles_required

# Import note-specific modules
from .service import NoteService
from .dto import NoteDto

# Get the API namespace and DTOs
api = NoteDto.api
data_resp = NoteDto.data_resp
list_data_resp = NoteDto.list_data_resp
note_create_input = NoteDto.note_create_input
note_update_input = NoteDto.note_update_input
# Get the filter/pagination parser
note_filter_parser = NoteDto.note_filter_parser


# --- Helper to get current user info ---
def get_current_user_info():
    user_id = get_jwt_identity()
    claims = get_jwt()
    role = claims.get("role")
    current_app.logger.debug(f"Current user info: ID={user_id}, Role={role}") # Log user info
    return user_id, role


# --- Route for listing/creating notes ---
@api.route("/")
class NoteList(Resource):

    @api.doc(
        "List notes (grades)",
        security="Bearer",
        parser=note_filter_parser,
        # Updated description
        description="Get a paginated list of notes (grades). Filterable. Access restricted by role (Admins see all, Teachers see own/relevant, Parents see own children, Students see self).",
        responses={
            200: ("Success", list_data_resp),
            401: "Unauthorized",
            403: "Forbidden",
            404: "Not Found (e.g., parent not found)",
            429: "Too Many Requests",
            500: "Internal Server Error",
        },
    )
    @jwt_required()
    @roles_required("admin", "teacher", "parent", "student")
    # Use config for rate limit
    @limiter.limit(lambda: current_app.config.get("RATE_LIMIT_NOTE_LIST", "60/minute"))
    def get(self):
        """Get a list of notes, filtered by query params, user role, and paginated"""
        user_id, role = get_current_user_info()
        args = note_filter_parser.parse_args()
        # Add logging
        current_app.logger.debug(
            f"Received GET request for notes list with args: {args}"
        )

        # Pass filter, pagination, and user info to service for scoping
        return NoteService.get_all_notes(
            student_id=args.get("student_id"),
            module_id=args.get("module_id"),
            teacher_id=args.get("teacher_id"),
            group_id=args.get("group_id"),
            page=args.get('page'), # Pass pagination arg
            per_page=args.get('per_page'), # Pass pagination arg
            current_user_id=user_id,
            current_user_role=role,
        )

    @api.doc(
        "Create a new note (grade)",
        security="Bearer",
        description="Create a new grade for a student in a module (Teacher/Admin only). Teacher ID is inferred.",
        responses={
            201: ("Created", data_resp),
            400: "Validation Error/Invalid Value/FK Not Found",
            401: "Unauthorized",
            403: "Forbidden",
            409: "Conflict (e.g., duplicate note)",
            429: "Too Many Requests",
            500: "Internal Server Error",
        },
    )
    @api.expect(note_create_input, validate=True)
    @jwt_required()
    @roles_required( "teacher") # Decorator handles role check
    # Use config for rate limit
    @limiter.limit(lambda: current_app.config.get("RATE_LIMIT_NOTE_CREATE", "30/minute"))
    def post(self):
        """Create a new note (grade)"""
        user_id, role = get_current_user_info() # Get user info for service logic
        data = request.get_json()
        # Add logging
        current_app.logger.debug(
            f"Received POST request to create note with data: {data}"
        )
        user_id = get_jwt_identity()
        role = get_jwt()["role"]
        # Service uses user_id as teacher_id if role is teacher
        return NoteService.create_note(data, user_id, role)


# --- Route for specific note operations ---
@api.route("/<int:note_id>")
@api.param("note_id", "The unique identifier of the note (grade)")
class NoteResource(Resource):

    @api.doc(
        "Get a specific note by ID",
        security="Bearer",
        description="Get data for a specific note. Access restricted by role.",
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
    @roles_required("admin", "teacher", "parent", "student") # Decorator handles base role check
    # Use config for rate limit
    @limiter.limit(lambda: current_app.config.get("RATE_LIMIT_NOTE_GET", "100/minute"))
    # Add type hint
    def get(self, note_id: int):
        """Get a specific note's data by ID (with record-level access control)"""
        # Get user info for record-level access check in service
        # Add logging
        current_app.logger.debug(
            f"Received GET request for note ID: {note_id}"
        )
        user_id = get_jwt_identity()
        role = get_jwt()["role"]
        # Pass user info for record-level check
        return NoteService.get_note_data(note_id, user_id, role)

    @api.doc(
        "Update a note (grade)",
        security="Bearer",
        description="Update the value or comment of a note (Admin or originating Teacher only).",
        responses={
            200: ("Success", data_resp),
            400: "Validation Error/Invalid Value/Empty Body",
            401: "Unauthorized",
            403: "Forbidden",
            404: "Not Found",
            409: "Conflict", # Added 409
            429: "Too Many Requests",
            500: "Internal Server Error",
        },
    )
    @api.expect(note_update_input, validate=True)
    @jwt_required()
    @roles_required("admin", "teacher") # Decorator handles base role check
    # Use config for rate limit
    @limiter.limit(lambda: current_app.config.get("RATE_LIMIT_NOTE_UPDATE", "40/minute"))
    # Add type hint
    def patch(self, note_id: int):
        """Update an existing note (value/comment)"""
        # Get user info for record-level access check in service
        user_id, role = get_current_user_info()
        data = request.get_json()
        # Add logging
        current_app.logger.debug(
            f"Received PATCH request for note ID {note_id} with data: {data}"
        )
        # Service layer handles authorization (is admin or original teacher)
        user_id = get_jwt_identity()
        role = get_jwt()["role"]
        return NoteService.update_note(note_id, data, user_id, role)

    @api.doc(
        "Delete a note (grade)",
        security="Bearer",
        description="Delete a note (Admin or originating Teacher only).",
        responses={
            204: "No Content - Success",
            401: "Unauthorized",
            403: "Forbidden",
            404: "Not Found",
            429: "Too Many Requests",
            500: "Internal Server Error",
        },
    )
    @jwt_required()
    @roles_required("admin", "teacher") # Decorator handles base role check
    # Use config for rate limit
    @limiter.limit(lambda: current_app.config.get("RATE_LIMIT_NOTE_DELETE", "20/minute"))
    # Add type hint
    def delete(self, note_id: int):
        """Delete a note (grade)"""
        # Get user info for record-level access check in service
        user_id, role = get_current_user_info()
        # Add logging
        current_app.logger.debug(
            f"Received DELETE request for note ID: {note_id}"
        )
        # Service layer handles authorization (is admin or original teacher)
        user_id = get_jwt_identity()
        role = get_jwt()["role"]
        return NoteService.delete_note(note_id, user_id, role)
