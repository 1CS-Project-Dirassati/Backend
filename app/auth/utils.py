# Validations with Marshmallow
from marshmallow import Schema, fields
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
    - Refresh token
    """


class OtpSchema(Schema):
    """/auth/otp [POST]

    Parameters:
    - Email
    - OTP (Str)
    """

    email = fields.Email(required=True, validate=[Length(max=64)])
    otp = fields.Str(required=True, validate=[Length(min=6, max=6)])


class RegisterSchema(Schema):
    """/auth/register [POST]

    Parameters:
    - Email
    - Username (Str)
    - Name (Str)
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
    phone_number = fields.Str(
        validate=[
            Regexp(
                r"^\+?[1-9]\d{1,14}$",
                error="Invalid phone number format.",
            )
        ]
    )
    first_name = fields.Str(
        validate=[
            Regexp(
                r"^[A-Za-z]+((\s)?((\'|\-|\.)?([A-Za-z])+))*$",
                error="Invalid first name!",
            )
        ]
    )
    last_name = fields.Str(
        validate=[
            Regexp(
                r"^[A-Za-z]+((\s)?((\'|\-|\.)?([A-Za-z])+))*$",
                error="invalid last name",
            )
        ]
    )
