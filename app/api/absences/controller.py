# Added current_app
from flask import request, current_app
from flask_restx import Resource
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt

# Import shared extensions/decorators
from app.extensions import limiter
from app.api.decorators import roles_required

# Import absence-specific modules
from .service import AbsenceService
from .dto import AbsenceDto

# Get the API namespace and DTOs
api = AbsenceDto.api
data_resp = AbsenceDto.data_resp
list_data_resp = AbsenceDto.list_data_resp
absence_create_input = AbsenceDto.absence_create_input
absence_update_input = AbsenceDto.absence_update_input
# Get the filter/pagination parser
absence_filter_parser = AbsenceDto.absence_filter_parser


# --- Helper to get current user info ---
def get_current_user_info():
    user_id = get_jwt_identity()
    claims = get_jwt()
    role = claims.get("role")
    current_app.logger.debug(
        f"Current user info: ID={user_id}, Role={role}"
    )  # Log user info
    return user_id, role


# --- Route for listing/creating absences ---
@api.route("/")
class AbsenceList(Resource):

    @api.doc(
        "List absences",
        security="Bearer",
        parser=absence_filter_parser,
        description="Get a paginated list of student absences. Filterable. Access restricted by role.",
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
    @roles_required("admin", "teacher", "parent", "student")  # Base roles allowed
    # Use config for rate limit
    @limiter.limit(
        lambda: current_app.config.get("RATE_LIMIT_ABSENCE_LIST", "60/minute")
    )
    def get(self):
        """Get a list of absences, filtered by query params and user role"""
        user_id, role = get_current_user_info()
        args = absence_filter_parser.parse_args()
        current_app.logger.debug(
            f"Received GET request for absences list with args: {args}"
        )

        # Pass filter, pagination, and user info to service for scoping
        return AbsenceService.get_all_absences(
            student_id=args.get("student_id"),
            session_id=args.get("session_id"),
            justified=args.get("justified"),
            start_date=args.get("start_date"),  # Filter based on session date
            end_date=args.get("end_date"),  # Filter based on session date
            page=args.get("page"),
            per_page=args.get("per_page"),
            current_user_id=user_id,
            current_user_role=role,
        )

    @api.doc(
        "Record a new absence",
        security="Bearer",
        description="Record a student's absence for a session (Teacher/Admin only). Teacher must be associated with the session.",
        responses={
            201: ("Created", data_resp),
            400: "Validation Error/Invalid Data/FK Not Found",
            401: "Unauthorized",
            403: "Forbidden (e.g., teacher not for this session)",
            409: "Conflict (Absence already recorded)",
            429: "Too Many Requests",
            500: "Internal Server Error",
        },
    )
    @api.expect(absence_create_input, validate=True)
    @jwt_required()
    @roles_required("admin", "teacher")  # Only these roles can create
    # Use config for rate limit
    @limiter.limit(
        lambda: current_app.config.get("RATE_LIMIT_ABSENCE_CREATE", "40/minute")
    )
    def post(self):
        """Record a new absence"""

        data = request.get_json()
        current_app.logger.debug(
            f"Received POST request to create absence with data: {data}"
        )
        user_id = get_jwt_identity()  # Get the user ID from JWT
        role = get_jwt()["role"]  # Get the role from JWT claims
        # Service handles authorization (is admin or teacher of the session)
        return AbsenceService.create_absence(data, user_id, role)


# --- Route for specific absence operations ---
@api.route("/<int:absence_id>")
@api.param("absence_id", "The unique identifier of the absence record")
class AbsenceResource(Resource):

    @api.doc(
        "Get a specific absence record by ID",
        security="Bearer",
        description="Get data for a specific absence record. Access restricted by role.",
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
    @roles_required("admin", "teacher", "parent", "student")  # Base roles allowed
    # Use config for rate limit
    @limiter.limit(
        lambda: current_app.config.get("RATE_LIMIT_ABSENCE_GET", "100/minute")
    )
    # Add type hint
    def get(self, absence_id: int):
        """Get a specific absence record's data by ID (with record-level access control)"""
        # Get user info for record-level access check in service
        current_app.logger.debug(f"Received GET request for absence ID: {absence_id}")
        # Pass user info for record-level check
        user_id = get_jwt_identity()
        role = get_jwt()["role"]
        return AbsenceService.get_absence_data(absence_id, user_id, role)

    @api.doc(
        "Update an absence record",
        security="Bearer",
        description="Update the justification status or reason for an absence (Admin or Teacher of the session only).",
        responses={
            200: ("Success", data_resp),
            400: "Validation Error/Invalid Data/Empty Body",
            401: "Unauthorized",
            403: "Forbidden",
            404: "Not Found",
            429: "Too Many Requests",
            500: "Internal Server Error",
        },
    )
    @api.expect(absence_update_input, validate=True)
    @jwt_required()
    @roles_required("admin", "teacher")  # Base roles allowed
    # Use config for rate limit
    @limiter.limit(
        lambda: current_app.config.get("RATE_LIMIT_ABSENCE_UPDATE", "50/minute")
    )
    # Add type hint
    def patch(self, absence_id: int):
        """Update an existing absence record (justification/reason)"""
        # Get user info for record-level access check in service
        data = request.get_json()
        current_app.logger.debug(
            f"Received PATCH request for absence ID {absence_id} with data: {data}"
        )
        # Service layer handles authorization (is admin or teacher of the session)
        user_id = get_jwt_identity()  # Get the user ID from JWT
        role = get_jwt()["role"]
        return AbsenceService.update_absence(absence_id, data, user_id, role)

    @api.doc(
        "Delete an absence record",
        security="Bearer",
        description="Delete an absence record (Admin or Teacher of the session only).",
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
    @roles_required("admin", "teacher")  # Base roles allowed
    # Use config for rate limit
    @limiter.limit(
        lambda: current_app.config.get("RATE_LIMIT_ABSENCE_DELETE", "30/minute")
    )
    # Add type hint
    def delete(self, absence_id: int):
        """Delete an absence record"""
        # Get user info for record-level access check in service
        current_app.logger.debug(
            f"Received DELETE request for absence ID: {absence_id}"
        )
        user_id = get_jwt_identity()
        role = get_jwt()["role"]
        # Service layer handles authorization (is admin or teacher of the session)
        return AbsenceService.delete_absence(absence_id, user_id, role)
