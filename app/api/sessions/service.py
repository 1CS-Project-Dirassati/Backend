from flask import current_app
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from marshmallow import ValidationError

# from sqlalchemy.orm import joinedload # Keep if needed for optimization later

# Import DB instance and models
from app import db
from app.models import (
    Session,
    Teacher,
    Module,
    Group,
    Semester,
    Salle,
)

# Import shared utilities
from app.utils import (
    err_resp,
    message,
    internal_err_resp,
    validation_error,
)

# Import serialization/deserialization utilities from local utils.py
from .utils import dump_data, load_data  # Use local utils


class SessionService:

    # --- Helper for Foreign Key Validation ---
    @staticmethod
    def _validate_foreign_keys(
        data: dict,
    ):  # -> Dict[str, str]: # Suggestion: Type hints
        """Check if related entities referenced in data exist. Returns dict of errors."""
        errors = {}
        # Check only keys present in the data that have non-None values
        if data.get("teacher_id") is not None and not Teacher.query.get(
            data["teacher_id"]
        ):
            errors["teacher_id"] = f"Teacher with ID {data['teacher_id']} not found."
        if data.get("module_id") is not None and not Module.query.get(
            data["module_id"]
        ):
            errors["module_id"] = f"Module with ID {data['module_id']} not found."
        if data.get("group_id") is not None and not Group.query.get(data["group_id"]):
            errors["group_id"] = f"Group with ID {data['group_id']} not found."
        if data.get("semester_id") is not None and not Semester.query.get(
            data["semester_id"]
        ):
            errors["semester_id"] = f"Semester with ID {data['semester_id']} not found."
        if data.get("salle_id") is not None and not Salle.query.get(data["salle_id"]):
            errors["salle_id"] = f"Salle with ID {data['salle_id']} not found."

        return errors

    # --- GET Single ---
    @staticmethod
    def get_session_data(
        session_id: int,
    ):  # -> Tuple[Dict[str, Any], int]: # Suggestion: Add type hints
        """Get session data by its ID"""
        session = Session.query.get(session_id)
        if not session:
            current_app.logger.info(
                f"Session with ID {session_id} not found."
            )  # Add logging
            return err_resp("Session not found!", "session_404", 404)
        try:
            # Use dump_data for serialization
            session_data = dump_data(session)
            resp = message(True, "Session data sent successfully")
            resp["session"] = session_data
            current_app.logger.debug(
                f"Successfully retrieved session ID {session_id}"
            )  # Add logging
            return resp, 200
        except Exception as error:
            current_app.logger.error(
                f"Error serializing session data for ID {session_id}: {error}",  # Update log message
                exc_info=True,
            )
            return internal_err_resp()

    # --- GET List with Filters and Pagination ---
    @staticmethod
    def get_all_sessions(
        group_id=None, teacher_id=None, page=None, per_page=None,semester_id=None
    ):  # -> Tuple[Dict[str, Any], int]: # Suggestion: Add type hints
        """Get a list of all sessions, optionally filtered and paginated."""
        page = page or 1  # Ensure page defaults to 1 if None
        per_page = per_page or 10  # Get per_page from config or default

        try:
            query = Session.query

            # Apply filters
            if group_id is not None:
                current_app.logger.debug(
                    f"Filtering sessions by group_id: {group_id}"
                )  # Add logging
                # Optional: Check if group exists? Maybe not necessary for filtering.
                query = query.filter(Session.group_id == group_id)
            if teacher_id is not None:
                current_app.logger.debug(
                    f"Filtering sessions by teacher_id: {teacher_id}"
                )  # Add logging
                # Optional: Check if teacher exists?
                query = query.filter(Session.teacher_id == teacher_id)
            # Add other filters (semester, date range) here if needed

            


            if semester_id is not None:
                current_app.logger.debug(
                    f"Filtering sessions by semester_id: {semester_id}"
                )  # Add logging
                # Optional: Check if teacher exists?
                query = query.filter(Session.semester_id == semester_id)

            # Add ordering, e.g., by start time
            query = query.order_by(Session.start_time)

            # Implement pagination
            current_app.logger.debug(
                f"Paginating sessions: page={page}, per_page={per_page}"
            )  # Add logging
            paginated_sessions = query.paginate(
                page=page, per_page=per_page, error_out=False
            )
            current_app.logger.debug(
                f"Paginated sessions items count: {len(paginated_sessions.items)}"
            )  # Add logging

            # Serialize the results using dump_data
            sessions_data = dump_data(
                paginated_sessions.items, many=True
            )  # Use .items for paginated list

            current_app.logger.debug(
                f"Serialized {len(sessions_data)} sessions"
            )  # Add logging
            resp = message(True, "Sessions list retrieved successfully")
            # Add pagination metadata to the response
            resp["sessions"] = sessions_data
            resp["total"] = paginated_sessions.total
            resp["pages"] = paginated_sessions.pages
            resp["current_page"] = paginated_sessions.page
            resp["per_page"] = paginated_sessions.per_page
            resp["has_next"] = paginated_sessions.has_next
            resp["has_prev"] = paginated_sessions.has_prev

            current_app.logger.debug(
                f"Successfully retrieved sessions page {page}. Total: {paginated_sessions.total}"
            )  # Add logging
            return resp, 200

        except Exception as error:
            log_msg = f"Error getting sessions"
            filters = []
            if group_id:
                filters.append(f"group_id={group_id}")
            if teacher_id:
                filters.append(f"teacher_id={teacher_id}")
            if filters:
                log_msg += f" with filters {', '.join(filters)}"
            if page:
                log_msg += f", page {page}"
            current_app.logger.error(f"{log_msg}: {error}", exc_info=True)
            return internal_err_resp()

    # --- CREATE ---
    @staticmethod
    def create_session(
        data: dict,
    ):  # -> Tuple[Dict[str, Any], int]: # Suggestion: Add type hints
        """Create a new session after validating input data"""
        try:
            # 1. Schema Validation & Deserialization using load_data
            new_session_obj = load_data(data)
            current_app.logger.debug(
                f"Session data validated by schema. Proceeding with FK checks."
            )

            # 2. Foreign Key Validation (on the deserialized data dictionary 'data')
            fk_errors = SessionService._validate_foreign_keys(
                data
            )  # Validate original input data
            if fk_errors:
                current_app.logger.warning(
                    f"Foreign key validation failed creating session: {fk_errors}. Data: {data}"
                )
                return validation_error(False, fk_errors), 400

            # 3. Add to DB Session & Commit
            db.session.add(new_session_obj)
            db.session.commit()
            current_app.logger.info(
                f"Session created successfully with ID: {new_session_obj.id}"
            )

            # 4. Serialize & Respond using dump_data
            session_resp_data = dump_data(new_session_obj)
            resp = message(True, "Session created successfully")
            resp["session"] = session_resp_data
            return resp, 201

        except ValidationError as err:
            db.session.rollback()  # Rollback on validation error
            current_app.logger.warning(
                f"Schema validation error creating session: {err.messages}. Data: {data}"
            )
            return validation_error(False, err.messages), 400
        except (
            IntegrityError
        ) as error:  # Catch potential unique constraints if added later
            db.session.rollback()
            current_app.logger.warning(
                f"Database integrity error creating session: {error}. Data: {data}",
                exc_info=True,
            )
            # Add specific checks if needed, e.g., for unique constraints
            return internal_err_resp()  # Or a more specific 409 if applicable
        except SQLAlchemyError as error:
            db.session.rollback()
            current_app.logger.error(
                f"Database error creating session: {error}. Data: {data}", exc_info=True
            )
            return internal_err_resp()
        except Exception as error:
            db.session.rollback()
            current_app.logger.error(
                f"Unexpected error creating session: {error}. Data: {data}",
                exc_info=True,
            )
            return internal_err_resp()

    # --- UPDATE ---
    @staticmethod
    def update_session(
        session_id: int, data: dict
    ):  # -> Tuple[Dict[str, Any], int]: # Suggestion: Add type hints
        """Update an existing session by ID"""
        session = Session.query.get(session_id)
        if not session:
            current_app.logger.info(
                f"Attempted to update non-existent session ID: {session_id}"
            )  # Add logging
            return err_resp("Session not found!", "session_404", 404)

        if not data:
            current_app.logger.warning(
                f"Attempted update for session {session_id} with empty data."
            )  # Add logging
            return err_resp(
                "Request body cannot be empty for update.", "empty_update_data", 400
            )

        try:
            # 1. Schema Validation & Deserialization into existing instance using load_data
            updated_session = load_data(data, partial=True, instance=session)
            current_app.logger.debug(
                f"Session data validated by schema for update. Proceeding with FK checks for ID: {session_id}"
            )

            # 2. Foreign Key Validation (on the input data 'data' for fields being updated)
            fk_errors = SessionService._validate_foreign_keys(
                data
            )  # Validate original input data fields
            if fk_errors:
                current_app.logger.warning(
                    f"Foreign key validation failed updating session {session_id}: {fk_errors}. Data: {data}"
                )
                # No rollback needed yet as commit hasn't happened
                return validation_error(False, fk_errors), 400

            # 3. Commit Changes (object is already in session and modified)
            # db.session.add(updated_session) # Not strictly needed when modifying instance loaded in session
            db.session.commit()
            current_app.logger.info(
                f"Session updated successfully for ID: {session_id}"
            )

            # 4. Serialize & Respond using dump_data
            session_resp_data = dump_data(updated_session)
            resp = message(True, "Session updated successfully")
            resp["session"] = session_resp_data
            return resp, 200

        except ValidationError as err:
            db.session.rollback()  # Rollback on validation error
            current_app.logger.warning(
                f"Schema validation error updating session {session_id}: {err.messages}. Data: {data}"
            )
            return validation_error(False, err.messages), 400
        except IntegrityError as error:
            db.session.rollback()
            current_app.logger.warning(
                f"Database integrity error updating session {session_id}: {error}. Data: {data}",
                exc_info=True,
            )
            # Add specific checks if needed
            return internal_err_resp()  # Or a more specific 409
        except SQLAlchemyError as error:
            db.session.rollback()
            current_app.logger.error(
                f"Database error updating session {session_id}: {error}. Data: {data}",
                exc_info=True,
            )
            return internal_err_resp()
        except Exception as error:
            db.session.rollback()
            current_app.logger.error(
                f"Unexpected error updating session {session_id}: {error}. Data: {data}",
                exc_info=True,
            )
            return internal_err_resp()

    # --- DELETE ---
    @staticmethod
    def delete_session(
        session_id: int,
    ):  # -> Tuple[None, int]: # Suggestion: Add type hints
        """Delete a session by ID"""
        session = Session.query.get(session_id)
        if not session:
            current_app.logger.info(
                f"Attempted to delete non-existent session ID: {session_id}"
            )  # Add logging
            return err_resp("Session not found!", "session_404", 404)

        try:
            # Check for dependencies if cascade delete is not fully reliable or if specific checks are needed.
            # Example: Check if associated absences exist IF cascade is not set/trusted for that relationship.
            # if session.absences: # Assuming 'absences' is the relationship name
            #    current_app.logger.warning(f"Attempted to delete session {session_id} with existing absences.")
            #    return err_resp("Cannot delete session with existing attendance records.", "delete_conflict_absences", 409)

            current_app.logger.debug(
                f"Deleting session ID: {session_id}"
            )  # Add logging
            db.session.delete(session)
            db.session.commit()
            current_app.logger.info(
                f"Session deleted successfully: ID {session_id}"
            )  # Add logging
            return None, 204

        except SQLAlchemyError as error:
            db.session.rollback()
            current_app.logger.error(
                f"Database error deleting session {session_id}: {error}", exc_info=True
            )
            # Check for specific constraint errors if necessary
            # if "constraint" in str(error).lower():
            #     return err_resp("Cannot delete session due to related records.", "delete_conflict_db", 409)
            return err_resp(
                f"Could not delete session due to a database error.",  # Simplified message
                "delete_error_db",
                500,
            )
        except Exception as error:
            db.session.rollback()
            current_app.logger.error(
                f"Unexpected error deleting session {session_id}: {error}",
                exc_info=True,
            )
            return internal_err_resp()
