# todo :
# 1. Update the shell context processor to include the new extensions
import os

from dotenv import load_dotenv
from flask import request, Response

dotenv_path = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)

##

import click
from flask_migrate import Migrate
from app import create_app, db

# Import models
from app.models import *


app = create_app(os.getenv("FLASK_CONFIG") or "default")
config = app.config
USERNAME = config.get("USERNAME")
PASSWORD = config.get("PASSWORD")


def check_auth():
    auth = request.authorization
    return auth and auth.username == USERNAME and auth.password == PASSWORD


@app.before_request
def protect_docs():
    if request.path.startswith("/swagger") or request.path.startswith("/docs"):
        if not check_auth():
            return Response(
                "Could not verify your access to the documentation.\n"
                "You have to login with proper credentials",
                401,
                {"WWW-Authenticate": 'Basic realm="Login Required"'},
            )


migrate = Migrate(app, db)


@app.shell_context_processor
def make_shell_context():
    return dict(db=db, config=config)


@app.cli.command()
@click.argument("test_names", nargs=-1)
def test(test_names):
    """Run unit tests"""
    import unittest

    if test_names:
        """Run specific unit tests.

        Example:
        $ flask test tests.test_auth_api tests.test_user_model ...
        """
        tests = unittest.TestLoader().loadTestsFromNames(test_names)

    else:
        tests = unittest.TestLoader().discover("tests", pattern="test*.py")

    result = unittest.TextTestRunner(verbosity=2).run(tests)
    if result.wasSuccessful():
        return 0

    # Return 1 if tests failed, won't reach here if succeeded.
    return 1
