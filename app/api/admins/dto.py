from flask_restx import Namespace, fields
from flask_restx.reqparse import RequestParser


class AdminDto:
    """Data Transfer Objects and Request Parsers for the Admin API."""

    api = Namespace(
        "admins",
        description="Administrator user management (Super Admin access often required).",
    )

    admin_filter_parser = RequestParser(bundle_errors=True)
    admin_filter_parser.add_argument(
        "is_super_admin",
        type=bool,  # Keep as bool if your service handles it correctly
        location="args",
        required=False,
        help="Filter admins by their super admin status (true/false).",
    )
    admin_filter_parser.add_argument(  # ADDED archived filter
        "archived",
        type=int,  # As per your spec for other models
        location="args",
        required=False,
        default=0,
        choices=(0, 1),
        help="Filter admins by archived status (1 for archived, 0 for not archived. Default: 0).",
    )
    admin_filter_parser.add_argument(
        "page",
        type=int,
        location="args",
        required=False,
        default=1,
        help="Page number for pagination (default: 1).",
    )
    admin_filter_parser.add_argument(
        "per_page",
        type=int,
        location="args",
        required=False,
        default=10,
        help="Number of items per page (default: 10).",
    )

    admin = api.model(
        "Admin Object",
        {
            "id": fields.Integer(readonly=True, description="Admin unique identifier"),
            "first_name": fields.String(
                required=False, description="Admin's first name"
            ),
            "last_name": fields.String(required=False, description="Admin's last name"),
            "email": fields.String(
                required=True, description="Admin's unique email address"
            ),
            "phone_number": fields.String(
                required=True, description="Admin's phone number"
            ),
            "is_super_admin": fields.Boolean(
                readonly=True,
                description="Indicates if the user has super administrator privileges",
            ),
            "archived": fields.Boolean(  # ADDED archived field to response
                readonly=True, description="Indicates if the admin account is archived"
            ),
            "created_at": fields.DateTime(
                readonly=True, description="Timestamp of admin record creation (UTC)"
            ),
            "updated_at": fields.DateTime(
                readonly=True, description="Timestamp of last admin record update (UTC)"
            ),
        },
    )

    data_resp = api.model(
        "Admin Data Response",
        {
            "status": fields.Boolean(description="Indicates success or failure"),
            "message": fields.String(description="Response message"),
            "admin": fields.Nested(admin, description="The admin data"),
        },
    )

    list_data_resp = api.model(
        "Admin List Response",
        {
            "status": fields.Boolean(description="Indicates success or failure"),
            "message": fields.String(description="Response message"),
            "admins": fields.List(
                fields.Nested(admin),
                description="List of admin data for the current page",
            ),
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

    admin_create_input = api.model(
        "Admin Create Input (Super Admin)",
        {
            "email": fields.String(
                required=True, description="Admin's unique email address"
            ),
            "password": fields.String(
                required=True,
                description="Admin's password (min length 8, will be hashed)",
                min_length=8,
            ),
            "phone_number": fields.String(
                required=True, description="Admin's phone number"
            ),
            "first_name": fields.String(
                required=False, description="Admin's first name"
            ),
            "last_name": fields.String(required=False, description="Admin's last name"),
            "is_super_admin": fields.Boolean(
                required=False,
                description="Set super administrator status (default: false)",
            ),
            # 'archived' defaults to False in model, not set on creation
        },
    )

    admin_super_update_input = api.model(
        "Admin SuperAdmin Update Input",
        {
            "first_name": fields.String(
                required=False, description="Admin's first name"
            ),
            "last_name": fields.String(required=False, description="Admin's last name"),
            "phone_number": fields.String(
                required=False, description="Admin's phone number"
            ),
            "is_super_admin": fields.Boolean(
                required=False, description="Set super administrator status"
            ),
            # 'archived' status is managed by specific archive/unarchive endpoints
        },
    )

    admin_self_update_input = api.model(
        "Admin Self Update Input",
        {
            "first_name": fields.String(required=False, description="Your first name"),
            "last_name": fields.String(required=False, description="Your last name"),
            "phone_number": fields.String(
                required=False, description="Your phone number"
            ),
            # 'archived' status is managed by specific archive/unarchive endpoints
            # 'is_super_admin' cannot be changed by self
        },
    )
