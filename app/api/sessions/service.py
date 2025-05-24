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
    Level,
    TeacherModuleAssociation,
    Student,
)
from app.models.TimeSlot import TimeSlot

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

    # --- GET Group Time Slots ---
    @staticmethod
    def get_group_time_slots(group_id):
        """Get a map of time slots with teacher-module pairs for a specific group"""
        try:
            # 1. Get the group and verify it exists
            group = Group.query.get(group_id)
            if not group:
                return err_resp("Group not found!", "group_404", 404)

            # 2. Get all modules for the group's level
            level_modules = Module.query.filter_by(level_id=group.level_id).all()
            if not level_modules:
                return message(True, "No modules found for this level"), 200

            # 3. Initialize the time slot map with all possible time slots
            time_slots = {slot.value: [] for slot in TimeSlot}

            # 4. For each module, get assigned teachers and check their availability
            for module in level_modules:
                # Get teachers assigned to this module
                teacher_associations = TeacherModuleAssociation.query.filter_by(
                    module_id=module.id
                ).all()

                for assoc in teacher_associations:
                    teacher = Teacher.query.get(assoc.teacher_id)
                    if not teacher:
                        continue

                    # Get all sessions for this teacher to check availability
                    teacher_sessions = Session.query.filter_by(teacher_id=teacher.id).all()
                    occupied_slots = {session.time_slot.value for session in teacher_sessions}

                    # For each time slot, check if teacher is available
                    for slot in TimeSlot:
                        if slot.value not in occupied_slots:
                            # Add teacher-module pair to this time slot
                            time_slots[slot.value].append({
                                "teacher_id": teacher.id,
                                "teacher_name": f"{teacher.first_name} {teacher.last_name}",
                                "module_id": module.id,
                                "module_name": module.name
                            })

            resp = message(True, "Time slot map retrieved successfully")
            resp["time_slots"] = time_slots
            return resp, 200

        except Exception as error:
            current_app.logger.error(
                f"Error getting time slots for group {group_id}: {error}",
                exc_info=True
            )
            return internal_err_resp()

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
            # Get related data
            teacher = Teacher.query.get(session.teacher_id)
            module = Module.query.get(session.module_id)
            group = Group.query.get(session.group_id)
            semester = Semester.query.get(session.semester_id)
            salle = Salle.query.get(session.salle_id) if session.salle_id else None

            # Use dump_data for serialization
            session_data = dump_data(session)
            
            # Add names to the response
            session_data["teacher_name"] = f"{teacher.first_name} {teacher.last_name}" if teacher else None
            session_data["module_name"] = module.name if module else None
            session_data["group_name"] = group.name if group else None
            session_data["semester_name"] = semester.name if semester else None
            session_data["salle_name"] = salle.name if salle else None

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
        group_id=None, teacher_id=None, page=None, per_page=None, semester_id=None, week=None,
        current_user_id=None, current_user_role=None
    ):
        """Get a list of all sessions, optionally filtered and paginated."""
        page = page or 1
        per_page = per_page or 10

        try:
            query = Session.query

            # Apply role-based filtering
            if current_user_role == "teacher":
                current_app.logger.debug(f"Filtering sessions for teacher ID: {current_user_id}")
                query = query.filter(Session.teacher_id == current_user_id)
            elif current_user_role == "student":
                # Get the student's group
                student = Student.query.get(current_user_id)
                if student and student.group_id:
                    current_app.logger.debug(f"Filtering sessions for student {current_user_id}'s group: {student.group_id}")
                    query = query.filter(Session.group_id == student.group_id)
                else:
                    current_app.logger.warning(f"Student {current_user_id} has no group assigned")
                    return message(True, "No sessions found - student not assigned to a group"), 200

            # Apply additional filters if provided
            if group_id is not None:
                current_app.logger.debug(f"Filtering sessions by group_id: {group_id}")
                query = query.filter(Session.group_id == group_id)
            if teacher_id is not None:
                current_app.logger.debug(f"Filtering sessions by teacher_id: {teacher_id}")
                query = query.filter(Session.teacher_id == teacher_id)
            if semester_id is not None:
                current_app.logger.debug(f"Filtering sessions by semester_id: {semester_id}")
                query = query.filter(Session.semester_id == semester_id)
            if week is not None:
                current_app.logger.debug(f"Filtering sessions by week: {week}")
                query = query.filter(Session.weeks == week)

            # Add ordering by time_slot
            query = query.order_by(Session.time_slot)

            # Implement pagination
            current_app.logger.debug(f"Paginating sessions: page={page}, per_page={per_page}")
            paginated_sessions = query.paginate(page=page, per_page=per_page, error_out=False)
            current_app.logger.debug(f"Paginated sessions items count: {len(paginated_sessions.items)}")

            # Get all related data in one go to avoid N+1 queries
            session_ids = [s.id for s in paginated_sessions.items]
            teachers = {t.id: t for t in Teacher.query.filter(Teacher.id.in_([s.teacher_id for s in paginated_sessions.items])).all()}
            modules = {m.id: m for m in Module.query.filter(Module.id.in_([s.module_id for s in paginated_sessions.items])).all()}
            groups = {g.id: g for g in Group.query.filter(Group.id.in_([s.group_id for s in paginated_sessions.items])).all()}
            semesters = {s.id: s for s in Semester.query.filter(Semester.id.in_([s.semester_id for s in paginated_sessions.items])).all()}
            salles = {s.id: s for s in Salle.query.filter(Salle.id.in_([s.salle_id for s in paginated_sessions.items if s.salle_id])).all()}

            # Serialize the results using dump_data
            sessions_data = dump_data(paginated_sessions.items, many=True)

            # Add names to each session
            for session_data in sessions_data:
                teacher = teachers.get(session_data["teacher_id"])
                module = modules.get(session_data["module_id"])
                group = groups.get(session_data["group_id"])
                semester = semesters.get(session_data["semester_id"])
                salle = salles.get(session_data["salle_id"]) if session_data.get("salle_id") else None

                session_data["teacher_name"] = f"{teacher.first_name} {teacher.last_name}" if teacher else None
                session_data["module_name"] = module.name if module else None
                session_data["group_name"] = group.name if group else None
                session_data["semester_name"] = semester.name if semester else None
                session_data["salle_name"] = salle.name if salle else None

            current_app.logger.debug(f"Serialized {len(sessions_data)} sessions")
            resp = message(True, "Sessions list retrieved successfully")
            resp["sessions"] = sessions_data
            resp["total"] = paginated_sessions.total
            resp["pages"] = paginated_sessions.pages
            resp["current_page"] = paginated_sessions.page
            resp["per_page"] = paginated_sessions.per_page
            resp["has_next"] = paginated_sessions.has_next
            resp["has_prev"] = paginated_sessions.has_prev

            current_app.logger.debug(f"Successfully retrieved sessions page {page}. Total: {paginated_sessions.total}")
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
        """Create new sessions for each week of the semester"""
        try:
            # 1. Get semester duration
            semester = Semester.query.get(data.get("semester_id"))
            if not semester:
                return err_resp("Semester not found!", "semester_404", 404)
            
            if not semester.duration:
                return err_resp("Semester duration not set!", "semester_duration_404", 400)

            # 2. Schema Validation & Deserialization using load_data
            new_session_obj = load_data(data)
            current_app.logger.debug(
                f"Session data validated by schema. Proceeding with FK checks."
            )

            # 3. Foreign Key Validation
            fk_errors = SessionService._validate_foreign_keys(data)
            if fk_errors:
                current_app.logger.warning(
                    f"Foreign key validation failed creating session: {fk_errors}. Data: {data}"
                )
                return validation_error(False, fk_errors), 400

            # 4. Create sessions for each week
            created_sessions = []
            for week in range(1, semester.duration + 1):
                session_obj = load_data(data)  # Create new instance for each week
                session_obj.weeks = week
                db.session.add(session_obj)
                created_sessions.append(session_obj)

            # 5. Commit all sessions
            db.session.commit()
            current_app.logger.info(
                f"Created {len(created_sessions)} sessions for semester {semester.id}"
            )

            # 6. Serialize & Respond
            sessions_data = dump_data(created_sessions, many=True)
            resp = message(True, f"Created {len(created_sessions)} sessions successfully")
            resp["sessions"] = sessions_data
            return resp, 201

        except ValidationError as err:
            db.session.rollback()
            current_app.logger.warning(
                f"Schema validation error creating sessions: {err.messages}. Data: {data}"
            )
            return validation_error(False, err.messages), 400
        except IntegrityError as error:
            db.session.rollback()
            current_app.logger.warning(
                f"Database integrity error creating sessions: {error}. Data: {data}",
                exc_info=True,
            )
            return internal_err_resp()
        except SQLAlchemyError as error:
            db.session.rollback()
            current_app.logger.error(
                f"Database error creating sessions: {error}. Data: {data}", exc_info=True
            )
            return internal_err_resp()
        except Exception as error:
            db.session.rollback()
            current_app.logger.error(
                f"Unexpected error creating sessions: {error}. Data: {data}",
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
