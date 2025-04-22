from datetime import datetime
from flask import make_response, current_app, jsonify
from flask_jwt_extended import (
    create_refresh_token,
    create_access_token,
    get_jwt_identity,
    get_jwt,
    set_access_cookies,
)
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
                print("debug pointer2")
                user_info = schemas[role].dump(user)

                access_token = create_access_token(identity=user.id)
                refresh_token = create_refresh_token(identity=str(user.id))
                resp = make_response(
                    jsonify(
                        {
                            "message": "Successfully logged in.",
                            "access_token": access_token,
                            "refresh_token": refresh_token,
                            "user": user_info,
                        }
                    ),
                    200,
                )
                resp.set_cookie(
                    "refresh_token",
                    refresh_token,
                    httponly=False,
                    secure=True,
                    samesite="None",
                    max_age=timedelta(days=30),
                )

                return resp

            return err_resp(
                "Failed to log in, password may be incorrect.", "password_invalid", 401
            )

        except Exception as error:
            current_app.logger.error(error)
            return internal_err_resp()

    @staticmethod
    def refresh():
        identity = get_jwt_identity()
        print(identity)

    @staticmethod
    def register(data):
        # Assign vars

        ## Required values
        email = data["email"]
        password = data["password"]
        role = data["role"]
        data_name = data["name"]
        phone_number = data["phone_number"]
        username = data["username"]

        print("debug pointer")
        # Check if the email is taken
        if models[role].query.filter_by(email=email).first() is not None:
            return err_resp("Email is already being used.", "email_taken", 403)
        try:
            print("debug pointer1")
            # new_user = models[role](
            #    email=email,
            #    first_name=data_name,
            #    password_hash=password,
            #    last_name=data_name,
            #    phone_number=phone_number,
            # )
            new_user = Parent(
                email=email,
                first_name=data_name,
                password_hash=generate_password_hash(password),
                last_name=data_name,
                phone_number=phone_number,
            )
            print("debug pointer2")

            # Generate a random OTP
            otp = random.randint(100000, 999999)
            # Load the new user's info
            user_info = schemas[role].dump(new_user)
            # redis_client.set(
            #    f"otp:{user_info['email']}",
            #    otp,
            #    user_info,
            #    ex=300,  # OTP expires in 5 minutes
            # )
            db.session.add(new_user)
            # Commit changes to DB
            db.session.commit()

            # Create an access token
            access_token = create_access_token(identity=new_user.id)

            resp = message(True, "User has been registered.")
            resp["access_token"] = access_token
            resp["user"] = user_info

            return resp, 201

        except Exception as error:
            current_app.logger.error(error)
            return internal_err_resp()
