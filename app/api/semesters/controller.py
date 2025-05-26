from flask import request, current_app
from flask_restx import Resource
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt

from app.extensions import limiter
from app.api.decorators import roles_required

from .service import SemesterService
from .dto import SemesterDto

api = SemesterDto.api
data_resp = SemesterDto.data_resp
list_data_resp = SemesterDto.list_data_resp
semester_create_input = SemesterDto.semester_create_input
semester_update_input = SemesterDto.semester_update_input
semester_filter_parser = SemesterDto.semester_filter_parser


def get_current_user_info():
    user_id = get_jwt_identity()
    claims = get_jwt()
    role = claims.get("role")
    current_app.logger.debug(
        f"Current user info: ID={user_id}, Role={role}"
    )
    return user_id, role


@api.route("/")
class SemesterList(Resource):

    @api.doc(
        "List semesters",
        security="Bearer",
        parser=semester_filter_parser,
        description="Get a list of semesters. Filterable by level_id, semester_index, and date range.", # Updated description
        responses={
            200: ("Success", list_data_resp),
            401: "Unauthorized",
            403: "Forbidden",
            429: "Too Many Requests",
            500: "Internal Server Error",
        },
    )
    @jwt_required()
    @roles_required("admin", "teacher", "parent", "student") # Expanded roles for viewing semesters
    @limiter.limit("60/minute")
    def get(self):
        """Get a list of semesters, filtered by query params"""
        user_id, role = get_current_user_info()
        args = semester_filter_parser.parse_args()
        current_app.logger.debug(
            f"Received GET request for semesters list with args: {args}"
        )
        return SemesterService.get_all_semesters(
            level_id=args.get("level_id"),
            semester_index=args.get("semester_index"), # ADDED semester_index
            start_date=args.get("start_date"),
            end_date=args.get("end_date"),
            page=args.get("page"), # Added page
            per_page=args.get("per_page"), # Added per_page
            current_user_id=user_id,
            current_user_role=role,
        )

    @api.doc(
        "Create a new semester",
        security="Bearer",
        description="Create a new academic semester. Requires 'semester_index'. (Admin only).", # Updated description
        responses={
            201: ("Created", data_resp),
            400: "Validation Error/Invalid Data",
            401: "Unauthorized",
            403: "Forbidden",
            429: "Too Many Requests",
            500: "Internal Server Error",
        },
    )
    @api.expect(semester_create_input, validate=True)
    @jwt_required()
    @roles_required("admin")
    @limiter.limit("30/minute")
    def post(self):
        """Create a new semester"""
        user_id, role = get_current_user_info() # Though role isn't strictly used in service for create logic beyond decorator
        data = request.get_json()
        current_app.logger.debug(
            f"Received POST request to create semester with data: {data}"
        )
        # user_id and role are passed for consistency, though service might not use them if decorator handles all auth
        return SemesterService.create_semester(data, user_id, role)


@api.route("/<int:semester_id>")
@api.param("semester_id", "The unique identifier of the semester")
class SemesterResource(Resource):

    @api.doc(
        "Get a specific semester by ID",
        security="Bearer",
        description="Get data for a specific semester.",
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
    @roles_required("admin", "teacher", "parent", "student") # Expanded roles
    @limiter.limit("100/minute")
    def get(self, semester_id: int): # Added type hint
        """Get a specific semester's data by ID"""
        user_id, role = get_current_user_info()
        current_app.logger.debug(f"Received GET request for semester ID: {semester_id}")
        return SemesterService.get_semester_data(semester_id, user_id, role)

    @api.doc(
        "Update a semester",
        security="Bearer",
        description="Update details of a semester, including 'semester_index'. (Admin only).", # Updated description
        responses={
            200: ("Success", data_resp),
            400: "Validation Error/Invalid Data",
            401: "Unauthorized",
            403: "Forbidden",
            404: "Not Found",
            429: "Too Many Requests",
            500: "Internal Server Error",
        },
    )
    @api.expect(semester_update_input, validate=True)
    @jwt_required()
    @roles_required("admin")
    @limiter.limit("40/minute")
    def patch(self, semester_id: int): # Added type hint
        """Update details of a semester"""
        user_id, role = get_current_user_info() # For consistency
        data = request.get_json()
        current_app.logger.debug(
            f"Received PATCH request for semester ID {semester_id} with data: {data}"
        )
        return SemesterService.update_semester(semester_id, data, user_id, role)

    @api.doc(
        "Delete a semester",
        security="Bearer",
        description="Delete a semester (Admin only).",
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
    @roles_required("admin")
    @limiter.limit("20/minute")
    def delete(self, semester_id: int): # Added type hint
        """Delete a semester"""
        user_id, role = get_current_user_info() # For consistency
        current_app.logger.debug(
            f"Received DELETE request for semester ID: {semester_id}"
        )
        return SemesterService.delete_semester(semester_id, user_id, role)
