from flask_restx import Namespace, fields
from flask_restx.reqparse import RequestParser

class StudentDto:
    # Define the namespace
    api = Namespace("students", description="Student related operations.")

    # --- Parser for Query Parameters ---
    student_filter_parser = RequestParser(bundle_errors=True)
    student_filter_parser.add_argument(
        'level_id', type=int, location='args', required=False,
        help='Filter students by the ID of the level they belong to.'
    )
    student_filter_parser.add_argument(
        'group_id', type=int, location='args', required=False,
        help='Filter students by the ID of the group they belong to.'
    )
    student_filter_parser.add_argument(
        'parent_id', type=int, location='args', required=False,
        help='Filter students by the ID of their parent.'
    )
    student_filter_parser.add_argument(
        'is_approved', type=bool, location='args', required=False,
        help='Filter students by their approval status (true/false).'
    )

    # Define the core 'student' object model (excluding password)
    student = api.model(
        "Student Object",
        {
            "id": fields.Integer(readonly=True, description="Student unique identifier"),
            "first_name": fields.String(description="Student's first name"),
            "last_name": fields.String(description="Student's last name"),
            "email": fields.String(required=True, description="Student's unique email address"),
            "level_id": fields.Integer(required=True, description="ID of the student's level"),
            "group_id": fields.Integer(description="ID of the student's group (if assigned)"),
            "is_approved": fields.Boolean(readonly=True, description="Approval status"), # Usually read-only for most users
            "parent_id": fields.Integer(required=True, readonly=True, description="ID of the student's parent"), # Generally read-only after creation
            "docs_url": fields.String(description="URL to student documents"),
            "created_at": fields.DateTime(readonly=True, description="Timestamp of creation"),
            "updated_at": fields.DateTime(readonly=True, description="Timestamp of last update"),
            # Consider adding parent/level/group names if needed via service layer enrichment
            # "level_name": fields.String(attribute="level.name", readonly=True),
        },
    )

    # Standard response for a single student
    data_resp = api.model(
        "Student Data Response",
        {
            "status": fields.Boolean(description="Indicates success or failure"),
            "message": fields.String(description="Response message"),
            "student": fields.Nested(student, description="The student data"),
        },
    )

    # Standard response for a list of students
    list_data_resp = api.model(
        "Student List Response",
        {
            "status": fields.Boolean(description="Indicates success or failure"),
            "message": fields.String(description="Response message"),
            "students": fields.List(fields.Nested(student), description="List of student data"),
        }
    )

    # --- DTOs for POST/PUT ---
    student_create_input = api.model(
        "Student Create Input",
        {
             "email": fields.String(required=True, description="Student's unique email address"),
             # Password input - will be hashed by the service
             "password": fields.String(required=True, description="Student's password (will be hashed)"),
             "level_id": fields.Integer(required=True, description="ID of the student's level"),
             "parent_id": fields.Integer(required=True, description="ID of the student's parent"),
             "first_name": fields.String(description="Student's first name"),
             "last_name": fields.String(description="Student's last name"),
             "docs_url": fields.String(description="URL to student documents"),
             # is_approved is typically handled by admins later, not on initial creation
        }
    )

    # DTO for updating a student (limited fields)
    student_update_input = api.model(
         "Student Update Input",
        {
             "first_name": fields.String(description="Student's first name"),
             "last_name": fields.String(description="Student's last name"),
             "level_id": fields.Integer(description="New ID for the student's level"),
             "group_id": fields.Integer(description="New ID for the student's group"),
             "docs_url": fields.String(description="New URL for student documents"),
             # Email/Password changes should have dedicated endpoints/processes
             # Parent ID is usually not changed via standard update
             # Approval status might be updated via a separate endpoint or admin action
        }
    )

    # DTO specifically for admin updating approval status
    student_approval_input = api.model(
        "Student Approval Input",
        {
            "is_approved": fields.Boolean(required=True, description="Set student approval status")
        }
    )

