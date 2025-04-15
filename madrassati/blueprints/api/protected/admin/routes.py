# protected/admin/routes.py

from flask_restx import Resource, fields, reqparse

# Import namespace, decorator, views from this module
from . import admin_ns, admin_required
from . import views as admin_views

# Define reusable models for request payloads and responses

# --- Generic Models ---
message_model = admin_ns.model("AdminMessageModel", {
    "message": fields.String(description="Success or informational message", required=True)
})

message_id_model = admin_ns.model("AdminMessageIDModel", {
    "id": fields.Integer(description="ID of the created/affected resource", required=True),
    "message": fields.String(description="Success message", required=True)
})

error_model = admin_ns.model("AdminErrorModel", {
    "error": fields.String(description="Error message", required=True)
})

# --- Admin Auth Models ---
admin_login_model = admin_ns.model("AdminLoginPayload", {
    "username": fields.String(required=True, description="Admin username"),
    "password": fields.String(required=True, description="Admin password")
})

admin_token_model = admin_ns.model("AdminTokenResponse", {
    "message": fields.String(required=True, description="Success message"),
    "admin_token": fields.String(required=True, description="Static token for admin access")
})

# --- Parent Models ---
parent_input_model = admin_ns.model("ParentInput", {
    "email": fields.String(required=True, description="Parent's email"),
    "password": fields.String(required=True, description="Parent's password"),
    "phone_number": fields.String(required=True, description="Parent's phone number"),
    "first_name": fields.String(description="Parent's first name"),
    "last_name": fields.String(description="Parent's last name"),
    "address": fields.String(description="Parent's address")
})

parent_brief_model = admin_ns.model("ParentBrief", {
    'id': fields.Integer(readOnly=True, description='Parent ID'),
    'name': fields.String(readOnly=True, description='Parent full name'),
    'email': fields.String(readOnly=True, description='Parent email'),
    'phone': fields.String(attribute='phone_number', description='Parent phone'), # Map attribute
    'children_count': fields.Integer(readOnly=True, description='Number of associated students'),
    'created_at': fields.DateTime(readOnly=True, description='Creation timestamp')
})

# --- Student Models ---
student_input_model = admin_ns.model("StudentInput", {
    "email": fields.String(required=True, description="Student's email"),
    "password": fields.String(required=True, description="Student's password"),
    "level_id": fields.Integer(required=True, description="ID of the student's level"),
    "first_name": fields.String(description="Student's first name"),
    "last_name": fields.String(description="Student's last name"),
    "docs_url": fields.String(description="URL to student documents")
})

student_model = admin_ns.model("Student", {
    'id': fields.Integer(readOnly=True),
    'name': fields.String(readOnly=True),
    'email': fields.String(readOnly=True),
    'level': fields.String(readOnly=True),
    'level_id': fields.Integer(),
    'group': fields.String(readOnly=True, allow_null=True),
    'group_id': fields.Integer(allow_null=True),
    'parent': fields.String(readOnly=True, allow_null=True),
    'is_approved': fields.Boolean(readOnly=True),
    'created_at': fields.DateTime(readOnly=True)
})

# --- Group Models ---
group_input_model = admin_ns.model("GroupInput", {
    "name": fields.String(required=True, description="Name of the group"),
    "level_id": fields.Integer(required=True, description="ID of the level this group belongs to")
})

group_model = admin_ns.model("Group", {
    'id': fields.Integer(readOnly=True),
    'name': fields.String(),
    'level': fields.String(readOnly=True, allow_null=True),
    'level_id': fields.Integer(),
    'students_count': fields.Integer(readOnly=True),
    'teachers': fields.List(fields.String, readOnly=True, description="Names of assigned teachers")
})

student_group_assignment_model = admin_ns.model("StudentGroupAssignment", {
    "student_id": fields.Integer(required=True),
    "group_id": fields.Integer(required=True)
})

# --- Teacher Models ---
teacher_input_model = admin_ns.model("TeacherInput", {
    "email": fields.String(required=True),
    "password": fields.String(required=True),
    "phone_number": fields.String(required=True),
    "first_name": fields.String(),
    "last_name": fields.String(),
    "address": fields.String(),
    "module_key": fields.String(description="Key or identifier for the primary module/subject")
})

teacher_group_model = admin_ns.model("TeacherGroupBrief", {
    'id': fields.Integer(),
    'name': fields.String()
})
teacher_module_model = admin_ns.model("TeacherModuleBrief", {
    'id': fields.Integer(),
    'name': fields.String()
})
teacher_model = admin_ns.model("Teacher", {
    'id': fields.Integer(readOnly=True),
    'name': fields.String(readOnly=True),
    'email': fields.String(),
    'phone': fields.String(attribute='phone_number'),
    'module_key': fields.String(allow_null=True),
    'groups': fields.List(fields.Nested(teacher_group_model), readOnly=True),
    'modules': fields.List(fields.Nested(teacher_module_model), readOnly=True) # Assuming modules relationship exists
})

# --- Session/Schedule Models ---
session_input_model = admin_ns.model("SessionInput", {
    "teacher_id": fields.Integer(required=True),
    "module_id": fields.Integer(required=True),
    "group_id": fields.Integer(required=True),
    "semester_id": fields.Integer(required=True),
    "day_of_week": fields.Integer(required=True, description="0=Monday, 6=Sunday"),
    "time_str": fields.String(required=True, description="HH:MM format (24-hour)"),
    "week_number": fields.Integer(required=True, description="Week number (1-based)")
})

session_model = admin_ns.model("Session", {
    'id': fields.Integer(readOnly=True),
    'teacher': fields.String(readOnly=True, allow_null=True),
    'teacher_id': fields.Integer(),
    'module': fields.String(readOnly=True, allow_null=True),
    'module_id': fields.Integer(),
    'start_time': fields.String(readOnly=True, description="YY-MM-DD-HH:MM format"),
    'week_number': fields.Integer()
})

session_list_response_model = admin_ns.model("SessionListResponse", {
    "sessions": fields.List(fields.Nested(session_model)),
    "current_week": fields.Integer(),
    "total_weeks": fields.Integer(),
    "semester_name": fields.String(),
    "group_name": fields.String()
})

schedule_template_model = admin_ns.model("ScheduleTemplate", {
    "day_of_week": fields.Integer(required=True, description="0=Monday, 6=Sunday"),
    "time_str": fields.String(required=True, description="HH:MM"),
    "teacher_id": fields.Integer(required=True),
    "module_id": fields.Integer(required=True)
})

modify_schedule_input_model = admin_ns.model("ModifyScheduleInput", {
    "semester_id": fields.Integer(required=True),
    "group_id": fields.Integer(required=True),
    "weekly_schedule": fields.List(fields.Nested(schedule_template_model), required=True)
})

modify_schedule_response_model = admin_ns.model("ModifyScheduleResponse", {
    "created_session_ids": fields.List(fields.Integer),
    "message": fields.String()
})

delete_sessions_input_model = admin_ns.model("DeleteSessionsInput", {
    "session_ids": fields.List(fields.Integer, required=True, description="List of session IDs to delete")
})

delete_sessions_response_model = admin_ns.model("DeleteSessionsResponse", {
    "deleted_count": fields.Integer(),
    "message": fields.String()
})


# --- Parsers for Query Parameters ---
parent_list_parser = reqparse.RequestParser()
parent_list_parser.add_argument('status', type=str, help='Filter parents by fee status (paid, unpaid, overdue)', location='args')

student_list_parser = reqparse.RequestParser()
student_list_parser.add_argument('level_id', type=int, help='Filter students by level ID', location='args')
student_list_parser.add_argument('group_id', type=int, help='Filter students by group ID', location='args')
student_list_parser.add_argument('approved', type=bool, help='Filter students by approval status', location='args')

group_list_parser = reqparse.RequestParser()
group_list_parser.add_argument('level_id', type=int, help='Filter groups by level ID', location='args')


# --- Routes ---

@admin_ns.route('/login')
class AdminLogin(Resource):
    @admin_ns.doc('admin_login')
    @admin_ns.expect(admin_login_model, validate=True)
    @admin_ns.response(200, 'Login Successful', admin_token_model)
    @admin_ns.response(401, 'Authentication Failed', error_model)
    def post(self):
        """Admin login with static credentials."""
        data = admin_ns.payload
        # Call view function (which raises AdminAuthError on failure)
        result = admin_views.handle_admin_login(data['username'], data['password'])
        return result, 200 # View function returns data for success

@admin_ns.route('/parents')
class ParentListResource(Resource):
    method_decorators = [admin_required] # Protect methods with admin auth check

    @admin_ns.doc('create_parent')
    @admin_ns.expect(parent_input_model, validate=True)
    @admin_ns.response(201, 'Parent Created', message_id_model)
    @admin_ns.response(400, 'Invalid Input', error_model)
    @admin_ns.response(409, 'Conflict - Parent Already Exists', error_model)
    @admin_ns.response(401, 'Admin Auth Required', error_model)
    def post(self):
        """Create a new parent."""
        result = admin_views.handle_create_parent(admin_ns.payload)
        return result, 201

    @admin_ns.doc('get_parents', parser=parent_list_parser)
    @admin_ns.marshal_list_with(parent_brief_model) # Use marshal_list_with for lists
    @admin_ns.response(400, 'Invalid Filter', error_model)
    @admin_ns.response(401, 'Admin Auth Required', error_model)
    def get(self):
        """Get a list of parents, optionally filtered by fee status."""
        args = parent_list_parser.parse_args()
        status = args.get('status')
        # View function handles logic and returns list or raises error
        parents_list = admin_views.handle_get_parents(status=status)
        return parents_list # Marshalled automatically

@admin_ns.route('/parents/<int:parent_id>')
@admin_ns.param('parent_id', 'The parent identifier')
class ParentResource(Resource):
    method_decorators = [admin_required]

    # @admin_ns.doc('get_parent_details') # GET specific parent details - Controller not provided, placeholder
    # @admin_ns.marshal_with(parent_model) # Need a detailed parent model
    # @admin_ns.response(404, 'Parent Not Found', error_model)
    # def get(self, parent_id):
    #     """Get details for a specific parent."""
    #     # result = admin_views.handle_get_parent_details(parent_id) # Create view/controller needed
    #     # return result
    #     admin_ns.abort(501, "Get parent details not implemented")

    @admin_ns.doc('delete_parent')
    @admin_ns.response(200, 'Parent Deletion Initiated (Placeholder)', message_model)
    @admin_ns.response(404, 'Parent Not Found', error_model)
    @admin_ns.response(401, 'Admin Auth Required', error_model)
    def delete(self, parent_id):
        """Delete a specific parent (Placeholder)."""
        # REMINDER: Implement actual deletion logic and error handling
        result = admin_views.handle_delete_parent(parent_id)
        return result, 200

    @admin_ns.doc('add_child_to_parent')
    @admin_ns.expect(student_input_model, validate=True)
    @admin_ns.response(201, 'Student Added', message_id_model)
    @admin_ns.response(400, 'Invalid Input', error_model)
    @admin_ns.response(404, 'Parent or Level Not Found', error_model)
    @admin_ns.response(401, 'Admin Auth Required', error_model)
    def post(self, parent_id):
        """Add a new student (child) associated with this parent."""
        result = admin_views.handle_add_child(parent_id, admin_ns.payload)
        return result, 201

@admin_ns.route('/students')
class StudentListResource(Resource):
    method_decorators = [admin_required]

    @admin_ns.doc('get_students', parser=student_list_parser)
    @admin_ns.marshal_list_with(student_model)
    @admin_ns.response(400, 'Invalid Filter', error_model)
    @admin_ns.response(401, 'Admin Auth Required', error_model)
    def get(self):
        """Get a list of students, optionally filtered."""
        args = student_list_parser.parse_args()
        students_list = admin_views.handle_get_students(
            level_id=args.get('level_id'),
            group_id=args.get('group_id'),
            approved=args.get('approved')
        )
        return students_list

@admin_ns.route('/groups')
class GroupListResource(Resource):
    method_decorators = [admin_required]

    @admin_ns.doc('create_group')
    @admin_ns.expect(group_input_model, validate=True)
    @admin_ns.response(201, 'Group Created', message_id_model)
    @admin_ns.response(400, 'Invalid Input', error_model)
    @admin_ns.response(404, 'Level Not Found', error_model)
    @admin_ns.response(401, 'Admin Auth Required', error_model)
    def post(self):
        """Create a new group."""
        result = admin_views.handle_add_group(admin_ns.payload)
        return result, 201

    @admin_ns.doc('get_groups', parser=group_list_parser)
    @admin_ns.marshal_list_with(group_model)
    @admin_ns.response(401, 'Admin Auth Required', error_model)
    def get(self):
        """Get a list of groups, optionally filtered by level."""
        args = group_list_parser.parse_args()
        groups_list = admin_views.handle_get_groups(level_id=args.get('level_id'))
        return groups_list

@admin_ns.route('/groups/assign-student')
class AssignStudentGroupResource(Resource):
     method_decorators = [admin_required]
     @admin_ns.doc('assign_student_to_group')
     @admin_ns.expect(student_group_assignment_model, validate=True)
     @admin_ns.response(200, 'Assignment Successful', message_model)
     @admin_ns.response(400, 'Invalid Input/Level Mismatch', error_model)
     @admin_ns.response(404, 'Student or Group Not Found', error_model)
     @admin_ns.response(401, 'Admin Auth Required', error_model)
     def post(self):
          """Assign a student to a group."""
          result = admin_views.handle_assign_student_to_group(admin_ns.payload)
          return result, 200

@admin_ns.route('/groups/remove-student')
class RemoveStudentGroupResource(Resource):
     method_decorators = [admin_required]
     @admin_ns.doc('remove_student_from_group')
     @admin_ns.expect(student_group_assignment_model, validate=True) # Re-use model
     @admin_ns.response(200, 'Removal Successful', message_model)
     @admin_ns.response(404, 'Student Not Found In Group', error_model)
     @admin_ns.response(401, 'Admin Auth Required', error_model)
     def post(self):
          """Remove a student from a group."""
          result = admin_views.handle_remove_student_from_group(admin_ns.payload)
          return result, 200


@admin_ns.route('/teachers')
class TeacherListResource(Resource):
    method_decorators = [admin_required]

    @admin_ns.doc('create_teacher')
    @admin_ns.expect(teacher_input_model, validate=True)
    @admin_ns.response(201, 'Teacher Created', message_id_model)
    @admin_ns.response(400, 'Invalid Input', error_model)
    @admin_ns.response(409, 'Conflict - Teacher Already Exists', error_model)
    @admin_ns.response(401, 'Admin Auth Required', error_model)
    def post(self):
        """Create a new teacher."""
        result = admin_views.handle_add_teacher(admin_ns.payload)
        return result, 201

    @admin_ns.doc('get_teachers')
    @admin_ns.marshal_list_with(teacher_model)
    @admin_ns.response(401, 'Admin Auth Required', error_model)
    def get(self):
        """Get a list of all teachers."""
        teachers_list = admin_views.handle_get_teachers()
        return teachers_list

@admin_ns.route('/sessions')
class SessionListResource(Resource):
    method_decorators = [admin_required]

    @admin_ns.doc('add_session', description="Add a single session for a specific week.")
    @admin_ns.expect(session_input_model, validate=True)
    @admin_ns.response(201, 'Session Created', message_id_model) # Message includes formatted time
    @admin_ns.response(400, 'Invalid Input', error_model)
    @admin_ns.response(404, 'Teacher/Module/Group/Semester Not Found', error_model)
    @admin_ns.response(401, 'Admin Auth Required', error_model)
    def post(self):
        """Add a single session."""
        result = admin_views.handle_add_sessions(admin_ns.payload)
        return result, 201

    # Parser for getting sessions by group/semester
    session_list_parser = reqparse.RequestParser()
    session_list_parser.add_argument('semester_id', type=int, required=True, help='Semester ID', location='args')
    session_list_parser.add_argument('group_id', type=int, required=True, help='Group ID', location='args')

    @admin_ns.doc('get_sessions_for_group_week', parser=session_list_parser, description="Get sessions for the current week for a specific group and semester.")
    @admin_ns.response(200, 'Sessions retrieved', session_list_response_model)
    @admin_ns.response(404, 'Group or Semester Not Found', error_model)
    @admin_ns.response(401, 'Admin Auth Required', error_model)
    def get(self):
        """Get sessions for the current week for a group/semester."""
        args = self.session_list_parser.parse_args()
        result = admin_views.handle_get_sessions(args['semester_id'], args['group_id'])
        return result, 200


@admin_ns.route('/schedule/modify')
class ModifyScheduleResource(Resource):
    method_decorators = [admin_required]
    @admin_ns.doc('modify_schedule', description="Set recurring weekly schedule from current week to semester end, replacing conflicts.")
    @admin_ns.expect(modify_schedule_input_model, validate=True)
    @admin_ns.response(200, 'Schedule Updated', modify_schedule_response_model)
    @admin_ns.response(400, 'Invalid Input', error_model)
    @admin_ns.response(404, 'Group or Semester Not Found', error_model)
    @admin_ns.response(401, 'Admin Auth Required', error_model)
    def post(self):
        """Modify recurring weekly schedule."""
        result = admin_views.handle_modify_schedule(admin_ns.payload)
        return result, 200

@admin_ns.route('/sessions/delete')
class DeleteSessionsResource(Resource):
     method_decorators = [admin_required]
     @admin_ns.doc('delete_sessions', description="Delete multiple sessions by their IDs.")
     @admin_ns.expect(delete_sessions_input_model, validate=True)
     @admin_ns.response(200, 'Sessions Deleted', delete_sessions_response_model)
     @admin_ns.response(400, 'Invalid Input', error_model)
     @admin_ns.response(401, 'Admin Auth Required', error_model)
     def post(self):
          """Delete multiple sessions."""
          result = admin_views.handle_delete_sessions(admin_ns.payload)
          return result, 200
