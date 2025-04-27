# Added current_app
from flask import request, current_app
from flask_restx import Resource
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt

# Import shared extensions/decorators
from app.extensions import limiter
from app.api.decorators import roles_required

# Import student-specific modules
from .service import StudentService
from .dto import StudentDto

# Get the API namespace and DTOs
api = StudentDto.api
data_resp = StudentDto.data_resp
list_data_resp = StudentDto.list_data_resp
student_create_input = StudentDto.student_create_input
student_update_input = StudentDto.student_update_input
student_approval_input = StudentDto.student_approval_input
student_filter_parser = StudentDto.student_filter_parser



# --- Route for listing/creating students ---
@api.route("/")
class StudentList(Resource):

    @api.doc(
        "List students",
        security="Bearer",
        parser=student_filter_parser,
        description="Get a paginated list of students. Filterable. Access restricted by role (Admins/Teachers see all, Parents see own children, Students see self).",
        responses={
            200: ("Success", list_data_resp),
            401: "Unauthorized",
            403: "Forbidden",
            429: "Too Many Requests",
            500: "Internal Server Error"
        },
    )
    @jwt_required()
    @roles_required('admin', 'teacher', 'parent', 'student')
    @limiter.limit(lambda: current_app.config.get("RATE_LIMIT_STUDENT_LIST", "50/minute"))
    def get(self):
        """ Get a list of students, filtered by query params, user role, and paginated """
        user_id = get_jwt_identity()  # Get the user ID from the JWT token
        role = get_jwt()['role']  # Get the role from the JWT token
        args = student_filter_parser.parse_args()
        current_app.logger.debug(
            f"Received GET request for students list with args: {args}"
        )

        # Pass role/id for data scoping in the service
        return StudentService.get_all_students(
            level_id=args.get('level_id'),
            group_id=args.get('group_id'),
            parent_id=args.get('parent_id'),
            is_approved=args.get('is_approved'),
            page=args.get('page'),
            per_page=args.get('per_page'),
            current_user_role=role,
            current_user_id=user_id
        )

    @api.doc(
        "Create a new student",
        security="Bearer",
        responses={
            201: ("Created", data_resp),
            400: "Validation Error/FK Not Found",
            401: "Unauthorized",
            403: "Forbidden",
            409: "Conflict (e.g., duplicate email)",
            429: "Too Many Requests",
            500: "Internal Server Error"
        }
    )
    @api.expect(student_create_input, validate=True)
    @jwt_required()
    @roles_required('admin',"parent") # Decorator handles role check
    @limiter.limit(lambda: current_app.config.get("RATE_LIMIT_STUDENT_CREATE", "10/minute"))
    def post(self):
        """ Create a new student (Admin only) """
        data = request.get_json()
        current_app.logger.debug(
            f"Received POST request to create student with data: {data}"
        )
        # No need to pass role, decorator handled it
        return StudentService.create_student(data)


# --- Route for specific student operations ---
@api.route("/<int:student_id>")
@api.param('student_id', 'The unique identifier of the student')
class StudentResource(Resource):

    @api.doc(
        "Get a specific student by ID",
        security="Bearer",
        description="Get data for a specific student. Access restricted to Admins, Teachers, the student themselves, or their parent.",
        responses={
            200: ("Success", data_resp),
            401: "Unauthorized",
            403: "Forbidden",
            404: "Not Found",
            429: "Too Many Requests",
            500: "Internal Server Error"
        }
    )
    @jwt_required()
    @roles_required('admin', 'teacher', 'parent', 'student') # Decorator handles role check
    @limiter.limit(lambda: current_app.config.get("RATE_LIMIT_STUDENT_GET", "100/minute"))
    def get(self, student_id: int):
        """ Get a specific student's data by ID (with record-level access control) """
        # Get user info for record-level access check in service
        current_app.logger.debug(
            f"Received GET request for student ID: {student_id}"
        )
        user_id = get_jwt_identity()  # Get the user ID from the JWT token
        role = get_jwt()['role']  # Get the role from the JWT token
        parent_id_for_check = None
        # Pass user info for record-level check
        return StudentService.get_student_data(student_id, user_id, role, parent_id_for_check)

    @api.doc(
        "Update a student",
        security="Bearer",
        description="Update limited fields for a student (Admin only).",
        responses={
            200: ("Success", data_resp),
            400: "Validation Error/FK Not Found/Empty Body",
            401: "Unauthorized",
            403: "Forbidden",
            404: "Not Found",
            409: "Conflict",
            429: "Too Many Requests",
            500: "Internal Server Error"
        }
    )
    @api.expect(student_update_input, validate=True)
    @jwt_required()
    @roles_required('admin',"parent") # Decorator handles role check
    @limiter.limit(lambda: current_app.config.get("RATE_LIMIT_STUDENT_UPDATE", "30/minute"))
    def put(self, student_id: int):
        """ Update an existing student (Admin only) """
        # No need to get role here
        data = request.get_json()
        current_app.logger.debug(
            f"Received PUT request for student ID {student_id} with data: {data}"
        )
        # No need to pass role, decorator handled it
        return StudentService.update_student(student_id, data)

    @api.doc(
        "Delete a student",
        security="Bearer",
        description="Delete a student (Admin only).",
        responses={
            204: "No Content - Success",
            401: "Unauthorized",
            403: "Forbidden",
            404: "Not Found",
            409: "Conflict",
            429: "Too Many Requests",
            500: "Internal Server Error"
        }
    )
    @jwt_required()
    @roles_required('admin',"parent") # Decorator handles role check
    @limiter.limit(lambda: current_app.config.get("RATE_LIMIT_STUDENT_DELETE", "10/minute"))
    def delete(self, student_id: int):
        """ Delete a student (Admin only) """
        # No need to get role here
        current_app.logger.debug(
            f"Received DELETE request for student ID: {student_id}"
        )
        # No need to pass role, decorator handled it
        return StudentService.delete_student(student_id)


# --- Route specifically for updating approval status ---
@api.route("/<int:student_id>/approval")
@api.param('student_id', 'The unique identifier of the student')
class StudentApproval(Resource):

     @api.doc(
        "Update student approval status",
        security="Bearer",
        description="Set the approval status for a student (Admin only).",
        responses={
            200: ("Success", data_resp),
            400: "Validation Error",
            401: "Unauthorized",
            403: "Forbidden",
            404: "Not Found",
            429: "Too Many Requests",
            500: "Internal Server Error"
        }
    )
     @api.expect(student_approval_input, validate=True)
     @jwt_required()
     @roles_required('admin',"parent") # Decorator handles role check
     @limiter.limit(lambda: current_app.config.get("RATE_LIMIT_STUDENT_APPROVE", "20/minute"))
     def patch(self, student_id: int):
        """ Update a student's approval status (Admin only) """
        # No need to get role here
        data = request.get_json()
        current_app.logger.debug(
            f"Received PATCH request for student ID {student_id} approval with data: {data}"
        )
        # No need to pass role, decorator handled it
        return StudentService.update_approval_status(student_id, data)
