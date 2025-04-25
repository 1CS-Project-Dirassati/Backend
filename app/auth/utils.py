# Validations with Marshmallow
from marshmallow import (
    Schema,
    fields,
    validate as marshmallow_validate,
)  # Alias validate
from marshmallow.validate import Regexp, Length


class LoginSchema(Schema):
    """/auth/login [POST]

    Parameters:
    - Email
    - Password (Str)
    """

    email = fields.Email(required=True, validate=[Length(max=64)])
    password = fields.Str(required=True, validate=[Length(min=8, max=128)])
    role = fields.Str(
        required=True,
        validate=[
            Regexp(
                r"^(parent|teacher|admin|student)$",
                error="Role must be one of the following: parent, teacher, admin, or student.",
            )
        ],
    )


class RefreshSchema(Schema):
    """/auth/refresh [POST]

    Parameters:
    - Refresh token (in header)
    """

    # No body parameters needed


class OtpSchema(Schema):
    """/auth/otp [POST]

    Parameters:
    - Email
    - OTP (Str)
    """

    email = fields.Email(required=True, validate=[Length(max=64)])
    otp = fields.Str(required=True, validate=[Length(min=6, max=6)])
    # Removed context field as it wasn't used in the service logic shown
    # If needed, add it back here and in the DTO


class RegisterSchema(Schema):
    """/auth/register [POST]

    Parameters:
    - Email
    - Password (Str)
    - Role (Str)
    - phone_number (Str)
    - first_name (Str)
    - last_name (Str)
    """

    email = fields.Email(required=True, validate=[Length(max=64)])
    password = fields.Str(required=True, validate=[Length(min=8, max=128)])
    role = fields.Str(
        required=True,
        validate=[
            Regexp(
                r"^(parent|teacher|admin|student)$",
                error="Role must be one of the following: parent, teacher, admin, or student.",
            )
        ],
    )
    phone_number = fields.Str(
        required=True,  # Make sure phone number is required if needed
        validate=[
            Regexp(
                r"^\+?[1-9]\d{1,14}$",  # E.164 format validation
                error="Invalid phone number format.",
            )
        ],
    )
    first_name = fields.Str(
        required=True,  # Make sure first name is required
        validate=[
            Regexp(
                r"^[A-Za-z\s'\-.]+$",  # Allow letters, spaces, apostrophes, hyphens, periods
                error="Invalid first name format.",
            ),
            Length(min=1, max=100),
        ],
    )
    last_name = fields.Str(
        required=True,  # Make sure last name is required
        validate=[
            Regexp(
                r"^[A-Za-z\s'\-.]+$",  # Allow letters, spaces, apostrophes, hyphens, periods
                error="Invalid last name format.",
            ),
            Length(min=1, max=100),
        ],
    )


class LogoutSchema(Schema):
    """/auth/logout [DELETE]

    Parameters:
    - Token (in header)
    """

    # No body parameters usually needed if token is from header
    # token = fields.Str(required=True, validate=[Length(min=1)])


class ForgotSchema(Schema):
    """/auth/forgot-password [POST]

    Parameters:
    - Email
    - Role
    """

    email = fields.Email(required=True, validate=[Length(max=64)])
    role = fields.Str(
        required=True,
        validate=[
            Regexp(
                r"^(parent|teacher|admin|student)$",
                error="Role must be one of the following: parent, teacher, admin, or student.",
            )
        ],
    )


# ---- NEW SCHEMA ----
class ResetPasswordSchema(Schema):
    """/auth/reset-password [POST]

    Parameters:
    - token (Str from URL/body)
    - new_password (Str)
    """

    token = fields.Str(required=True, validate=[Length(min=10)])  # Basic length check
    new_password = fields.Str(required=True, validate=[Length(min=8, max=128)])
