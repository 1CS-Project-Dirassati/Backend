# protected/admin/errors.py


class AdminError(Exception):
    """Base exception for admin module errors."""

    status_code = 500  # Default to Internal Server Error for admin issues initially
    message = "An error occurred in the admin operation."

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


# --- Specific Admin Errors ---


class AdminAuthError(AdminError):
    """Raised for admin login failures or unauthorized access."""

    status_code = 401
    message = "Admin authentication failed."


class ResourceNotFoundError(AdminError):
    """Raised when a requested resource (Parent, Student, etc.) is not found."""

    status_code = 404
    message = "The requested resource was not found."


class CreationFailedError(AdminError):
    """Raised when creating a resource fails."""

    status_code = 400  # Often bad input, but could be 500 for DB issues
    message = "Failed to create the resource."


class UpdateFailedError(AdminError):
    """Raised when updating a resource fails."""

    status_code = 400  # Often bad input/conflict, could be 500
    message = "Failed to update the resource."


class DeletionFailedError(AdminError):
    """Raised when deleting a resource fails."""

    status_code = 500  # Usually internal error if deletion fails unexpectedly
    message = "Failed to delete the resource."


class AlreadyExistsError(AdminError):
    """Raised when trying to create a resource that already exists (e.g., email conflict)."""

    status_code = 409  # Conflict
    message = "Resource with the provided identifier already exists."


class InvalidInputError(AdminError):
    """Raised for general invalid input data not caught by schema validation."""

    status_code = 400  # Bad Request
    message = "Invalid input data provided."


class OperationFailedError(AdminError):
    """Generic failure for operations like assignment/removal."""

    status_code = 400  # Or 500 depending on cause
    message = "The requested operation failed."
