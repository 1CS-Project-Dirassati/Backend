import json
import random
from datetime import timedelta

from flask import current_app
from flask_jwt_extended import create_refresh_token, create_access_token
from werkzeug.security import (
    generate_password_hash,
)
from itsdangerous import (
    URLSafeTimedSerializer,
    SignatureExpired,
    BadSignature,
)

from app import db
from app.utils import message, err_resp, internal_err_resp
from app.models import Parent, Admin, Teacher, Student
from app.models.Schemas import AdminSchema, ParentSchema, TeacherSchema, StudentSchema
from app.extensions import (
    redis_client,
    jwt,
)  # Assuming redis is initialized in extensions
from app.service import send_email

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


# --- Placeholder for Email Sending ---
# You'll need to replace this with your actual email sending logic
# using Flask-Mail, SendGrid, Mailgun, etc.
def send_password_reset_email(to_email, reset_link):
    """Sends the password reset link to the user."""
    try:
        # Example using print (replace with real email sending)
        print("---- SENDING PASSWORD RESET EMAIL ----")
        print(f"To: {to_email}")
        print(f"Subject: Reset Your Password")
        print(f"Body: Click the link below to reset your password:\n{reset_link}")
        print("---- END EMAIL ----")
        # --- Integrate your email sending code here ---
        # Example using Flask-Mail (if configured)
        # from flask_mail import Message
        # from app.extensions import mail
        # msg = Message("Reset Your Password",
        #               sender=current_app.config['MAIL_DEFAULT_SENDER'],
        #               recipients=[to_email])
        # msg.body = f"Click the link below to reset your password:\n{reset_link}\n\nIf you did not request this, please ignore this email."
        # mail.send(msg)
        current_app.logger.info(f"Password reset email ostensibly sent to {to_email}")
        return True
    except Exception as e:
        current_app.logger.error(
            f"Failed to send password reset email to {to_email}: {e}", exc_info=True
        )
        return False


# --- End Placeholder ---
@jwt.token_in_blocklist_loader
def check_if_token_is_revoked(jwt_header, jwt_payload: dict):
    jti = jwt_payload["jti"]
    key = f"blocklist:{jti}"
    token_in_redis = redis_client.get(key)
    return token_in_redis is not None


class AuthService:

    @staticmethod
    def _get_serializer():
        """Creates an instance of the timed serializer."""
        if (
            "SECRET_KEY" not in current_app.config
            or not current_app.config["SECRET_KEY"]
        ):
            current_app.logger.critical(
                "SECRET_KEY is not configured. Cannot generate secure tokens."
            )
            raise ValueError("Application is not configured with a SECRET_KEY.")
        # Using a salt makes the signature unique for password resets
        return URLSafeTimedSerializer(
            current_app.config["SECRET_KEY"], salt="password-reset-salt"
        )

    @staticmethod
    def login(data):
        email = data["email"]
        password = data["password"]
        role = data["role"]

        try:
            if role not in models:
                return err_resp("Invalid role provided.", "invalid_role", 400)

            user = models[role].query.filter_by(email=email).first()

            if not user:
                return err_resp("Email does not match any account.", "email_404", 404)

            # Assuming user model has verify_password method using check_password_hash
            if user.verify_password(password):
                user_info = schemas[role].dump(user)
                identity = str(user.id)
                additional_claims = {"role": role}

                access_token = create_access_token(
                    identity=identity,
                    additional_claims=additional_claims,
                    expires_delta=timedelta(
                        seconds=current_app.config["ACCESS_EXPIRES_SECONDS"]
                    ),
                )
                refresh_token = create_refresh_token(
                    identity=identity,
                    additional_claims=additional_claims,
                    expires_delta=timedelta(
                        days=current_app.config["REFRESH_EXPIRES_DAYS"]
                    ),
                )

                resp = message(True, "Login successful.")
                resp["access_token"] = access_token
                resp["refresh_token"] = refresh_token
                resp["user"] = user_info
                return resp, 200  # OK status
            else:
                # Correct status code for wrong password
                return err_resp(
                    "Incorrect email or password.", "login_info_invalid", 401
                )  # Unauthorized

        except Exception as error:
            current_app.logger.error(f"Login exception: {error}", exc_info=True)
            return internal_err_resp()

    @staticmethod
    def logout(token):
        """Revokes a token by adding its JTI to the blocklist (Redis)."""
        try:
            # Assuming Redis is configured as the blocklist in Flask-JWT-Extended setup
            jti = token["jti"]
            ttype = token["type"]
            # The expiry should match the token's original expiry for accurate blocklisting
            # Get expiry from token payload if possible, otherwise use a sensible default like current_app.config["ACCESS_EXPIRES_SECONDS"]
            # For simplicity here, using the access token expiry, but ideally JWT setup handles this
            token_expires = (
                current_app.config["ACCESS_EXPIRES_SECONDS"]
                if ttype == "access"
                else current_app.config["REFRESH_EXPIRES_DAYS"] * 24 * 60 * 60
            )

            redis_client.set(f"blocklist:{jti}", "revoked", ex=token_expires)

            resp = message(True, f"{ttype.capitalize()} token successfully revoked.")
            # Status code 200 OK for successful logout/revocation
            return resp, 200
        except Exception as e:
            current_app.logger.error(f"Logout failed: {e}", exc_info=True)
            # Don't expose internal errors directly
            return err_resp(
                "Logout failed due to an internal issue.", "logout_failed", 500
            )

    @staticmethod
    def forgot_password(data):
        """Handles forgot password request: generates token, sends email."""
        email = data["email"]
        role = data["role"]

        # --- Security: Always return a generic success message ---
        # --- This prevents attackers from enumerating valid emails/roles ---
        generic_success_message = "If an account with that email and role exists, a password reset link has been sent."
        status_code = 200  # OK status

        try:
            if role not in models:
                # Log this issue but still return generic success to user
                current_app.logger.warning(
                    f"Forgot password attempt with invalid role: {role}"
                )
                return message(True, generic_success_message), status_code

            user = models[role].query.filter_by(email=email).first()

            if user:
                # --- User found, generate token and send email ---
                serializer = AuthService._get_serializer()
                # Include user ID and role in the token payload
                token_payload = {"user_id": user.id, "role": role}
                try:
                    token = serializer.dumps(token_payload)
                except Exception as e:
                    current_app.logger.error(
                        f"Failed to serialize password reset token for {email}: {e}",
                        exc_info=True,
                    )
                    # Still return generic success, but log the failure
                    return message(True, generic_success_message), status_code

                # --- Construct Reset Link ---
                frontend_base = current_app.config.get("FRONTEND_BASE_URL")
                if not frontend_base:
                    current_app.logger.error(
                        "FRONTEND_BASE_URL is not configured. Cannot create reset link."
                    )
                    # Still return generic success
                    return message(True, generic_success_message), status_code

                # Adjust the path '/reset-password' if your frontend uses a different route
                reset_link = f"{frontend_base}/reset-password?token={token}"

                # --- Send Email (Using Placeholder) ---
                # --- Send OTP Email ---
                subject = f"Madrassati Reset Password Link - "  # Include OTP in subject for easy finding
                template = (
                    "email/password_reset"  # Prefix for otp_email.html / otp_email.txt
                )
                context = {
                    "reset_link": reset_link,
                    "expiration_minutes": current_app.config[
                        "RESET_LINK_EXPIRATION_MINUTES"
                    ],
                }
                email_sent = send_email(
                    to_email=email,
                    subject=subject,
                    template_prefix=template,
                    context=context,
                )

                email_sent = send_password_reset_email(user.email, reset_link)
                if not email_sent:
                    # Log the failure but still return generic success
                    current_app.logger.error(
                        f"Failed to send password reset email to {email} via configured method."
                    )

            else:
                # --- User not found ---
                # Log this for monitoring if desired, but don't tell the requester
                current_app.logger.info(
                    f"Password reset requested for non-existent user/role: {email}/{role}"
                )

            # Return the generic success message whether user existed or email failed
            return message(True, generic_success_message), status_code

        except ValueError as ve:  # Catch specific config errors like missing SECRET_KEY
            current_app.logger.critical(
                f"Configuration error during forgot password: {ve}"
            )
            return internal_err_resp()  # Return a generic internal error
        except Exception as error:
            current_app.logger.error(
                f"Forgot password exception for {email}: {error}", exc_info=True
            )
            # Even on unexpected errors, return generic success if possible,
            # unless it's a critical config issue caught above.
            # If you want to be safer, return internal_err_resp() here too.
            return message(True, generic_success_message), status_code

    @staticmethod
    def reset_password(data):
        """Handles password reset using the token and new password."""
        token = data["token"]
        new_password = data["new_password"]

        serializer = AuthService._get_serializer()
        max_age = current_app.config["PASSWORD_RESET_TOKEN_MAX_AGE_SECONDS"]

        try:
            # Deserialize and validate the token (checks signature and expiry)
            token_payload = serializer.loads(token, max_age=max_age)
            user_id = token_payload.get("user_id")
            role = token_payload.get("role")

            if not user_id or not role or role not in models:
                # Token payload is invalid or missing required info
                return err_resp(
                    "Invalid or corrupted password reset token.", "token_invalid", 400
                )

            # Fetch the user based on ID and Role from token
            user = models[role].query.get(user_id)

            if not user:
                # User might have been deleted after token was issued
                return err_resp(
                    "User associated with this token not found.", "user_not_found", 404
                )

            # --- Update Password ---
            # Assuming user model has a 'password' attribute or setter
            user.password = generate_password_hash(new_password)
            db.session.add(
                user
            )  # Add user to session if needed (or rely on query.get keeping it in session)
            db.session.commit()

            # --- Optional: Invalidate user's other sessions ---
            # If you have a blocklist, you might want to revoke existing refresh tokens here.
            # This requires storing refresh token JTIs per user or another mechanism.

            resp = message(True, "Password successfully reset.")
            return resp, 200  # OK status

        except SignatureExpired:
            return err_resp("Password reset link has expired.", "token_expired", 400)
        except BadSignature:
            return err_resp("Invalid password reset link.", "token_invalid", 400)
        except ValueError as ve:  # Catch specific config errors like missing SECRET_KEY
            current_app.logger.critical(
                f"Configuration error during reset password: {ve}"
            )
            return internal_err_resp()
        except Exception as error:
            current_app.logger.error(
                f"Reset password exception: {error}", exc_info=True
            )
            return internal_err_resp()

    # --- Existing Methods (Register, Verify OTP, Refresh) ---
    # Ensure they use current_app.config for expiry times etc. as needed
    # and handle errors robustly.

    @staticmethod
    def register(data):
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

        if models[role].query.filter_by(email=email).first() is not None:
            return err_resp(
                "Email is already being used.", "email_taken", 409
            )  # 409 Conflict is suitable

        try:
            # Check if OTP exists in Redis for this email (prevents re-sending within expiry window)
            redis_key = f"otp:register:{email}"  # Use context in key
            if redis_client.exists(redis_key):
                ttl = redis_client.ttl(redis_key)
                return err_resp(
                    f"An OTP has already been sent. Please check your inbox or wait {ttl} seconds.",
                    "otp_exists",
                    429,  # Too Many Requests is appropriate
                )

            otp = random.randint(100000, 999999)
            # Store all necessary info to create the user later
            user_info_to_store = {
                "email": email,
                "password_hash": generate_password_hash(
                    password
                ),  # Store hash directly
                "phone_number": phone_number,
                "first_name": first_name,
                "last_name": last_name,
                # Add any other fields needed from registration DTO
            }
            # Info stored in Redis: [user_data_dict, otp_code, user_role]
            info_for_redis = [user_info_to_store, str(otp), role]  # Store OTP as string

            redis_client.set(
                redis_key,
                json.dumps(info_for_redis),
                ex=current_app.config["OTP_EXPIRATION_SECONDS"],
            )

            # --- Send OTP Email/SMS ---
            # send_registration_otp(email, otp) # Implement this function

            # --- Send OTP Email ---
            otp_code = otp
            subject = f"Madrassati Registration - Your OTP Code ({otp_code})"  # Include OTP in subject for easy finding
            template = "email/otp_email"  # Prefix for otp_email.html / otp_email.txt
            context = {
                "otp_code": otp_code,
                "expiration_minutes": current_app.config["OTP_EXPIRATION_MINUTES"],
            }
            email_sent = send_email(
                to_email=email,
                subject=subject,
                template_prefix=template,
                context=context,
            )

            resp = message(
                True, "OTP has been sent to your email for registration verification."
            )
            return resp, 201  # Created (Implicitly, user creation pending OTP)

        except Exception as error:
            current_app.logger.error(
                f"Registration exception for {email}: {error}", exc_info=True
            )
            return internal_err_resp()

    @staticmethod
    def verify_otp(data):
        email = data["email"]
        otp_provided = data["otp"]
        # Add context if needed: context = data.get("context", "register")
        redis_key = f"otp:register:{email}"  # Key should match registration

        try:
            # Use getdel to atomically retrieve and delete the OTP entry
            otp_entry_json = redis_client.getdel(redis_key)

            if not otp_entry_json:
                return err_resp(
                    "OTP has expired or is invalid.", "otp_invalid_or_expired", 400
                )

            otp_data = json.loads(otp_entry_json)
            user_info_stored = otp_data[0]
            stored_otp = otp_data[1]
            role = otp_data[2]

            if stored_otp != otp_provided:  # Direct string comparison
                # Invalid OTP, potentially re-set the OTP in Redis for retry? Or just fail.
                # For simplicity, fail here. Re-setting might require careful thought.
                return err_resp("Invalid OTP provided.", "otp_invalid", 400)

            # --- OTP is valid, create the user ---
            if role not in models or role not in schemas:
                current_app.logger.error(
                    f"Invalid role '{role}' found in OTP data for {email}"
                )
                return (
                    internal_err_resp()
                )  # Should not happen if register logic is correct

            # Check again if email was taken *between* registration start and OTP verification
            if models[role].query.filter_by(email=email).first() is not None:
                return err_resp(
                    "Email has been registered by another user.",
                    "email_taken_concurrently",
                    409,
                )

            # Create model instance (ensure schema handles 'password_hash')
            # Modify schemas if needed to accept 'password_hash' instead of 'password'
            # Or directly instantiate the model here:
            new_user = models[role](
                email=user_info_stored["email"],
                password=user_info_stored[
                    "password_hash"
                ],  # Use the pre-hashed password
                phone_number=user_info_stored["phone_number"],
                first_name=user_info_stored["first_name"],
                last_name=user_info_stored["last_name"],
                # Add other fields...
            )

            db.session.add(new_user)
            db.session.commit()

            # --- Login the user immediately after verification ---
            identity = {"id": new_user.id, "role": role}
            access_token = create_access_token(
                identity=identity,
                expires_delta=timedelta(
                    seconds=current_app.config["ACCESS_EXPIRES_SECONDS"]
                ),
            )
            refresh_token = create_refresh_token(
                identity=identity,
                expires_delta=timedelta(
                    days=current_app.config["REFRESH_EXPIRES_DAYS"]
                ),
            )

            user_info_response = schemas[role].dump(
                new_user
            )  # Get serializable user data

            resp = message(True, "Account successfully verified and registered.")
            resp["access_token"] = access_token
            resp["refresh_token"] = refresh_token
            resp["user"] = user_info_response
            return resp, 201  # Created

        except json.JSONDecodeError:
            current_app.logger.error(
                f"Failed to decode JSON OTP data from Redis for {email}"
            )
            return err_resp(
                "Failed to verify OTP due to internal state error.",
                "otp_state_error",
                500,
            )
        except Exception as error:
            # Rollback potentially uncommitted changes if DB error occurred before commit
            db.session.rollback()
            current_app.logger.error(
                f"Verify OTP exception for {email}: {error}", exc_info=True
            )
            return internal_err_resp()

    @staticmethod
    def refresh(user_id, role):
        """Refreshes the access token."""
        try:
            # Identity should contain {'id': user_id, 'role': user_role} if set during login/register
            if not user_id or not role:
                current_app.logger.warning(
                    f"Missing user_id or role in refresh token payload."
                )
                return err_resp(
                    "Invalid refresh token.", "token_invalid", 401
                )  # Unauthorized

            # Optional: Check if user still exists and is active
            if role not in models:
                return err_resp(
                    "Invalid role associated with token.", "token_invalid", 401
                )
            user = models[role].query.get(user_id)
            if not user:  # or (hasattr(user, 'is_active') and not user.is_active):
                return err_resp(
                    "User associated with token not found or inactive.",
                    "user_inactive",
                    401,
                )

            identity = str(user.id)
            new_access_token = create_access_token(
                identity=identity,
                additional_claims={"role": role},
                expires_delta=timedelta(
                    seconds=current_app.config["ACCESS_EXPIRES_SECONDS"]
                ),
            )
            resp = message(True, "Access token refreshed successfully.")
            resp["access_token"] = new_access_token
            return resp, 200  # OK
        except Exception as error:
            current_app.logger.error(
                f"Token refresh exception for identity {user_id}: {error}",
                exc_info=True,
            )
            return internal_err_resp()
