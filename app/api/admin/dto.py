from flask_restx import Namespace, fields


class AdminDto:

    api = Namespace("admin", description="Admin related operations")
    admin = api.model(
        "Admin object",
        {
            "id": fields.Integer(description="Admin ID"),
            "first_name": fields.String(description="Admin first name"),
            "last_name": fields.String(description="Admin last name"),
            "email": fields.String(required=True, description="Admin email"),
            "phone_number": fields.String(description="Admin phone number"),
            "is_super_admin": fields.Boolean(description="Whether the admin is a super admin"),
            "created_at": fields.DateTime(description="Account creation date"),
            "updated_at": fields.DateTime(description="Last update date"),
        },
    )

    data_resp = api.model(
        "User Data Response",
        {
            "status": fields.Boolean,
            "message": fields.String,
            "user": fields.Nested(admin),
        },
    )
