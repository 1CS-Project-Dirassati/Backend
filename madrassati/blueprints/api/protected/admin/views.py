# protected/admin/views.py
import logging
from flask import current_app

import madrassati

# Import custom errors for this module
from .errors import (
    AdminError,
    AdminAuthError,
    ResourceNotFoundError,
    CreationFailedError,
    UpdateFailedError,
    DeletionFailedError,
    AlreadyExistsError,
    InvalidInputError,
    OperationFailedError,
)
from madrassati.blueprints.api.auth.errors import InternalAuthError

# Import controller functions (adjust path if controllers.py is elsewhere)
# It's often better to have controllers in a dedicated top-level folder
# Assuming controllers.py is one level up: from ..controllers import ...
# Or if it's structured like madrassati/controllers/admin_controllers.py:
# from madrassati.controllers import admin_controllers as ctrl
from madrassati import (
    controllers as ctrl,
)  # Assuming controllers.py is in the same directory for now

logger = logging.getLogger(__name__)


# --- Admin Auth ---
def handle_admin_login(username, password):
    """
    Handles the simple static admin login.
    In a real app, verify against a secure source.
    """
    # VERY basic check - Replace with secure check (e.g., DB lookup, env vars)
    ADMIN_USER = current_app.config.get("ADMIN_USERNAME", "admin")
    ADMIN_PASS = current_app.config.get(
        "ADMIN_PASSWORD", "password"
    )  # !! CHANGE THIS !!

    if username == ADMIN_USER and password == ADMIN_PASS:
        # Return the static token defined in __init__.py
        from . import ADMIN_STATIC_TOKEN

        return {"message": "Admin login successful", "admin_token": ADMIN_STATIC_TOKEN}
    else:
        raise AdminAuthError("Invalid admin credentials.")


# --- Parent Views ---
def handle_create_parent(data):
    """Handles parent creation, calling controller and mapping errors."""
    try:
        # Extract required fields (add optional ones as needed)
        email = data["email"]
        password = data["password"]
        phone_number = data["phone_number"]
        first_name = data.get("first_name")
        last_name = data.get("last_name")
        address = data.get("address")

        parent_id, message = ctrl.create_parent(
            email=email,
            password=password,
            phone_number=phone_number,
            first_name=first_name,
            last_name=last_name,
            address=address,
        )

        if parent_id is None:
            # Analyze message to raise specific error
            if "already exists" in message:
                raise AlreadyExistsError(message)
            else:
                logger.error(f"Parent creation failed: {message}")
                raise CreationFailedError(
                    "Failed to create parent due to an internal error."
                )
        else:
            return {"id": parent_id, "message": message}

    except KeyError as e:
        raise InvalidInputError(f"Missing required field: {e}")
    except Exception as e:
        logger.error(f"Unexpected error in handle_create_parent: {e}", exc_info=True)
        raise AdminError("An unexpected error occurred while creating the parent.")


def handle_get_parents(status=None):
    """Handles retrieving parents, calling controller and mapping errors."""
    try:
        if status:
            parents, message = ctrl.get_parents_by_paid(status=status)
        else:
            parents, message = ctrl.get_parents()

        if parents is None:
            # Controller failed
            logger.error(f"Failed to get parents: {message}")
            if "Invalid status parameter" in message:
                raise InvalidInputError(message)
            else:
                raise AdminError(
                    "Failed to retrieve parents due to an internal error."
                )  # Generic 500
        else:
            # Success, return the list directly (marshalling handled by routes)
            return parents

    except Exception as e:
        logger.error(f"Unexpected error in handle_get_parents: {e}", exc_info=True)
        raise AdminError("An unexpected error occurred while retrieving parents.")


# Placeholder for delete parent
def handle_delete_parent(parent_id):
    """Placeholder for deleting a parent."""
    # TODO: Implement parent deletion logic in controllers.py and here.
    # Consider implications: deleting associated students, fees, etc.?
    # Or maybe just mark as inactive?
    logger.warning(f"Placeholder: Attempted to delete parent ID: {parent_id}")
    # For now, return success to avoid breaking flow, but indicate action needed
    # ctrl_result, ctrl_message = ctrl.delete_parent(parent_id) # Call controller when ready
    # if not ctrl_result: raise DeletionFailedError(ctrl_message)
    return {"message": f"Parent {parent_id} deletion placeholder - Implement logic!"}


# --- Student Views ---
def handle_add_child(parent_id, data):
    """Handles adding a child (student) to a parent."""
    try:
        student_id, message = ctrl.add_child(
            parent_id=parent_id,
            email=data["email"],
            password=data["password"],
            level_id=data["level_id"],
            first_name=data.get("first_name"),
            last_name=data.get("last_name"),
            docs_url=data.get("docs_url"),
        )
        if student_id is None:
            if "not found" in message:
                raise ResourceNotFoundError(message)
            else:
                logger.error(f"Failed to add child for parent {parent_id}: {message}")
                raise CreationFailedError(
                    "Failed to add student due to an internal error."
                )
        else:
            return {"id": student_id, "message": message}
    except KeyError as e:
        raise InvalidInputError(f"Missing required field: {e}")
    except Exception as e:
        logger.error(f"Unexpected error in handle_add_child: {e}", exc_info=True)
        raise AdminError("An unexpected error occurred while adding the student.")


def handle_get_students(level_id=None, group_id=None, approved=None):
    """Handles retrieving students with optional filters."""
    try:
        filter_type = None
        filter_value = None
        if level_id is not None:
            filter_type = "level"
            filter_value = level_id
        elif group_id is not None:
            filter_type = "group"
            filter_value = group_id
        elif approved is not None:
            filter_type = "approved"
            filter_value = approved

        students, message = ctrl.get_students(
            filter_type=filter_type, filter_value=filter_value
        )

        if students is None:
            logger.error(f"Failed to get students: {message}")
            if "Invalid filter type" in message:
                raise InvalidInputError(message)
            else:
                raise AdminError(
                    "Failed to retrieve students due to an internal error."
                )
        else:
            return students
    except Exception as e:
        logger.error(f"Unexpected error in handle_get_students: {e}", exc_info=True)
        raise AdminError("An unexpected error occurred while retrieving students.")


# --- Group Views ---
def handle_add_group(data):
    """Handles adding a new group."""
    try:
        group_id, message = ctrl.add_group(name=data["name"], level_id=data["level_id"])
        if group_id is None:
            if "not found" in message:
                raise ResourceNotFoundError(message)  # Level not found
            else:
                logger.error(f"Failed to add group: {message}")
                raise CreationFailedError(
                    "Failed to add group due to an internal error."
                )
        else:
            return {"id": group_id, "message": message}
    except KeyError as e:
        raise InvalidInputError(f"Missing required field: {e}")
    except Exception as e:
        logger.error(f"Unexpected error in handle_add_group: {e}", exc_info=True)
        raise AdminError("An unexpected error occurred while adding the group.")


def handle_get_groups(level_id=None):
    """Handles retrieving groups, optionally filtered by level."""
    try:
        groups, message = ctrl.get_groups(level_id=level_id)
        if groups is None:
            logger.error(f"Failed to get groups: {message}")
            raise AdminError("Failed to retrieve groups due to an internal error.")
        else:
            return groups
    except Exception as e:
        logger.error(f"Unexpected error in handle_get_groups: {e}", exc_info=True)
        raise AdminError("An unexpected error occurred while retrieving groups.")


def handle_assign_student_to_group(data):
    """Handles assigning a student to a group."""
    try:
        success, message = ctrl.assign_student_to_group(
            student_id=data["student_id"], group_id=data["group_id"]
        )
        if not success:
            if "not found" in message:
                raise ResourceNotFoundError(message)
            elif "level doesn't match" in message:
                raise InvalidInputError(message)
            else:
                logger.error(f"Failed to assign student to group: {message}")
                raise OperationFailedError(
                    "Failed to assign student due to an internal error."
                )
        else:
            return {"message": message}
    except KeyError as e:
        raise InvalidInputError(f"Missing required field: {e}")
    except Exception as e:
        logger.error(
            f"Unexpected error in handle_assign_student_to_group: {e}", exc_info=True
        )
        raise AdminError("An unexpected error occurred while assigning the student.")


def handle_remove_student_from_group(data):
    """Handles removing a student from a group."""
    try:
        success, message = ctrl.remove_student_from_group(
            student_id=data["student_id"],
            group_id=data["group_id"],  # Controller requires group_id for confirmation
        )
        if not success:
            if "not found" in message:
                raise ResourceNotFoundError(message)
            else:
                logger.error(f"Failed to remove student from group: {message}")
                raise OperationFailedError(
                    "Failed to remove student due to an internal error."
                )
        else:
            return {"message": message}
    except KeyError as e:
        raise InvalidInputError(f"Missing required field: {e}")
    except Exception as e:
        logger.error(
            f"Unexpected error in handle_remove_student_from_group: {e}", exc_info=True
        )
        raise AdminError("An unexpected error occurred while removing the student.")


# --- Teacher Views ---
def handle_add_teacher(data):
    """Handles adding a new teacher."""
    try:
        teacher_id, message = ctrl.add_teacher(
            email=data["email"],
            password=data["password"],
            phone_number=data["phone_number"],
            first_name=data.get("first_name"),
            last_name=data.get("last_name"),
            address=data.get("address"),
            module_key=data.get("module_key"),
        )
        if teacher_id is None:
            if "already exists" in message:
                raise AlreadyExistsError(message)
            else:
                logger.error(f"Failed to add teacher: {message}")
                raise CreationFailedError(
                    "Failed to add teacher due to an internal error."
                )
        else:
            return {"id": teacher_id, "message": message}
    except KeyError as e:
        raise InvalidInputError(f"Missing required field: {e}")
    except Exception as e:
        logger.error(f"Unexpected error in handle_add_teacher: {e}", exc_info=True)
        raise AdminError("An unexpected error occurred while adding the teacher.")


def handle_get_teachers():
    """Handles retrieving all teachers."""
    try:
        teachers, message = ctrl.get_teachers()
        if teachers is None:
            logger.error(f"Failed to get teachers: {message}")
            raise AdminError("Failed to retrieve teachers due to an internal error.")
        else:
            return teachers
    except Exception as e:
        logger.error(f"Unexpected error in handle_get_teachers: {e}", exc_info=True)
        raise AdminError("An unexpected error occurred while retrieving teachers.")


# --- Session/Schedule Views ---
def handle_add_sessions(data):
    """Handles adding a single session."""
    try:
        session_id, message = ctrl.add_sessions(
            teacher_id=data["teacher_id"],
            module_id=data["module_id"],
            group_id=data["group_id"],
            semester_id=data["semester_id"],
            day_of_week=data["day_of_week"],
            time_str=data["time_str"],
            week_number=data["week_number"],
        )
        if session_id is None:
            if "not found" in message:
                raise ResourceNotFoundError(message)
            else:
                logger.error(f"Failed to add session: {message}")
                raise CreationFailedError(
                    "Failed to add session due to an internal error."
                )
        else:
            return {"id": session_id, "message": message}
    except KeyError as e:
        raise InvalidInputError(f"Missing required field: {e}")
    except Exception as e:
        logger.error(f"Unexpected error in handle_add_sessions: {e}", exc_info=True)
        raise AdminError("An unexpected error occurred while adding the session.")


def handle_modify_schedule(data):
    """Handles modifying the recurring schedule for a group/semester."""
    try:
        session_ids, message = ctrl.modify_schedule(
            semester_id=data["semester_id"],
            group_id=data["group_id"],
            weekly_schedule=data["weekly_schedule"],  # Expects list of dicts
        )
        if session_ids is None:
            if "not found" in message:
                raise ResourceNotFoundError(message)
            else:
                logger.error(f"Failed to modify schedule: {message}")
                raise OperationFailedError(
                    "Failed to modify schedule due to an internal error."
                )
        else:
            return {"created_session_ids": session_ids, "message": message}
    except KeyError as e:
        raise InvalidInputError(f"Missing required field: {e}")
    except Exception as e:
        logger.error(f"Unexpected error in handle_modify_schedule: {e}", exc_info=True)
        raise AdminError("An unexpected error occurred while modifying the schedule.")


def handle_get_sessions(semester_id, group_id):
    """Handles retrieving sessions for a specific group/semester/week."""
    try:
        result_data, message = ctrl.get_sessions_by_trimestre_id_and_group_id(
            semester_id=semester_id, group_id=group_id
        )
        if result_data is None:
            if "not found" in message:
                raise ResourceNotFoundError(message)
            else:
                logger.error(f"Failed to get sessions: {message}")
                raise AdminError(
                    "Failed to retrieve sessions due to an internal error."
                )
        else:
            return result_data  # Contains sessions and context
    except Exception as e:
        logger.error(f"Unexpected error in handle_get_sessions: {e}", exc_info=True)
        raise AdminError("An unexpected error occurred while retrieving sessions.")


def handle_delete_sessions(data):
    """Handles deleting multiple sessions by ID."""
    try:
        session_ids = data.get("session_ids")
        if not isinstance(session_ids, list):
            raise InvalidInputError("Field 'session_ids' must be a list.")

        deleted_count, message = ctrl.delete_sessions(session_ids=session_ids)

        if deleted_count is None:  # Controller indicates failure
            logger.error(f"Failed to delete sessions: {message}")
            raise DeletionFailedError(
                "Failed to delete sessions due to an internal error."
            )
        else:
            return {"deleted_count": deleted_count, "message": message}
    except KeyError as e:
        raise InvalidInputError(f"Missing required field: {e}")
    except Exception as e:
        logger.error(f"Unexpected error in handle_delete_sessions: {e}", exc_info=True)
        raise AdminError("An unexpected error occurred while deleting sessions.")
