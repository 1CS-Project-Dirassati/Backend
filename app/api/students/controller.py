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
message_resp = StudentDto.message_resp # Added generic message response
student_create_input = StudentDto.student_create_input
student_add_child_input = StudentDto.student_add_child_input # Added DTO for add child
student_update_input = StudentDto.student_update_input
student_approval_input = StudentDto.student_approval_input
student_filter_parser = StudentDto.student_filter_parser
student_complete_child_reg_input = StudentDto.student_complete_child_reg_input




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
        user_id = get_jwt_identity()
        role = get_jwt()['role']
        args = student_filter_parser.parse_args()
        current_app.logger.debug(
            f"Received GET request for students list with args: {args} by User {user_id} ({role})"
        )

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
        "Create a new student (Admin)",
        security="Bearer",
        description="Directly create a new student record (Admin access required).",
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
    @roles_required('admin') # Only Admin can use this direct creation route
    @limiter.limit(lambda: current_app.config.get("RATE_LIMIT_STUDENT_ADMIN_CREATE", "10/minute")) # Different limit name
    def post(self):
        """ Create a new student directly (Admin only) """
        data = request.get_json()
        current_app.logger.debug(
            f"Received POST request by Admin to create student with data: {data}"
        )
        return StudentService.create_student(data)


# --- NEW ROUTE for Parent adding a child ---
@api.route("/add-child")
class StudentAddChild(Resource):

    @api.doc(
        "Add Child (Parent)",
        security="Bearer",
        description="Initiate registration for a child by sending them an email link (Parent access required).",
        responses={
            200: ("Success - Email Sent", message_resp), # Return generic success
            400: "Validation Error",
            401: "Unauthorized",
            403: "Forbidden (Not a Parent)",
            409: "Conflict (Child email already exists)",
            429: "Too Many Requests",
            500: "Internal Server Error (Config issue, Email failure, etc.)"
        }
    )
    @api.expect(student_add_child_input, validate=True)
    @jwt_required()
    @roles_required('parent') # Only Parents can use this route
    @limiter.limit(lambda: current_app.config.get("RATE_LIMIT_STUDENT_ADD_CHILD", "5/hour")) # Limit parent invitations
    def post(self):
        """ Initiate registration for a child (Parent only) """
        parent_id = get_jwt_identity() # Parent's ID from token
        data = request.get_json()
        current_app.logger.info(
            f"Received POST request by Parent {parent_id} to add child with data: {data}"
        )
        # Service handles validation, token generation, email sending
        return StudentService.add_child(data, parent_id)
# -----------------------------------------


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
    @roles_required('admin', 'teacher', 'parent', 'student')
    @limiter.limit(lambda: current_app.config.get("RATE_LIMIT_STUDENT_GET", "100/minute"))
    def get(self, student_id: int):
        """ Get a specific student's data by ID (with record-level access control) """
        user_id = get_jwt_identity()
        role = get_jwt()['role']
        current_app.logger.debug(
            f"Received GET request for student ID: {student_id} by User {user_id} ({role})"
        )
        # Service handles record-level access check
        return StudentService.get_student_data(student_id, user_id, role)

    @api.doc(
        "Update a student (Admin)",
        security="Bearer",
        description="Update limited fields for a student (Admin access required).",
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
    @roles_required('admin') # Only Admin can update via this route
    @limiter.limit(lambda: current_app.config.get("RATE_LIMIT_STUDENT_ADMIN_UPDATE", "30/minute")) # Different limit name
    def put(self, student_id: int):
        """ Update an existing student (Admin only) """
        data = request.get_json()
        current_app.logger.debug(
            f"Received PUT request by Admin for student ID {student_id} with data: {data}"
        )
        return StudentService.update_student(student_id, data)

    @api.doc(
        "Delete a student (Admin)",
        security="Bearer",
        description="Delete a student (Admin access required).",
        responses={
            204: "No Content - Success",
            401: "Unauthorized",
            403: "Forbidden",
            404: "Not Found",
            409: "Conflict (e.g., FK constraints)",
            429: "Too Many Requests",
            500: "Internal Server Error"
        }
    )
    @jwt_required()
    @roles_required('admin') # Only Admin can delete
    @limiter.limit(lambda: current_app.config.get("RATE_LIMIT_STUDENT_ADMIN_DELETE", "10/minute")) # Different limit name
    def delete(self, student_id: int):
        """ Delete a student (Admin only) """
        current_app.logger.warning( # Log deletion attempts as warning
            f"Received DELETE request by Admin for student ID: {student_id}"
        )
        return StudentService.delete_student(student_id)


# --- NEW ROUTE for Completing Child Registration ---
@api.route("/complete-child-registration")
class StudentCompleteChildRegistration(Resource):

    @api.doc(
        "Complete Child Registration",
        description="Complete the student registration using the token from the email and set a password.",
        responses={
            201: ("Created and Logged In"), # Return tokens and user data
            400: "Validation Error / Invalid or Expired Token / Password Too Weak",
            404: "Registration data not found (expired or invalid token link)", # Could argue 400 too
            409: "Conflict (Email registered concurrently)",
            429: "Too Many Requests",
            500: "Internal Server Error"
        }
    )
    @api.expect(student_complete_child_reg_input, validate=True)
    # NO @jwt_required() - Child is not logged in yet
    # NO @roles_required() - Access controlled by token validity
    @limiter.limit(lambda: current_app.config.get("RATE_LIMIT_STUDENT_COMPLETE_REG", "10/minute")) # Limit completion attempts
    def post(self):
        """ Complete child registration using token and set password """
        data = request.get_json()
        current_app.logger.info(
            f"Received POST request to complete child registration for token starting with: {data.get('token', '')[:10]}..."
        )
        # Service handles token validation, Redis lookup, DB creation, token cleanup, login token generation
        return StudentService.complete_child_registration(data)
# --- Route specifically for updating approval status ---
@api.route("/<int:student_id>/approval")
@api.param('student_id', 'The unique identifier of the student')
class StudentApproval(Resource):

     @api.doc(
        "Update student approval status (Admin)",
        security="Bearer",
        description="Set the approval status for a student (Admin access required).",
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
     @roles_required('admin') # Only Admin can approve
     @limiter.limit(lambda: current_app.config.get("RATE_LIMIT_STUDENT_APPROVE", "20/minute"))
     def patch(self, student_id: int):
        """ Update a student's approval status (Admin only) """
        data = request.get_json()
        current_app.logger.debug(
            f"Received PATCH request by Admin for student ID {student_id} approval with data: {data}"
        )
        return StudentService.update_approval_status(student_id, data)

