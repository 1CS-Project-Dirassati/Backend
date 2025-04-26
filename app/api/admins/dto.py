from flask_restx import Namespace, fields
from flask_restx.reqparse import RequestParser


class AdminDto:
    # Define the namespace
    api = Namespace(
        "admins",
        description="Administrator user management (Super Admin access often required).",
    )

    # --- Parser for Query Parameters (Super Admin view) ---
    admin_filter_parser = RequestParser(bundle_errors=True)
    admin_filter_parser.add_argument(
        "is_super_admin",
        type=bool,
        location="args",
        required=False,
        help="Filter admins by their super admin status (true/false).",
    )

    # Define the core 'admin' object model (excluding password)
    admin = api.model(
        "Admin Object",
        {
            "id": fields.Integer(readonly=True, description="Admin unique identifier"),
            "first_name": fields.String(description="Admin's first name"),
            "last_name": fields.String(description="Admin's last name"),
            "email": fields.String(
                required=True, description="Admin's unique email address"
            ),
            "phone_number": fields.String(
                required=True, description="Admin's phone number"
            ),
            "is_super_admin": fields.Boolean(
                readonly=True, description="Super administrator status"
            ),
            "created_at": fields.DateTime(
                readonly=True, description="Timestamp of creation"
            ),
            "updated_at": fields.DateTime(
                readonly=True, description="Timestamp of last update"
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

    # Standard response for a list of admins
    list_data_resp = api.model(
        "Admin List Response",
        {
            "status": fields.Boolean(description="Indicates success or failure"),
            "message": fields.String(description="Response message"),
            "admins": fields.List(
                fields.Nested(admin), description="List of admin data"
            ),
        },
    )

    # --- DTOs for POST/PUT ---
    admin_create_input = api.model(
        "Admin Create Input",
        {
            "email": fields.String(
                required=True, description="Admin's unique email address"
            ),
            "password": fields.String(
                required=True, description="Admin's password (will be hashed)"
            ),
            "phone_number": fields.String(
                required=True, description="Admin's phone number"
            ),
            "first_name": fields.String(description="Admin's first name"),
            "last_name": fields.String(description="Admin's last name"),
            # Super Admin flag can be set on creation by another Super Admin
            "is_super_admin": fields.Boolean(
                description="Set super administrator status (default: false)"
            ),
        },
    )

    # DTO for SUPER ADMIN updating another admin
    admin_super_update_input = api.model(
        "Admin SuperAdmin Update Input",
        {
            "first_name": fields.String(description="Admin's first name"),
            "last_name": fields.String(description="Admin's last name"),
            "phone_number": fields.String(description="Admin's phone number"),
            # Super Admin status can be changed by another Super Admin
            "is_super_admin": fields.Boolean(
                description="Set super administrator status"
            ),
            # Excludes email, password
        },
    )

    # DTO for ADMIN updating their OWN profile
    admin_self_update_input = api.model(
        "Admin Self Update Input",
        {
            "first_name": fields.String(description="Your first name"),
            "last_name": fields.String(description="Your last name"),
            "phone_number": fields.String(description="Your phone number"),
            # Excludes email, password, is_super_admin (cannot change own super admin status)
            # Consider adding current_password if password change is allowed here
        },
    )
