from datetime import datetime
from flask import make_response, current_app, jsonify
from flask_jwt_extended import (
    create_refresh_token,
    create_access_token,
)
import json
from datetime import timezone, timedelta
from werkzeug.security import generate_password_hash, check_password_hash

import random

from app import db
from app.utils import message, err_resp, internal_err_resp
from app.models import Parent, Admin, Teacher, Student
from app.models.Schemas import AdminSchema, ParentSchema, TeacherSchema, StudentSchema
from app.extensions import redis_client

schemas = {
    "parent": ParentSchema(),
    "teacher": TeacherSchema(),
    "student": StudentSchema(),
    "admin": AdminSchema(),
}
models = {
    "parent": Parent,
    "teacher": Teacher,
    "student": Student,
    "admin": Admin,
}


class AuthService:
    @staticmethod
    def login(data):
        # Assign vars
        email = data["email"]
        password = data["password"]
        role = data["role"]
        print(role)
        try:
            # Fetch user data
            if role not in models:
                return err_resp(
                    "Invalid role provided. Please use 'parent', 'teacher', or 'admin'.",
                    "invalid_role",
                    400,
                )
            user = models[role].query.filter_by(email=email).first()
            if not user:
                return err_resp(
                    "The email you have entered does not match any account.",
                    "email_404",
                    404,
                )

            elif user and user.verify_password(password):
                user_info = schemas[role].dump(user)

                access_token = create_access_token(identity=user.id)

                refresh_token = create_refresh_token(identity=str(user.id))
                resp = message(True, "User has been logged in.")
                resp["access_token"] = access_token
                resp["refresh_token"] = refresh_token
                return resp

            return err_resp(
                "Failed to log in, password may be incorrect.", "password_invalid", 401
            )

        except Exception as error:
            current_app.logger.error(error)
            return internal_err_resp()

    @staticmethod
    def register(data):
        # Assign vars

        ## Required values
        email = data["email"]
        password = data["password"]
        role = data["role"]
        phone_number = data["phone_number"]
        first_name = data["first_name"]
        last_name = data["last_name"]

        if role == "admin":
            return err_resp(
                "Admin registration is not allowed.", "admin_registration", 403
            )
        # Check if the email is taken
        if models[role].query.filter_by(email=email).first() is not None:
            return err_resp("Email is already being used.", "email_taken", 403)
        try:

            if redis_client.get(
                f"otp:{email}"
            ):  # Check if OTP already exists for this email
                return err_resp(
                    "An OTP has already been sent to this email. Please check your inbox.",
                    "otp_exists",
                    403,
                )

            otp = random.randint(100000, 999999)
            user_info = {}
            user_info["email"] = email
            user_info["password"] = generate_password_hash(password)
            user_info["phone_number"] = phone_number
            user_info["first_name"] = first_name
            user_info["last_name"] = last_name
            info = [user_info, otp, role]
            # Generate a random OTP
            # Load the new user's info

            redis_client.set(
                f"otp:{email}",
                json.dumps(info),
                ex=300,  # OTP expires in 5 minutes
            )

            resp = message(True, "Otp has been sent to your email.")
            return resp, 201

        except Exception as error:
            current_app.logger.error(error)
            return internal_err_resp()

    @staticmethod
    def verify_otp(data):
        # Assign vars
        email = data["email"]
        otp = data["otp"]

        info = redis_client.getdel(f"otp:{email}")

        if not info:
            return err_resp("OTP has expired or is invalid.", "otp_invalid", 403)
        info = json.loads(info)
        stored_otp = info[1]
        if int(stored_otp) != int(otp):
            return err_resp("Invalid OTP.", "otp_invalid", 403)

        # If valid, create the user in the database
        try:

            print("debug")
            user_info = info[0]
            role = info[2]
            print(user_info)
            new_user = schemas[role].load(user_info)
            print(new_user)
            print(">>>", type(new_user))

            db.session.add(new_user)
            db.session.commit()

            access_token = create_access_token(identity=new_user.id)
            refresh_token = create_refresh_token(identity=str(new_user.id))
            resp = message(True, "User has been registered.")
            resp["access_token"] = access_token
            resp["refresh_token"] = refresh_token
            return resp, 201

        except Exception as error:
            current_app.logger.error(error)
            return internal_err_resp()

    @staticmethod
    def refresh(identity):
        # Create a new access token using the identity from the refresh token
        access_token = create_access_token(identity=identity)
        resp = message(True, "User has been registered.")
        resp["access_token"] = access_token
        resp = jsonify()
        return resp
