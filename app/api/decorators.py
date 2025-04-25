from functools import wraps
from flask_jwt_extended import get_jwt
from flask import current_app

# Assuming err_resp is importable from your utils module
from app.utils import err_resp

def roles_required(*required_roles):
    """
    Decorator to ensure the JWT identity has one of the specified roles.

    Must be used *after* @jwt_required() so that the JWT payload is available.

    Args:
        *required_roles: One or more role strings (e.g., 'admin', 'teacher').

    Returns:
        Decorator function.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                # Get the full decoded JWT payload
                # This is safe because @jwt_required() runs first
                jwt_payload = get_jwt()

                # Extract the role from the additional claims
                user_role = jwt_payload.get("role")

                if not user_role:
                    # This case should ideally not happen if login logic is correct
                    current_app.logger.warning(
                        f"Role missing from JWT payload for endpoint {func.__name__}. Payload: {jwt_payload}"
                    )
                    return err_resp(
                        "Authorization failed: Role information missing from token.",
                        "role_missing",
                        403  # Forbidden - Authenticated but missing necessary claim
                    )

                # Check if the user's role is in the allowed list for this endpoint
                allowed_roles_set = set(required_roles)
                if user_role not in allowed_roles_set:
                    # User is authenticated but does not have the required role
                    return err_resp(
                        f"Forbidden: Access requires one of the following roles: {list(allowed_roles_set)}",
                        "forbidden_role",
                        403  # Forbidden - Correct status code for authorization failure
                    )

                # If role check passes, execute the original endpoint function
                return func(*args, **kwargs)

            except Exception as e:
                # Catch potential errors during JWT processing, though less likely after @jwt_required
                current_app.logger.error(
                    f"Error during role check decorator for {func.__name__}: {e}",
                    exc_info=True
                )
                # Use your internal error response utility
                from app.utils import internal_err_resp
                return internal_err_resp()

        return wrapper
    return decorator

# Example of a more specific decorator if needed (though roles_required is more flexible)
# def admin_required(func):
#     @wraps(func)
#     @roles_required('admin') # Reuse the general decorator
#     def wrapper(*args, **kwargs):
#         return func(*args, **kwargs)
#     return wrapper

