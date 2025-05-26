from flask_restx import Namespace, fields
from flask_restx.reqparse import RequestParser


class ParentDto:
    """Data Transfer Objects and Request Parsers for the Parent API."""

    api = Namespace("parents", description="Parent/Guardian related operations.")

    parent_filter_parser = RequestParser(bundle_errors=True)
    parent_filter_parser.add_argument(
        "is_email_verified",
        type=lambda x: x.lower() == 'true' if isinstance(x, str) else bool(x),
        location="args",
        required=False,
        help="Filter parents by email verification status (true/false).",
    )
    parent_filter_parser.add_argument(
        "is_phone_verified",
        type=lambda x: x.lower() == 'true' if isinstance(x, str) else bool(x),
        location="args",
        required=False,
        help="Filter parents by phone verification status (true/false).",
    )
    parent_filter_parser.add_argument(
        "student_id",
        type=int,
        location="args",
        required=False,
        help="Filter parents by their student's ID.",
    )
    parent_filter_parser.add_argument( # ADDED teacher_id filter
        "teacher_id",
        type=int,
        location="args",
        required=False,
        help="Filter parents by the ID of a teacher who teaches their student(s).",
    )
    parent_filter_parser.add_argument(
        "page",
        type=int,
        location="args",
        required=False,
        default=1,
        help="Page number for pagination (default: 1).",
    )
    parent_filter_parser.add_argument(
        "per_page",
        type=int,
        location="args",
        required=False,
        default=10,
        help="Number of items per page (default: 10).",
    )

    parent = api.model(
        "Parent Object",
        {
            "id": fields.Integer(readonly=True, description="Parent unique identifier"),
            "first_name": fields.String(
                required=False, description="Parent's first name"
            ),
            "last_name": fields.String(
                required=False, description="Parent's last name"
            ),
            "email": fields.String(
                required=True, description="Parent's unique email address"
            ),
            "is_email_verified": fields.Boolean(
                readonly=True,
                description="Indicates if the parent's email address is verified",
            ),
            "phone_number": fields.String(
                required=True, description="Parent's phone number"
            ),
            "is_phone_verified": fields.Boolean(
                readonly=True,
                description="Indicates if the parent's phone number is verified",
            ),
            "address": fields.String(
                required=False, description="Parent's address"
            ),
            "profile_picture": fields.String(
                required=False,
                description="URL to parent's profile picture",
            ),
            "created_at": fields.DateTime(
                readonly=True,
                description="Timestamp of parent record creation (UTC)",
            ),
            "updated_at": fields.DateTime(
                readonly=True,
                description="Timestamp of last parent record update (UTC)",
            ),
        },
    )

    data_resp = api.model(
        "Parent Data Response",
        {
            "status": fields.Boolean(description="Indicates success or failure"),
            "message": fields.String(description="Response message"),
            "parent": fields.Nested(parent, description="The parent data"),
        },
    )

    list_data_resp = api.model(
        "Parent List Response",
        {
            "status": fields.Boolean(description="Indicates success or failure"),
            "message": fields.String(description="Response message"),
            "parents": fields.List(
                fields.Nested(parent),
                description="List of parent data for the current page",
            ),
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

    parent_create_input = api.model(
        "Parent Create Input (Admin)",
        {
            "email": fields.String(
                required=True, description="Parent's unique email address"
            ),
            "password": fields.String(
                required=True,
                description="Parent's password (min length 8, will be hashed)",
                min_length=8,
            ),
            "phone_number": fields.String(
                required=True, description="Parent's phone number"
            ),
            "first_name": fields.String(
                required=False, description="Parent's first name"
            ),
            "last_name": fields.String(
                required=False, description="Parent's last name"
            ),
            "address": fields.String(
                required=False, description="Parent's address"
            ),
            "profile_picture": fields.String(
                required=False,
                description="URL to parent's profile picture",
            ),
        },
    )

    parent_admin_update_input = api.model(
        "Parent Admin Update Input",
        {
            "first_name": fields.String(
                required=False, description="Parent's first name"
            ),
            "last_name": fields.String(
                required=False, description="Parent's last name"
            ),
            "phone_number": fields.String(
                required=False, description="Parent's phone number"
            ),
            "address": fields.String(
                required=False, description="Parent's address"
            ),
            "profile_picture": fields.String(
                required=False,
                description="URL to parent's profile picture",
            ),
        },
    )

    parent_self_update_input = api.model(
        "Parent Self Update Input",
        {
            "first_name": fields.String(
                required=False, description="Your first name"
            ),
            "last_name": fields.String(
                required=False, description="Your last name"
            ),
            "phone_number": fields.String(
                required=False,
                description="Your phone number (may require re-verification)",
            ),
            "address": fields.String(
                required=False, description="Your address"
            ),
            "profile_picture": fields.String(
                required=False, description="URL to your profile picture"
            ),
        },
    )
