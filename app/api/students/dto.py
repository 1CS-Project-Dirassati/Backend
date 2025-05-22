from flask_restx import Namespace, fields
from flask_restx.reqparse import RequestParser


class StudentDto:
    """Data Transfer Objects and Request Parsers for the Student API."""

    # Define the namespace
    api = Namespace("students", description="Student related operations.")

    # --- Parser for Query Parameters (Filters and Pagination) ---
    student_filter_parser = RequestParser(bundle_errors=True)
    student_filter_parser.add_argument(
        "level_id",
        type=int,
        location="args",
        required=False,
        help="Filter students by the ID of the level they belong to.",
    )
    student_filter_parser.add_argument(
        "group_id",
        type=int,
        location="args",
        required=False,
        help="Filter students by the ID of the group they belong to.",
    )
    student_filter_parser.add_argument(
        "parent_id",
        type=int,
        location="args",
        required=False,
        help="Filter students by the ID of their parent (Admin/Teacher only).",
    )
    student_filter_parser.add_argument(
        "is_approved",
        type=bool,
        location="args",
        required=False,
        help="Filter students by their approval status (true/false).",
    )
    student_filter_parser.add_argument(
        "page",
        type=int,
        location="args",
        required=False,
        default=1,
        help="Page number for pagination (default: 1).",
    )
    student_filter_parser.add_argument(
        "per_page",
        type=int,
        location="args",
        required=False,
        default=10,
        help="Number of items per page (default: 10).",
    )

    # Define the core 'student' object model (excluding password)
    student = api.model(
        "Student Object",
        {
            "id": fields.Integer(
                readonly=True, description="Student unique identifier"
            ),
            "first_name": fields.String(
                required=False, description="Student's first name"
            ),
            "last_name": fields.String(
                required=False, description="Student's last name"
            ),
            "email": fields.String(
                required=True, description="Student's unique email address"
            ),
            "level_id": fields.Integer(
                required=True, description="ID of the student's current level"
            ),
            "group_id": fields.Integer(
                required=False,
                description="ID of the student's current group (if assigned)",
            ),
            "is_approved": fields.Boolean(
                readonly=True,
                description="Indicates if the student account is approved by admin",
            ),
            "parent_id": fields.Integer(
                required=True, readonly=True, description="ID of the student's parent"
            ),
            "docs_url": fields.String(
                required=False,
                description="URL to student documents (e.g., registration forms)",
            ),
            "created_at": fields.DateTime(
                readonly=True, description="Timestamp of student record creation (UTC)"
            ),
            "updated_at": fields.DateTime(
                readonly=True,
                description="Timestamp of last student record update (UTC)",
            ),
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

    # Generic success message response (can be reused)
    message_resp = api.model(
        "Message Response",
        {
            "status": fields.Boolean(description="Indicates success or failure"),
            "message": fields.String(description="Response message"),
        },
    )

    # Standard response for a list of students (includes pagination)
    list_data_resp = api.model(
        "Student List Response",
        {
            "status": fields.Boolean(description="Indicates success or failure"),
            "message": fields.String(description="Response message"),
            "students": fields.List(
                fields.Nested(student),
                description="List of student data for the current page",
            ),
            "total": fields.Integer(
                description="Total number of students matching the query"
            ),
            "pages": fields.Integer(description="Total number of pages"),
            "current_page": fields.Integer(description="The current page number"),
            "per_page": fields.Integer(description="Number of items per page"),
            "has_next": fields.Boolean(description="True if there is a next page"),
            "has_prev": fields.Boolean(description="True if there is a previous page"),
        },
    )

    # --- DTOs for POST/PUT/PATCH ---
    student_create_input = api.model(
        "Student Create Input (Admin)",  # Clarified Admin role
        {
            "email": fields.String(
                required=True, description="Student's unique email address"
            ),
            "password": fields.String(
                required=True,
                description="Student's password (min length 8, will be hashed)",
                min_length=8,
            ),
            "level_id": fields.Integer(
                required=True, description="ID of the student's level"
            ),
            "parent_id": fields.Integer(
                required=True, description="ID of the student's parent"
            ),
            "first_name": fields.String(
                required=False, description="Student's first name"
            ),
            "last_name": fields.String(
                required=False, description="Student's last name"
            ),
            "docs_url": fields.String(
                required=False, description="URL to student documents, optional"
            ),
        },
    )

    # --- NEW DTO for Parent adding a child ---
    student_add_child_input = api.model(
        "Student Add Child Input (Parent)",
        {
            "first_name": fields.String(
                required=True, description="Child's first name"
            ),
            "last_name": fields.String(required=True, description="Child's last name"),
            "email": fields.String(
                required=True, description="Child's unique email address"
            ),
            "docs_url": fields.String(
                required=False, description="URL to child's documents (optional)"
            ),
        },
    )
    # -----------------------------------------

    # DTO for updating a student (limited fields, Admin only)
    student_update_input = api.model(
        "Student Update Input (Admin)",
        {
            "first_name": fields.String(
                required=False, description="Student's first name"
            ),
            "last_name": fields.String(
                required=False, description="Student's last name"
            ),
            "level_id": fields.Integer(
                required=False, description="New ID for the student's level"
            ),
            "group_id": fields.Integer(
                required=False,
                description="New ID for the student's group (can be null)",
            ),
            "docs_url": fields.String(
                required=False, description="New URL for student documents"
            ),
        },
    )
    student_complete_child_reg_input = api.model(
        "Student Complete Child Registration Input",
        {
            "token": fields.String(required=True, description="The registration token received via email."),
            "password": fields.String(required=True, description="The desired password for the student account (min 8 chars).", min_length=8),
        }
    )
    # -----------------------------------------------


    # DTO specifically for admin updating approval status
    student_approval_input = api.model(
        "Student Approval Input (Admin)",
        {
            "is_approved": fields.Boolean(
                required=True, description="Set student approval status (true or false)"
            )
        },
    )
