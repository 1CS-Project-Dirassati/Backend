from flask import request
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
note_filter_parser = NoteDto.note_filter_parser


# --- Helper to get current user info ---
def get_current_user_info():
    user_id = get_jwt_identity()
    claims = get_jwt()
    role = claims.get("role")
    # is_super = claims.get('is_super_admin', False) # If needed for admin checks
    return user_id, role  # , is_super


# --- Route for listing/creating notes ---
@api.route("/")
class NoteList(Resource):

    @api.doc(
        "List notes (grades)",
        security="Bearer",
        parser=note_filter_parser,
        description="Get a list of notes (grades). Filterable. Access restricted by role (Admins see all, Teachers see own/relevant, Parents see own children, Students see self).",
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
    # Allow all authenticated roles to hit the endpoint; service layer handles fine-grained access
    @roles_required("admin", "teacher", "parent", "student")
    @limiter.limit("60/minute")
    def get(self):
        """Get a list of notes, filtered by query params and user role"""
        user_id, role = get_current_user_info()
        args = note_filter_parser.parse_args()

        return NoteService.get_all_notes(
            student_id=args.get("student_id"),
            module_id=args.get("module_id"),
            teacher_id=args.get(
                "teacher_id"
            ),  # Service checks role before applying this
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
    @roles_required("admin", "teacher")  # Only these roles can create
    @limiter.limit("30/minute")
    def post(self):
        """Create a new note (grade)"""
        user_id, role = get_current_user_info()
        data = request.get_json()
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
    @roles_required(
        "admin", "teacher", "parent", "student"
    )  # Allow all roles to attempt access
    @limiter.limit("100/minute")
    def get(self, note_id):
        """Get a specific note's data by ID (with access control)"""
        user_id, role = get_current_user_info()
        # Service layer handles the authorization check
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
            429: "Too Many Requests",
            500: "Internal Server Error",
        },
    )
    @api.expect(note_update_input, validate=True)
    @jwt_required()
    @roles_required("admin", "teacher")  # Only these roles can attempt update
    @limiter.limit("40/minute")
    def patch(self, note_id):  # Use PATCH for partial updates
        """Update an existing note (value/comment)"""
        user_id, role = get_current_user_info()
        data = request.get_json()
        # Service layer handles authorization (is admin or original teacher)
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
    @roles_required("admin", "teacher")  # Only these roles can attempt delete
    @limiter.limit("20/minute")
    def delete(self, note_id):
        """Delete a note (grade)"""
        user_id, role = get_current_user_info()
        # Service layer handles authorization (is admin or original teacher)
        return NoteService.delete_note(note_id, user_id, role)
