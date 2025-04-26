from flask_restx import Namespace, fields
from flask_restx.reqparse import RequestParser


class ParentDto:
    # Define the namespace
    api = Namespace("parents", description="Parent/Guardian related operations.")

    # --- Parser for Query Parameters (Admin view) ---
    parent_filter_parser = RequestParser(bundle_errors=True)
    # Add filters Admins might use, e.g., verification status
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

    # Define the core 'parent' object model (excluding password)
    parent = api.model(
        "Parent Object",
        {
            "id": fields.Integer(readonly=True, description="Parent unique identifier"),
            "first_name": fields.String(description="Parent's first name"),
            "last_name": fields.String(description="Parent's last name"),
            "email": fields.String(
                required=True, description="Parent's unique email address"
            ),
            "is_email_verified": fields.Boolean(
                readonly=True, description="Email verification status"
            ),
            "phone_number": fields.String(
                required=True, description="Parent's phone number"
            ),
            "is_phone_verified": fields.Boolean(
                readonly=True, description="Phone verification status"
            ),
            "address": fields.String(description="Parent's address"),
            "profile_picture": fields.String(
                description="URL to parent's profile picture"
            ),
            "created_at": fields.DateTime(
                readonly=True, description="Timestamp of creation"
            ),
            "updated_at": fields.DateTime(
                readonly=True, description="Timestamp of last update"
            ),
            # Consider adding student count/ids if needed via service layer enrichment
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

    # Standard response for a list of parents
    list_data_resp = api.model(
        "Parent List Response",
        {
            "status": fields.Boolean(description="Indicates success or failure"),
            "message": fields.String(description="Response message"),
            "parents": fields.List(
                fields.Nested(parent), description="List of parent data"
            ),
        },
    )

    # --- DTOs for POST/PUT ---
    parent_create_input = api.model(
        "Parent Create Input",
        {
            "email": fields.String(
                required=True, description="Parent's unique email address"
            ),
            # Password input - will be hashed by the service
            "password": fields.String(
                required=True, description="Parent's password (will be hashed)"
            ),
            "phone_number": fields.String(
                required=True, description="Parent's phone number"
            ),
            "first_name": fields.String(description="Parent's first name"),
            "last_name": fields.String(description="Parent's last name"),
            # Address and profile picture can be set on creation or later
            "address": fields.String(description="Parent's address"),
            "profile_picture": fields.String(
                description="URL to parent's profile picture"
            ),
            # Verification statuses are typically handled post-creation
        },
    )

    # DTO for ADMIN updating a parent (limited fields)
    # Excludes password, email, verification statuses
    parent_admin_update_input = api.model(
        "Parent Admin Update Input",
        {
            "first_name": fields.String(description="Parent's first name"),
            "last_name": fields.String(description="Parent's last name"),
            "phone_number": fields.String(description="Parent's phone number"),
            "address": fields.String(description="Parent's address"),
            "profile_picture": fields.String(
                description="URL to parent's profile picture"
            ),
        },
    )

    # DTO specifically for a PARENT updating their OWN profile
    # Similar fields, but used on a different endpoint/context
    parent_self_update_input = api.model(
        "Parent Self Update Input",
        {
            "first_name": fields.String(description="Your first name"),
            "last_name": fields.String(description="Your last name"),
            "phone_number": fields.String(description="Your phone number"),
            "address": fields.String(description="Your address"),
            "profile_picture": fields.String(description="URL to your profile picture"),
            # Consider adding current_password if password change is allowed here
        },
    )
