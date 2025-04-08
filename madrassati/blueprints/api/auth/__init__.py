# madrassati/auth/__init__.py
from flask_restx import Namespace

# Create the blueprint
# It's good practice to add a url_prefix to namespace your auth routes
auth_ns = Namespace(
    "auth",
    description="Authentication related routes",
    url_prefix='/auth' # All routes in this blueprint will be under /auth/login, /auth/register etc.
)

# Import routes to register the routes and error handlers defined within routes.py
from . import routes  # noqa: F401, E402

# You might also import errors if you want the custom exceptions easily accessible
# via `from madrassati.auth import InvalidCredentialsError`, etc., but it's not
# strictly required just for registering the routes/handlers.
# from . import errors # noqa: F401, E402

# The original import 'from . import views' is removed because routes.py
# now handles importing view functions and registering the routes.
