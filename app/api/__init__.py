from flask_restx import Api
from flask import Blueprint

from .groups.controller import api as groups_ns
from .levels.controller import api as levels_ns
from .sessions.controller import api as sessions_ns
from .students.controller import api as students_ns
from .parents.controller import api as parents_ns
from .teachers.controller import api as teachers_ns
from .admins.controller import api as admins_ns
from .grades.controller import api as grades_ns

# Import controller APIs as namespaces.
api_bp = Blueprint("api", __name__)
authorizations = {"Bearer": {"type": "apiKey", "in": "header", "name": "Authorization"}}


api = Api(
    api_bp,
    title="API",
    description="Main routes.",
    authorizations=authorizations,
)

# API namespaces
api.add_namespace(groups_ns)
api.add_namespace(levels_ns)
api.add_namespace(sessions_ns)
api.add_namespace(students_ns)
api.add_namespace(parents_ns)
api.add_namespace(teachers_ns)
api.add_namespace(admins_ns)
api.add_namespace(grades_ns)
