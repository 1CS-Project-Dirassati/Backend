from flask_restx import Namespace, fields
from flask_restx.reqparse import RequestParser


class TeacherDto:
    """Data Transfer Objects and Request Parsers for the Teacher API."""

    api = Namespace("teachers", description="Teacher related operations.")

    teacher_filter_parser = RequestParser(bundle_errors=True)
    # Removed specialization_id filter
    teacher_filter_parser.add_argument(
        "module_id",
        type=int,
        location="args",
        required=False,
        help="Filter teachers by module ID they are assigned to.",
    )
    teacher_filter_parser.add_argument(
        "archived",
        type=int,
        location="args",
        required=False,
        default=0,
        choices=(0, 1),
        help="Filter teachers by archived status (1 for archived, 0 for not archived. Default: 0).",
    )
    teacher_filter_parser.add_argument(
        "page",
        type=int,
        location="args",
        required=False,
        default=1,
        help="Page number for pagination (default: 1).",
    )
    teacher_filter_parser.add_argument(
        "per_page",
        type=int,
        location="args",
        required=False,
        default=10,
        help="Number of items per page (default: 10).",
    )

    teacher = api.model(
        "Teacher Object",
        {
            "id": fields.Integer(readonly=True, description="Teacher unique identifier"),
            "first_name": fields.String(required=False, description="Teacher's first name"),
            "last_name": fields.String(required=False, description="Teacher's last name"),
            "email": fields.String(required=True, description="Teacher's unique email address"),
            "phone_number": fields.String(required=True, description="Teacher's phone number"),
            "address": fields.String(required=False, description="Teacher's address"),
            "profile_picture": fields.String(required=False, description="URL to teacher's profile picture"),
            # Removed specialization_id and specialization_name
            "archived": fields.Boolean(readonly=True, description="Indicates if the teacher account is archived"),
            "created_at": fields.DateTime(readonly=True, description="Timestamp of teacher record creation (UTC)"),
            "updated_at": fields.DateTime(readonly=True, description="Timestamp of last teacher record update (UTC)"),
        },
    )

    data_resp = api.model(
        "Teacher Data Response",
        {
            "status": fields.Boolean(description="Indicates success or failure"),
            "message": fields.String(description="Response message"),
            "teacher": fields.Nested(teacher, description="The teacher data"),
        },
    )

    list_data_resp = api.model(
        "Teacher List Response",
        {
            "status": fields.Boolean(description="Indicates success or failure"),
            "message": fields.String(description="Response message"),
            "teachers": fields.List(
                fields.Nested(teacher),
                description="List of teacher data for the current page",
            ),
            "total": fields.Integer(description="Total number of teachers matching the query"),
            "pages": fields.Integer(description="Total number of pages"),
            "current_page": fields.Integer(description="The current page number"),
            "per_page": fields.Integer(description="Number of items per page"),
            "has_next": fields.Boolean(description="True if there is a next page"),
            "has_prev": fields.Boolean(description="True if there is a previous page"),
        },
    )

    teacher_create_input = api.model(
        "Teacher Create Input (Admin)",
        {
            "email": fields.String(required=True, description="Teacher's unique email address"),
            "password": fields.String(required=True, description="Teacher's password (min length 8, will be hashed)", min_length=8),
            "phone_number": fields.String(required=True, description="Teacher's phone number"),
            "first_name": fields.String(required=False, description="Teacher's first name"),
            "last_name": fields.String(required=False, description="Teacher's last name"),
            "address": fields.String(required=False, description="Teacher's address"),
            "profile_picture": fields.String(required=False, description="URL to teacher's profile picture"),
            # Removed specialization_id
        },
    )

    teacher_admin_update_input = api.model(
        "Teacher Admin Update Input",
        {
            "first_name": fields.String(required=False, description="Teacher's first name"),
            "last_name": fields.String(required=False, description="Teacher's last name"),
            "phone_number": fields.String(required=False, description="Teacher's phone number"),
            "address": fields.String(required=False, description="Teacher's address"),
            "profile_picture": fields.String(required=False, description="URL to teacher's profile picture"),
            # Removed specialization_id
        },
    )

    teacher_self_update_input = api.model(
        "Teacher Self Update Input",
        {
            "first_name": fields.String(required=False, description="Your first name"),
            "last_name": fields.String(required=False, description="Your last name"),
            "phone_number": fields.String(required=False, description="Your phone number"),
            "address": fields.String(required=False, description="Your address"),
            "profile_picture": fields.String(required=False, description="URL to your profile picture"),
            # Removed specialization_id
        },
    )
