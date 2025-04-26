from flask import current_app
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from marshmallow import ValidationError
from sqlalchemy.orm import joinedload  # For potential optimization

# Import DB instance and models
from app import db
from app.models import (
    Session,
    Teacher,
    Module,
    Group,
    Semester,
    Salle,
)  # Import related models for FK checks

# Import shared utilities and the schema CLASS
from app.models.Schemas import SessionSchema
from app.utils import err_resp, message, internal_err_resp, validation_error

# --- Schema instances FOR VALIDATION (.load) ---
session_create_schema = SessionSchema()
# When loading for update, ensure DateTime fields are handled correctly if partial
session_update_schema = SessionSchema(partial=True)

# --- Utility for SERIALIZATION (.dump) ---
from .utils import load_data


class SessionService:

    # --- Helper for Foreign Key Validation ---
    @staticmethod
    def _validate_foreign_keys(data, is_update=False):
        """Check if related entities exist"""
        errors = {}
        # Check only keys present in the data
        if "teacher_id" in data and not Teacher.query.get(data["teacher_id"]):
            errors["teacher_id"] = f"Teacher with ID {data['teacher_id']} not found."
        if "module_id" in data and not Module.query.get(data["module_id"]):
            errors["module_id"] = f"Module with ID {data['module_id']} not found."
        if "group_id" in data and not Group.query.get(data["group_id"]):
            errors["group_id"] = f"Group with ID {data['group_id']} not found."
        if "semester_id" in data and not Semester.query.get(data["semester_id"]):
            errors["semester_id"] = f"Semester with ID {data['semester_id']} not found."
        # Salle is nullable, but if provided, it should exist
        if data.get("salle_id") is not None and not Salle.query.get(data["salle_id"]):
            errors["salle_id"] = f"Salle with ID {data['salle_id']} not found."

        # For create, all required FKs must be valid
        if not is_update:
            required_keys = {"teacher_id", "module_id", "group_id", "semester_id"}
            missing = required_keys - data.keys()
            # This should ideally be caught by schema validation, but double-check
            if missing:
                for key in missing:
                    errors[key] = "Required field missing."

        return errors

    # --- GET Single ---
    @staticmethod
    def get_session_data(session_id):
        """Get session data by its ID"""
        # Consider using joinedload if you often need related object data
        # session = Session.query.options(joinedload(Session.teacher), ...).get(session_id)
        session = Session.query.get(session_id)
        if not session:
            return err_resp("Session not found!", "session_404", 404)
        try:
            session_data = load_data(session)
            resp = message(True, "Session data sent successfully")
            resp["session"] = session_data
            return resp, 200
        except Exception as error:
            current_app.logger.error(
                f"Error getting session data for ID {session_id}: {error}",
                exc_info=True,
            )
            return internal_err_resp()

    # --- GET List with Filters ---
    @staticmethod
    def get_all_sessions(group_id=None, teacher_id=None):
        """Get a list of all sessions, optionally filtered"""
        try:
            query = Session.query

            # Apply filters
            if group_id is not None:
                query = query.filter(Session.group_id == group_id)
            if teacher_id is not None:
                query = query.filter(Session.teacher_id == teacher_id)
            # Add other filters (semester, date range) here if needed

            # Add ordering, e.g., by start time
            sessions = query.order_by(Session.start_time).all()

            sessions_data = load_data(sessions, many=True)
            resp = message(True, "Sessions list retrieved successfully")
            resp["sessions"] = sessions_data
            return resp, 200
        except Exception as error:
            log_msg = f"Error getting all sessions"
            filters = []
            if group_id:
                filters.append(f"group_id={group_id}")
            if teacher_id:
                filters.append(f"teacher_id={teacher_id}")
            if filters:
                log_msg += f" with filters {', '.join(filters)}"
            current_app.logger.error(f"{log_msg}: {error}", exc_info=True)
            return internal_err_resp()

    # --- CREATE ---
    @staticmethod
    def create_session(data):
        """Create a new session after validating input data"""
        try:
            # 1. Schema Validation
            validated_data = session_create_schema.load(data)

            # 2. Foreign Key Validation
            fk_errors = SessionService._validate_foreign_keys(
                validated_data, is_update=False
            )
            if fk_errors:
                # Return validation error response with FK details
                return validation_error(False, fk_errors), 400

            # 3. Create Instance & Commit
            new_session = Session(**validated_data)
            db.session.add(new_session)
            db.session.commit()

            # 4. Serialize & Respond
            session_data = load_data(new_session)
            resp = message(True, "Session created successfully")
            resp["session"] = session_data
            return resp, 201

        except ValidationError as err:
            current_app.logger.warning(
                f"Validation error creating session: {err.messages}"
            )
            return validation_error(False, err.messages), 400
        # Catch potential IntegrityErrors (e.g., if unique constraints were added)
        except IntegrityError as error:
            db.session.rollback()
            current_app.logger.warning(
                f"Database integrity error creating session: {error}", exc_info=True
            )
            return internal_err_resp()
        except SQLAlchemyError as error:
            db.session.rollback()
            current_app.logger.error(
                f"Database error creating session: {error}", exc_info=True
            )
            return internal_err_resp()
        except Exception as error:
            db.session.rollback()
            current_app.logger.error(f"Error creating session: {error}", exc_info=True)
            return internal_err_resp()

    # --- UPDATE ---
    @staticmethod
    def update_session(session_id, data):
        """Update an existing session by ID"""
        session = Session.query.get(session_id)
        if not session:
            return err_resp("Session not found!", "session_404", 404)

        if not data:
            return err_resp(
                "Request body cannot be empty for update.", "empty_update_data", 400
            )

        try:
            # 1. Schema Validation (Partial)
            # Pass 'unknown=EXCLUDE' if you want to ignore extra fields in input
            validated_data = session_update_schema.load(data)

            # 2. Foreign Key Validation (only for keys being updated)
            fk_errors = SessionService._validate_foreign_keys(
                validated_data, is_update=True
            )
            if fk_errors:
                return validation_error(False, fk_errors), 400

            # 3. Update Instance Fields & Commit
            for key, value in validated_data.items():
                setattr(session, key, value)
            db.session.add(session)  # Add potentially modified session to session
            db.session.commit()

            # 4. Serialize & Respond
            session_data = load_data(session)
            resp = message(True, "Session updated successfully")
            resp["session"] = session_data
            return resp, 200

        except ValidationError as err:
            db.session.rollback()
            current_app.logger.warning(
                f"Validation error updating session {session_id}: {err.messages}"
            )
            return validation_error(False, err.messages), 400
        except IntegrityError as error:
            db.session.rollback()
            current_app.logger.warning(
                f"Database integrity error updating session {session_id}: {error}",
                exc_info=True,
            )
            return internal_err_resp()
        except SQLAlchemyError as error:
            db.session.rollback()
            current_app.logger.error(
                f"Database error updating session {session_id}: {error}", exc_info=True
            )
            return internal_err_resp()
        except Exception as error:
            db.session.rollback()
            current_app.logger.error(
                f"Error updating session {session_id}: {error}", exc_info=True
            )
            return internal_err_resp()

    # --- DELETE ---
    @staticmethod
    def delete_session(session_id):
        """Delete a session by ID"""
        session = Session.query.get(session_id)
        if not session:
            return err_resp("Session not found!", "session_404", 404)

        try:
            # Absences relationship has cascade="all, delete-orphan", so they should be deleted automatically.
            # If there were other critical dependencies without cascade, check them here.
            # Example: if session.some_other_important_relation:
            #     return err_resp("Cannot delete session with active relations.", "delete_conflict", 409)

            db.session.delete(session)
            db.session.commit()
            return None, 204  # 204 No Content

        except (
            SQLAlchemyError
        ) as error:  # Catch potential DB errors during cascade or delete
            db.session.rollback()
            current_app.logger.error(
                f"Database error deleting session {session_id}: {error}", exc_info=True
            )
            return err_resp(
                f"Could not delete session due to a database constraint or error.",
                "delete_error_db",
                500,
            )
        except Exception as error:
            db.session.rollback()
            current_app.logger.error(
                f"Error deleting session {session_id}: {error}", exc_info=True
            )
            return internal_err_resp()
