from flask import request
from flask_restx import Resource
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt

# Import shared extensions/decorators
from app.extensions import limiter
from app.api.decorators import roles_required # Adjust path if necessary

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
student_filter_parser = StudentDto.student_filter_parser # Get the filter parser


# --- Helper to get current user info ---
def get_current_user_info():
    user_id = get_jwt_identity()
    claims = get_jwt()
    role = claims.get('role')
    # Assuming parent ID might also be in claims if role is parent
    parent_id_claim = claims.get('parent_id') if role == 'parent' else None
    # Important: Ensure parent_id in JWT claim actually corresponds to Parent model ID
    # For simplicity here, we assume jwt identity IS the parent_id if role is parent
    parent_id_for_check = user_id if role == 'parent' else None
    return user_id, role, parent_id_for_check

# --- Route for listing/creating students ---
@api.route("/")
class StudentList(Resource):

    @api.doc(
        "List students",
        security="Bearer",
        parser=student_filter_parser,
        description="Get a list of students. Filterable. Access restricted by role (Admins/Teachers see all, Parents see own children, Students see self).",
        responses={200: ("Success", list_data_resp), 401: "Unauthorized", 403: "Forbidden", 429: "Too Many Requests", 500: "Internal Server Error"},
    )
    @jwt_required()
    @roles_required('admin', 'teacher', 'parent', 'student') # Roles allowed to access the endpoint
    @limiter.limit("50/minute")
    def get(self):
        """ Get a list of students, filtered by query params and user role """
        user_id, role, _ = get_current_user_info() # Don't need parent_id here
        args = student_filter_parser.parse_args()

        return StudentService.get_all_students(
            level_id=args.get('level_id'),
            group_id=args.get('group_id'),
            parent_id=args.get('parent_id'), # Service checks role before applying this
            is_approved=args.get('is_approved'),
            current_user_role=role,
            current_user_id=user_id
        )

    @api.doc(
        "Create a new student",
        security="Bearer",
        responses={201: ("Created", data_resp), 400: "Validation Error/FK Not Found", 401: "Unauthorized", 403: "Forbidden", 409: "Conflict (e.g., duplicate email)", 429: "Too Many Requests", 500: "Internal Server Error"}
    )
    @api.expect(student_create_input, validate=True)
    @jwt_required()
    @roles_required('admin') # Only admins can create students directly for now
    @limiter.limit("10/minute")
    def post(self):
        """ Create a new student (Admin only) """
        data = request.get_json()
        return StudentService.create_student(data)


# --- Route for specific student operations ---
@api.route("/<int:student_id>")
@api.param('student_id', 'The unique identifier of the student')
class StudentResource(Resource):

    @api.doc(
        "Get a specific student by ID",
        security="Bearer",
        description="Get data for a specific student. Access restricted to Admins, Teachers, the student themselves, or their parent.",
        responses={200: ("Success", data_resp), 401: "Unauthorized", 403: "Forbidden", 404: "Not Found", 429: "Too Many Requests", 500: "Internal Server Error"}
    )
    @jwt_required()
    @roles_required('admin', 'teacher', 'parent', 'student')
    @limiter.limit("100/minute")
    def get(self, student_id):
        """ Get a specific student's data by ID (with access control) """
        user_id, role, parent_id_for_check = get_current_user_info()
        return StudentService.get_student_data(student_id, user_id, role, parent_id_for_check)

    @api.doc(
        "Update a student",
        security="Bearer",
        description="Update limited fields for a student (Admin only).",
        responses={200: ("Success", data_resp), 400: "Validation Error/FK Not Found/Empty Body", 401: "Unauthorized", 403: "Forbidden", 404: "Not Found", 429: "Too Many Requests", 500: "Internal Server Error"}
    )
    @api.expect(student_update_input, validate=True)
    @jwt_required()
    @roles_required('admin') # Only Admin can use this generic update for now
    @limiter.limit("30/minute")
    def put(self, student_id):
        """ Update an existing student (Admin only) """
        user_id, role, _ = get_current_user_info()
        data = request.get_json()
        # Pass role for authorization check inside service
        return StudentService.update_student(student_id, data, role)

    @api.doc(
        "Delete a student",
        security="Bearer",
        description="Delete a student (Admin only).",
        responses={204: "No Content - Success", 401: "Unauthorized", 403: "Forbidden", 404: "Not Found", 409: "Conflict", 429: "Too Many Requests", 500: "Internal Server Error"}
    )
    @jwt_required()
    @roles_required('admin') # Only Admin can delete
    @limiter.limit("10/minute")
    def delete(self, student_id):
        """ Delete a student (Admin only) """
        user_id, role, _ = get_current_user_info()
        # Pass role for authorization check inside service
        return StudentService.delete_student(student_id, role)


# --- Route specifically for updating approval status ---
@api.route("/<int:student_id>/approval")
@api.param('student_id', 'The unique identifier of the student')
class StudentApproval(Resource):

     @api.doc(
        "Update student approval status",
        security="Bearer",
        description="Set the approval status for a student (Admin only).",
        responses={200: ("Success", data_resp), 400: "Validation Error", 401: "Unauthorized", 403: "Forbidden", 404: "Not Found", 429: "Too Many Requests", 500: "Internal Server Error"}
    )
     @api.expect(student_approval_input, validate=True)
     @jwt_required()
     @roles_required('admin') # Only Admin can approve
     @limiter.limit("20/minute")
     def patch(self, student_id): # Use PATCH for partial update
        """ Update a student's approval status (Admin only) """
        user_id, role, _ = get_current_user_info()
        data = request.get_json()
        return StudentService.update_approval_status(student_id, data, role)


