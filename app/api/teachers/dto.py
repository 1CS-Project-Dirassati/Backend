from flask_restx import Namespace, fields
from flask_restx.reqparse import RequestParser

class TeacherDto:
    # Define the namespace
    api = Namespace("teachers", description="Teacher related operations.")

    # --- Parser for Query Parameters (Admin view) ---
    teacher_filter_parser = RequestParser(bundle_errors=True)
    # Example filter: by module_key (if used for categorization)
    teacher_filter_parser.add_argument(
        'module_key', type=str, location='args', required=False,
        help='Filter teachers by their associated module key (if applicable).'
    )

    # Define the core 'teacher' object model (excluding password)
    teacher = api.model(
        "Teacher Object",
        {
            "id": fields.Integer(readonly=True, description="Teacher unique identifier"),
            "first_name": fields.String(description="Teacher's first name"),
            "last_name": fields.String(description="Teacher's last name"),
            "email": fields.String(required=True, description="Teacher's unique email address"),
            "phone_number": fields.String(required=True, description="Teacher's phone number"),
            "address": fields.String(description="Teacher's address"),
            "profile_picture": fields.String(description="URL to teacher's profile picture"),
            "module_key": fields.String(description="Associated module key, if applicable"),
            "created_at": fields.DateTime(readonly=True, description="Timestamp of creation"),
            "updated_at": fields.DateTime(readonly=True, description="Timestamp of last update"),
            # Could add module names/ids or group counts if needed via service layer
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

    # Standard response for a list of teachers
    list_data_resp = api.model(
        "Teacher List Response",
        {
            "status": fields.Boolean(description="Indicates success or failure"),
            "message": fields.String(description="Response message"),
            "teachers": fields.List(fields.Nested(teacher), description="List of teacher data"),
        }
    )

    # --- DTOs for POST/PUT ---
    teacher_create_input = api.model(
        "Teacher Create Input",
        {
             "email": fields.String(required=True, description="Teacher's unique email address"),
             "password": fields.String(required=True, description="Teacher's password (will be hashed)"),
             "phone_number": fields.String(required=True, description="Teacher's phone number"),
             "first_name": fields.String(description="Teacher's first name"),
             "last_name": fields.String(description="Teacher's last name"),
             "address": fields.String(description="Teacher's address"),
             "profile_picture": fields.String(description="URL to teacher's profile picture"),
             "module_key": fields.String(description="Associated module key, if applicable"),
        }
    )

    # DTO for ADMIN updating a teacher
    teacher_admin_update_input = api.model(
         "Teacher Admin Update Input",
        {
             "first_name": fields.String(description="Teacher's first name"),
             "last_name": fields.String(description="Teacher's last name"),
             "phone_number": fields.String(description="Teacher's phone number"),
             "address": fields.String(description="Teacher's address"),
             "profile_picture": fields.String(description="URL to teacher's profile picture"),
             "module_key": fields.String(description="Associated module key, if applicable"),
             # Excludes email, password
        }
    )

    # DTO for TEACHER updating their OWN profile
    teacher_self_update_input = api.model(
         "Teacher Self Update Input",
        {
             "first_name": fields.String(description="Your first name"),
             "last_name": fields.String(description="Your last name"),
             "phone_number": fields.String(description="Your phone number"),
             "address": fields.String(description="Your address"),
             "profile_picture": fields.String(description="URL to your profile picture"),
             # Excludes email, password, module_key (assuming module_key is admin-managed)
             # Consider adding current_password if password change is allowed here
        }
    )

