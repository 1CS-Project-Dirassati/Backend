from flask_restx import Api
from flask import Blueprint

from .groups import groups_ns
from .notifications.controller import api as notifications_ns
from .levels.controller import api as levels_ns
from .sessions.controller import api as sessions_ns
from .students.controller import api as students_ns
from .parents.controller import api as parents_ns
from .teachers.controller import api as teachers_ns
from .admins.controller import api as admins_ns
from .grades.controller import api as grades_ns
from .payment.controller import api as payments_ns
from .semesters.controller import api as semesters_ns
from .modules.controller import api as modules_ns
from .absences.controller import api as absences_ns
from .salles.controller import api as salles_ns
from .chats.controller import api as chat_ns
from .messages.controller import api as messages_ns


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
api.add_namespace(payments_ns)
api.add_namespace(semesters_ns)
api.add_namespace(modules_ns)
api.add_namespace(absences_ns)
api.add_namespace(salles_ns)
api.add_namespace(notifications_ns)
api.add_namespace(chat_ns)
api.add_namespace(messages_ns)
