# madrassati/auth/errors.py

class AuthError(Exception):
    """Base exception for authentication errors."""
    status_code = 400 # Default status code

class InvalidCredentialsError(AuthError):
    """Raised for invalid login attempts."""
    status_code = 401

class UserAlreadyExistsError(AuthError):
    """Raised when trying to register an existing user."""
    status_code = 409

class InvalidOtpError(AuthError):
    """Raised for invalid or expired OTPs."""
    status_code = 403

class UserNotFoundError(AuthError):
    """Raised when a user lookup fails."""
    status_code = 404

class MissingDataError(AuthError):
    """Raised when required data is missing from the request."""
    status_code = 400
