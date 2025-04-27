from flask_restx import Namespace, fields
from flask_restx.reqparse import RequestParser


class TeacherDto:
    """Data Transfer Objects and Request Parsers for the Teacher API."""  # Updated docstring

    # Define the namespace
    api = Namespace("teachers", description="Teacher related operations.")

    # --- Parser for Query Parameters (Admin list view - Filters and Pagination) ---
    teacher_filter_parser = RequestParser(bundle_errors=True)
    teacher_filter_parser.add_argument(
        "module_key",
        type=str,
        location="args",
        required=False,
        help="Filter teachers by their associated module key (case-insensitive partial match).",  # Updated help
    )
    teacher_filter_parser.add_argument(  # Added page
        "page",
        type=int,
        location="args",
        required=False,
        default=1,
        help="Page number for pagination (default: 1).",
    )
    teacher_filter_parser.add_argument(  # Added per_page
        "per_page",
        type=int,
        location="args",
        required=False,
        default=10,
        help="Number of items per page (default: 10).",
    )

    # Define the core 'teacher' object model (excluding password)
    teacher = api.model(
        "Teacher Object",
        {
            "id": fields.Integer(
                readonly=True, description="Teacher unique identifier"
            ),
            "first_name": fields.String(
                required=False, description="Teacher's first name"
            ),  # Optional
            "last_name": fields.String(
                required=False, description="Teacher's last name"
            ),  # Optional
            "email": fields.String(
                required=True, description="Teacher's unique email address"
            ),
            "phone_number": fields.String(
                required=True, description="Teacher's phone number"
            ),
            "address": fields.String(
                required=False, description="Teacher's address"
            ),  # Optional
            "profile_picture": fields.String(
                required=False, description="URL to teacher's profile picture"
            ),  # Optional
            "module_key": fields.String(
                required=False,
                description="Associated module key, if applicable (Admin managed)",
            ),  # Optional, clarify admin managed
            "created_at": fields.DateTime(
                readonly=True, description="Timestamp of teacher record creation (UTC)"
            ),  # Added UTC
            "updated_at": fields.DateTime(
                readonly=True,
                description="Timestamp of last teacher record update (UTC)",
            ),  # Added UTC
            # Could add module names/ids or session counts if needed via service layer enrichment
        },
    )

    # Standard response for a single teacher
    data_resp = api.model(
        "Teacher Data Response",
        {
            "status": fields.Boolean(description="Indicates success or failure"),
            "message": fields.String(description="Response message"),
            "teacher": fields.Nested(teacher, description="The teacher data"),
        },
    )

    # Standard response for a list of teachers (includes pagination)
    list_data_resp = api.model(
        "Teacher List Response",
        {
            "status": fields.Boolean(description="Indicates success or failure"),
            "message": fields.String(description="Response message"),
            # Updated description
            "teachers": fields.List(
                fields.Nested(teacher),
                description="List of teacher data for the current page",
            ),
            # Pagination metadata fields
            "total": fields.Integer(
                description="Total number of teachers matching the query"
            ),
            "pages": fields.Integer(description="Total number of pages"),
            "current_page": fields.Integer(description="The current page number"),
            "per_page": fields.Integer(description="Number of items per page"),
            "has_next": fields.Boolean(description="True if there is a next page"),
            "has_prev": fields.Boolean(description="True if there is a previous page"),
        },
    )

    # --- DTOs for POST/PUT ---
    teacher_create_input = api.model(
        "Teacher Create Input (Admin)",  # Clarified title
        {
            "email": fields.String(
                required=True, description="Teacher's unique email address"
            ),
            "password": fields.String(
                required=True,
                description="Teacher's password (min length 8, will be hashed)",
                min_length=8,
            ),  # Added min_length
            "phone_number": fields.String(
                required=True, description="Teacher's phone number"
            ),
            "first_name": fields.String(
                required=False, description="Teacher's first name"
            ),  # Optional
            "last_name": fields.String(
                required=False, description="Teacher's last name"
            ),  # Optional
            "address": fields.String(
                required=False, description="Teacher's address"
            ),  # Optional
            "profile_picture": fields.String(
                required=False, description="URL to teacher's profile picture"
            ),  # Optional
            "module_key": fields.String(
                required=False, description="Associated module key, optional"
            ),  # Optional
        },
    )

    # DTO for ADMIN updating a teacher
    teacher_admin_update_input = api.model(
        "Teacher Admin Update Input",
        {
            "first_name": fields.String(
                required=False, description="Teacher's first name"
            ),  # Optional
            "last_name": fields.String(
                required=False, description="Teacher's last name"
            ),  # Optional
            "phone_number": fields.String(
                required=False, description="Teacher's phone number"
            ),  # Optional
            "address": fields.String(
                required=False, description="Teacher's address"
            ),  # Optional
            "profile_picture": fields.String(
                required=False, description="URL to teacher's profile picture"
            ),  # Optional
            "module_key": fields.String(
                required=False, description="Associated module key, optional"
            ),  # Optional
            # Excludes email, password
        },
    )

    # DTO for TEACHER updating their OWN profile
    teacher_self_update_input = api.model(
        "Teacher Self Update Input",
        {
            "first_name": fields.String(
                required=False, description="Your first name"
            ),  # Optional
            "last_name": fields.String(
                required=False, description="Your last name"
            ),  # Optional
            "phone_number": fields.String(
                required=False, description="Your phone number"
            ),  # Optional
            "address": fields.String(
                required=False, description="Your address"
            ),  # Optional
            "profile_picture": fields.String(
                required=False, description="URL to your profile picture"
            ),  # Optional
            # Excludes email, password, module_key
            # Password change should use a dedicated endpoint
        },
    )
