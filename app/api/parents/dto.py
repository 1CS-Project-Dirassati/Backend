from flask_restx import Namespace, fields
from flask_restx.reqparse import RequestParser


class ParentDto:
    """Data Transfer Objects and Request Parsers for the Parent API."""  # Updated docstring

    # Define the namespace
    api = Namespace("parents", description="Parent/Guardian related operations.")

    # --- Parser for Query Parameters (Admin list view - Filters and Pagination) ---
    parent_filter_parser = RequestParser(bundle_errors=True)
    parent_filter_parser.add_argument(
        "is_email_verified",
        type=bool,
        location="args",
        required=False,
        help="Filter parents by email verification status (true/false).",
    )
    parent_filter_parser.add_argument(
        "is_phone_verified",
        type=bool,
        location="args",
        required=False,
        help="Filter parents by phone verification status (true/false).",
    )
    parent_filter_parser.add_argument(  # Added page
        "page",
        type=int,
        location="args",
        required=False,
        default=1,
        help="Page number for pagination (default: 1).",
    )
    parent_filter_parser.add_argument(  # Added per_page
        "per_page",
        type=int,
        location="args",
        required=False,
        default=10,
        help="Number of items per page (default: 10).",
    )

    # Define the core 'parent' object model (excluding password)
    parent = api.model(
        "Parent Object",
        {
            "id": fields.Integer(readonly=True, description="Parent unique identifier"),
            "first_name": fields.String(
                required=False, description="Parent's first name"
            ),  # Optional
            "last_name": fields.String(
                required=False, description="Parent's last name"
            ),  # Optional
            "email": fields.String(
                required=True, description="Parent's unique email address"
            ),
            "is_email_verified": fields.Boolean(
                readonly=True,
                description="Indicates if the parent's email address is verified",  # Clarified
            ),
            "phone_number": fields.String(
                required=True, description="Parent's phone number"
            ),
            "is_phone_verified": fields.Boolean(
                readonly=True,
                description="Indicates if the parent's phone number is verified",  # Clarified
            ),
            "address": fields.String(
                required=False, description="Parent's address"
            ),  # Optional
            "profile_picture": fields.String(
                required=False,
                description="URL to parent's profile picture",  # Optional
            ),
            "created_at": fields.DateTime(
                readonly=True,
                description="Timestamp of parent record creation (UTC)",  # Added UTC
            ),
            "updated_at": fields.DateTime(
                readonly=True,
                description="Timestamp of last parent record update (UTC)",  # Added UTC
            ),
            # Consider adding student count/ids if needed via service layer enrichment
            # "student_ids": fields.List(fields.Integer, attribute="students.id") # Example
        },
    )

    # Standard response for a single parent
    data_resp = api.model(
        "Parent Data Response",
        {
            "status": fields.Boolean(description="Indicates success or failure"),
            "message": fields.String(description="Response message"),
            "parent": fields.Nested(parent, description="The parent data"),
        },
    )

    # Standard response for a list of parents (includes pagination)
    list_data_resp = api.model(
        "Parent List Response",
        {
            "status": fields.Boolean(description="Indicates success or failure"),
            "message": fields.String(description="Response message"),
            # Updated description
            "parents": fields.List(
                fields.Nested(parent),
                description="List of parent data for the current page",
            ),
            # Pagination metadata fields
            "total": fields.Integer(
                description="Total number of parents matching the query"
            ),
            "pages": fields.Integer(description="Total number of pages"),
            "current_page": fields.Integer(description="The current page number"),
            "per_page": fields.Integer(description="Number of items per page"),
            "has_next": fields.Boolean(description="True if there is a next page"),
            "has_prev": fields.Boolean(description="True if there is a previous page"),
        },
    )

    # --- DTOs for POST/PUT ---
    parent_create_input = api.model(
        "Parent Create Input (Admin)",  # Clarified title
        {
            "email": fields.String(
                required=True, description="Parent's unique email address"
            ),
            "password": fields.String(
                required=True,
                description="Parent's password (min length 8, will be hashed)",
                min_length=8,  # Added min_length
            ),
            "phone_number": fields.String(
                required=True, description="Parent's phone number"
            ),
            "first_name": fields.String(
                required=False, description="Parent's first name"
            ),  # Optional
            "last_name": fields.String(
                required=False, description="Parent's last name"
            ),  # Optional
            "address": fields.String(
                required=False, description="Parent's address"
            ),  # Optional
            "profile_picture": fields.String(
                required=False,
                description="URL to parent's profile picture",  # Optional
            ),
            # Verification statuses are handled post-creation (e.g., via email/SMS workflows)
        },
    )

    # DTO for ADMIN updating a parent
    parent_admin_update_input = api.model(
        "Parent Admin Update Input",
        {
            "first_name": fields.String(
                required=False, description="Parent's first name"
            ),  # Optional
            "last_name": fields.String(
                required=False, description="Parent's last name"
            ),  # Optional
            "phone_number": fields.String(
                required=False, description="Parent's phone number"
            ),  # Optional
            "address": fields.String(
                required=False, description="Parent's address"
            ),  # Optional
            "profile_picture": fields.String(
                required=False,
                description="URL to parent's profile picture",  # Optional
            ),
            # Admin cannot update email, password, or verification status via this endpoint
        },
    )

    # DTO specifically for a PARENT updating their OWN profile
    parent_self_update_input = api.model(
        "Parent Self Update Input",
        {
            "first_name": fields.String(
                required=False, description="Your first name"
            ),  # Optional
            "last_name": fields.String(
                required=False, description="Your last name"
            ),  # Optional
            "phone_number": fields.String(
                required=False,
                description="Your phone number (may require re-verification)",
            ),  # Optional, clarify verification
            "address": fields.String(
                required=False, description="Your address"
            ),  # Optional
            "profile_picture": fields.String(
                required=False, description="URL to your profile picture"
            ),  # Optional
            # Email/password changes should use dedicated endpoints (e.g., /account/email, /account/password)
            # Verification status cannot be updated directly by the parent
        },
    )
