from flask_restx import Namespace, fields
from flask_restx.reqparse import RequestParser


class AdminDto:
    """Data Transfer Objects and Request Parsers for the Admin API."""  # Updated docstring

    # Define the namespace
    api = Namespace(
        "admins",
        description="Administrator user management (Super Admin access often required).",
    )

    # --- Parser for Query Parameters (Super Admin list view - Filters and Pagination) ---
    admin_filter_parser = RequestParser(bundle_errors=True)
    admin_filter_parser.add_argument(
        "is_super_admin",
        type=bool,
        location="args",
        required=False,
        help="Filter admins by their super admin status (true/false).",
    )
    admin_filter_parser.add_argument(  # Added page
        "page",
        type=int,
        location="args",
        required=False,
        default=1,
        help="Page number for pagination (default: 1).",
    )
    admin_filter_parser.add_argument(  # Added per_page
        "per_page",
        type=int,
        location="args",
        required=False,
        default=10,
        help="Number of items per page (default: 10).",
    )

    # Define the core 'admin' object model (excluding password)
    admin = api.model(
        "Admin Object",
        {
            "id": fields.Integer(readonly=True, description="Admin unique identifier"),
            "first_name": fields.String(
                required=False, description="Admin's first name"
            ),  # Optional
            "last_name": fields.String(
                required=False, description="Admin's last name"
            ),  # Optional
            "email": fields.String(
                required=True, description="Admin's unique email address"
            ),
            "phone_number": fields.String(
                required=True, description="Admin's phone number"
            ),
            "is_super_admin": fields.Boolean(
                readonly=True,
                description="Indicates if the user has super administrator privileges",  # Clarified
            ),
            "created_at": fields.DateTime(
                readonly=True,
                description="Timestamp of admin record creation (UTC)",  # Added UTC
            ),
            "updated_at": fields.DateTime(
                readonly=True,
                description="Timestamp of last admin record update (UTC)",  # Added UTC
            ),
        },
    )

    # Standard response for a single admin
    data_resp = api.model(
        "Admin Data Response",
        {
            "status": fields.Boolean(description="Indicates success or failure"),
            "message": fields.String(description="Response message"),
            "admin": fields.Nested(admin, description="The admin data"),
        },
    )

    # Standard response for a list of admins (includes pagination)
    list_data_resp = api.model(
        "Admin List Response",
        {
            "status": fields.Boolean(description="Indicates success or failure"),
            "message": fields.String(description="Response message"),
            # Updated description
            "admins": fields.List(
                fields.Nested(admin),
                description="List of admin data for the current page",
            ),
            # Pagination metadata fields
            "total": fields.Integer(
                description="Total number of admins matching the query"
            ),
            "pages": fields.Integer(description="Total number of pages"),
            "current_page": fields.Integer(description="The current page number"),
            "per_page": fields.Integer(description="Number of items per page"),
            "has_next": fields.Boolean(description="True if there is a next page"),
            "has_prev": fields.Boolean(description="True if there is a previous page"),
        },
    )

    # --- DTOs for POST/PUT ---
    admin_create_input = api.model(
        "Admin Create Input (Super Admin)",  # Clarified title
        {
            "email": fields.String(
                required=True, description="Admin's unique email address"
            ),
            "password": fields.String(
                required=True,
                description="Admin's password (min length 8, will be hashed)",
                min_length=8,  # Added min_length
            ),
            "phone_number": fields.String(
                required=True, description="Admin's phone number"
            ),
            "first_name": fields.String(
                required=False, description="Admin's first name"
            ),  # Optional
            "last_name": fields.String(
                required=False, description="Admin's last name"
            ),  # Optional
            "is_super_admin": fields.Boolean(
                required=False,  # Optional, defaults to False in service if not provided
                description="Set super administrator status (default: false)",
            ),
        },
    )

    # DTO for SUPER ADMIN updating another admin
    admin_super_update_input = api.model(
        "Admin SuperAdmin Update Input",
        {
            "first_name": fields.String(
                required=False, description="Admin's first name"
            ),  # Optional
            "last_name": fields.String(
                required=False, description="Admin's last name"
            ),  # Optional
            "phone_number": fields.String(
                required=False, description="Admin's phone number"
            ),  # Optional
            "is_super_admin": fields.Boolean(
                required=False,  # Optional, only include if changing status
                description="Set super administrator status",
            ),
            # Excludes email, password
        },
    )

    # DTO for ADMIN updating their OWN profile
    admin_self_update_input = api.model(
        "Admin Self Update Input",
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
            # Excludes email, password, is_super_admin
            # Password change should use a dedicated endpoint
        },
    )
