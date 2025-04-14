# madrassati/auth/errors.py


class AuthError(Exception):
    """Base exception for authentication/authorization errors."""

    status_code = 400  # Default to Bad Request for client-side errors
    message = "An authentication error occurred."

    def __init__(self, message=None, status_code=None):
        super().__init__(message or self.message)
        if status_code is not None:
            self.status_code = status_code
        # Allow message override via constructor
        if message:
            self.message = message

    def to_dict(self):
        """Provides a dictionary representation for JSON responses."""
        return {"error": self.message}


# --- Specific Client-Side Errors (4xx) ---


class InvalidCredentialsError(AuthError):
    """Raised for invalid login attempts (wrong email/password)."""

    status_code = 401
    message = "Invalid email or password."


class UserAlreadyExistsError(AuthError):
    """Raised when trying to register an existing user (email or phone)."""

    status_code = 409
    message = "User with the provided email or phone number already exists."


class InvalidOtpError(AuthError):
    """Raised for invalid or expired OTPs."""

    status_code = 403  # Forbidden - OTP is incorrect/expired
    message = "Invalid or expired OTP."


class UserNotFoundError(AuthError):
    """Raised when a user lookup fails (e.g., for password reset)."""

    status_code = 404
    message = "User not found."


class MissingDataError(AuthError):
    """Raised when required data is missing from the request payload."""

    status_code = 400  # Changed from 405 - Bad Request is more appropriate
    message = "Missing required data in request."


class InvalidRefreshTokenError(AuthError):
    """Raised when the refresh token is invalid (e.g., format, not found, revoked)."""

    status_code = 401  # Changed from 406 - Unauthorized, requires re-login
    message = "Invalid or expired refresh token."


class ExpiredTokenError(AuthError):
    """Raised specifically when a token (access or refresh) has expired."""

    status_code = 401  # Unauthorized, requires refresh or re-login
    message = "Token has expired."


class RevokedTokenError(AuthError):
    """Raised when a token has been explicitly revoked or cannot be found during validation."""

    status_code = 401  # Unauthorized, requires re-login
    message = "Token has been revoked or is invalid."


class TokenFormatError(AuthError):
    """Raised for malformed tokens (e.g., invalid JWT structure)."""

    status_code = 400  # Bad Request - client sent bad data
    message = "Invalid token format."


class TokenSignatureError(AuthError):
    """Raised specifically for JWT signature verification failures."""

    status_code = 401  # Unauthorized - token tampering suspected
    message = "Invalid token signature."


class InvalidFormatError(AuthError):
    """Raised for validation errors on specific field formats (email, phone, etc.)."""

    status_code = 400  # Bad Request - client sent badly formatted data
    # Message should ideally be set specifically when raised, e.g., InvalidFormatError("Invalid email format.")
    message = "Invalid data format provided."


class WeakPasswordError(AuthError):
    """Raised if a password does not meet strength requirements."""

    status_code = 400  # Bad Request - client provided weak password
    message = "Password does not meet complexity requirements."


# --- Specific Server-Side Errors (5xx) ---


class OtpServiceError(AuthError):
    """Raised when communicating with an external OTP service fails."""

    status_code = 503  # Service Unavailable
    message = "Failed to send OTP. Please try again later."


class StorageError(AuthError):
    """Raised for issues communicating with backend storage (DB, Redis) during auth."""

    status_code = 500  # Internal Server Error
    message = "A storage error occurred. Please try again later."


class InternalAuthError(AuthError):
    """Generic catch-all for unexpected server-side errors in authentication logic."""

    status_code = 500  # Internal Server Error
    message = "An internal authentication error occurred. Please try again later."
