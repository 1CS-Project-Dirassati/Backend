# Added current_app
from flask import current_app
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from marshmallow import ValidationError
from sqlalchemy.orm import joinedload
from datetime import datetime  # For date parsing

# Import DB instance and models
from app import db

# Import related models needed for checks and context
from app.models import Absence, Student, Session, Teacher, Parent

# Import shared utilities
from app.utils import (
    err_resp,
    message,
    internal_err_resp,
    validation_error,
)

# Import serialization/deserialization utilities from local utils.py
from .utils import dump_data, load_data


class AbsenceService:

    # --- Helper for Foreign Key Validation ---
    @staticmethod
    def _validate_foreign_keys(data: dict):
        """Check if related entities referenced in data exist. Returns dict of errors."""
        errors = {}
        if data.get("student_id") is not None:
            if not Student.query.get(data["student_id"]):
                errors["student_id"] = (
                    f"Student with ID {data['student_id']} not found."
                )
        if data.get("session_id") is not None:
            if not Session.query.get(data["session_id"]):
                errors["session_id"] = (
                    f"Session with ID {data['session_id']} not found."
                )
        return errors

    # --- GET Single ---
    @staticmethod
    # Add type hints
    def get_absence_data(absence_id: int, current_user_id: int, current_user_role: str):
        """Get absence data by ID, with record-level authorization check"""
        # Eager load related data for context and auth checks
        absence = Absence.query.options(
            joinedload(Absence.student).joinedload(
                Student.parent
            ),  # Load student and their parent
            joinedload(Absence.session).joinedload(
                Session.teacher
            ),  # Load session and its teacher
        ).get(absence_id)

        if not absence:
            current_app.logger.info(f"Absence record with ID {absence_id} not found.")
            return err_resp("Absence record not found!", "absence_404", 404)

        # --- Record-Level Authorization Check ---
        can_access = False
        log_reason = ""
        if current_user_role == "admin":
            can_access = True
            log_reason = "User is admin."
        elif (
            absence.session and absence.session.teacher_id == int(current_user_id)
        ):  # Check if user is the teacher of the session
            can_access = True
            log_reason = "User is the teacher of the session."
        elif current_user_role == "student" and absence.student_id == int(current_user_id):
            can_access = True
            log_reason = "User is the student associated with the absence."
        # Check parent access using the eager-loaded student.parent_id
        elif (
            current_user_role == "parent"
            and absence.student
            and absence.student.parent_id == int(current_user_id)
        ):
            can_access = True
            log_reason = (
                "User is the parent of the student associated with the absence."
            )

        if not can_access:
            current_app.logger.warning(
                f"Forbidden: User {current_user_id} (Role: {current_user_role}) attempted to access absence record {absence_id}."
            )
            return err_resp(
                "Forbidden: You do not have permission to access this absence record.",
                "record_access_denied",
                403,
            )
        current_app.logger.debug(
            f"Record access granted for user {current_user_id} to absence {absence_id}. Reason: {log_reason}"
        )

        try:
            absence_data = dump_data(absence)
            resp = message(True, "Absence record data sent successfully")
            resp["absence"] = absence_data
            current_app.logger.debug(
                f"Successfully retrieved absence record ID {absence_id}"
            )
            return resp, 200
        except Exception as error:
            current_app.logger.error(
                f"Error serializing absence data for ID {absence_id}: {error}",
                exc_info=True,
            )
            return internal_err_resp()

    # --- GET List with Filters, Pagination & Authorization ---
    @staticmethod
    # Add type hints
    def get_all_absences(
        student_id=None,
        session_id=None,
        justified=None,
        start_date=None,
        end_date=None,
        page=None,
        per_page=None,
        current_user_id=None,
        current_user_role=None,
    ):
        """Get a paginated list of absences, filtered, with role-based data scoping"""
        page = page or 1
        per_page = per_page or 10

        try:
            # Eager load student->parent and session->teacher for filtering/auth
            query = Absence.query.options(
                joinedload(Absence.student).joinedload(Student.parent),
                joinedload(Absence.session).joinedload(Session.teacher),
            )

            child_ids_for_parent = []  # Store child IDs if user is parent

            # --- Role-Based Data Scoping ---
            if current_user_role == "student":
                current_app.logger.debug(
                    f"Scoping absences list for student ID: {current_user_id}"
                )
                query = query.filter(Absence.student_id == int(current_user_id))
                student_id = current_user_id  # Force student_id filter
                session_id = None  # Ignore session filter from student
            elif current_user_role == "parent":
                parent = Parent.query.options(joinedload(Parent.students)).get(
                    current_user_id
                )
                if not parent:
                    return (
                        message(True, "Parent profile not found, cannot list absences.")
                        | {
                            "absences": [],
                            "total": 0,
                            "pages": 0,
                            "current_page": 1,
                            "per_page": per_page,
                            "has_next": False,
                            "has_prev": False,
                        },
                        200,
                    )

                child_ids_for_parent = [student.id for student in parent.students]
                if not child_ids_for_parent:
                    return (
                        message(True, "No students found for this parent.")
                        | {
                            "absences": [],
                            "total": 0,
                            "pages": 0,
                            "current_page": 1,
                            "per_page": per_page,
                            "has_next": False,
                            "has_prev": False,
                        },
                        200,
                    )

                current_app.logger.debug(
                    f"Scoping absences list for parent ID: {current_user_id}, Children IDs: {child_ids_for_parent}"
                )
                query = query.filter(Absence.student_id.in_(child_ids_for_parent))

                if student_id is not None and student_id not in child_ids_for_parent:
                    return err_resp(
                        "Forbidden: You can only filter by your own children's student IDs.",
                        "parent_filter_denied",
                        403,
                    )
            elif current_user_role == "teacher":
                # Teachers see absences for sessions THEY teach
                current_app.logger.debug(
                    f"Scoping absences list for teacher ID: {current_user_id}"
                )
                query = query.join(Absence.session).filter(
                    Session.teacher_id == int(current_user_id)
                )
            # Admins see all

            # --- Apply Standard Filters ---
            filters_applied = {}
            if student_id is not None:
                # Parent/Student role already filtered or validated above
                filters_applied["student_id"] = student_id
                query = query.filter(Absence.student_id == student_id)
            if session_id is not None:
                filters_applied["session_id"] = session_id
                query = query.filter(Absence.session_id == session_id)
            if justified is not None:
                filters_applied["justified"] = justified
                query = query.filter(Absence.justified == justified)

            # Date filters (apply to session start_time)
            if start_date:
                try:
                    start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
                    filters_applied["start_date"] = start_date
                    query = query.join(Absence.session).filter(
                        Session.start_time >= start_dt
                    )
                except ValueError:
                    return err_resp(
                        "Invalid start_date format. Use YYYY-MM-DD.",
                        "invalid_date_format",
                        400,
                    )
            if end_date:
                try:
                    end_dt = datetime.strptime(end_date, "%Y-%m-%d").date()
                    filters_applied["end_date"] = end_date
                    # Add 1 day to end_dt to make it inclusive of the end date
                    from datetime import timedelta

                    query = query.join(Absence.session).filter(
                        Session.start_time < (end_dt + timedelta(days=1))
                    )
                except ValueError:
                    return err_resp(
                        "Invalid end_date format. Use YYYY-MM-DD.",
                        "invalid_date_format",
                        400,
                    )

            if filters_applied:
                current_app.logger.debug(
                    f"Applying absence list filters: {filters_applied}"
                )

            # Add ordering (e.g., by session date descending)
            query = query.join(Absence.session).order_by(
                Session.start_time.desc(), Absence.recorded_at.desc()
            )

            # Implement pagination
            current_app.logger.debug(
                f"Paginating absences: page={page}, per_page={per_page}"
            )
            paginated_absences = query.paginate(
                page=page, per_page=per_page, error_out=False
            )
            current_app.logger.debug(
                f"Paginated absences items count: {len(paginated_absences.items)}"
            )

            # Serialize results using dump_data
            absences_data = dump_data(paginated_absences.items, many=True)

            current_app.logger.debug(f"Serialized {len(absences_data)} absences")
            resp = message(True, "Absences list retrieved successfully")
            # Add pagination metadata
            resp["absences"] = absences_data
            resp["total"] = paginated_absences.total
            resp["pages"] = paginated_absences.pages
            resp["current_page"] = paginated_absences.page
            resp["per_page"] = paginated_absences.per_page
            resp["has_next"] = paginated_absences.has_next
            resp["has_prev"] = paginated_absences.has_prev

            current_app.logger.debug(
                f"Successfully retrieved absences page {page}. Total: {paginated_absences.total}"
            )
            return resp, 200

        except Exception as error:
            log_msg = f"Error getting absences list (role: {current_user_role})"
            if page:
                log_msg += f", page {page}"
            current_app.logger.error(f"{log_msg}: {error}", exc_info=True)
            return internal_err_resp()

    # --- CREATE (Teacher/Admin) ---
    @staticmethod
    # Add type hints
    def create_absence(data: dict, current_user_id: int, current_user_role: str):
        """Record a new absence. Assumes @roles_required handled base role."""
        try:
            # 1. Schema Validation
            # Using temporary manual load until load_data adjusted/confirmed.
            from app.models.Schemas import AbsenceSchema  # Temp import

            absence_create_schema = AbsenceSchema()  # Temp instance
            validated_data = absence_create_schema.load(data)
            # End Temporary block

            current_app.logger.debug("Absence data validated by schema.")

            # 2. Foreign Key Validation & Fetch Session
            fk_errors = AbsenceService._validate_foreign_keys(data)
            if fk_errors:
                current_app.logger.warning(
                    f"Foreign key validation failed creating absence: {fk_errors}. Data: {data}"
                )
                return validation_error(False, fk_errors), 400

            # Fetch the session and student
            session = Session.query.get(data["session_id"])
            student = Student.query.get(data["student_id"])

            # 3. Validate Student Group
            if not student:
                return err_resp("Student not found.", "student_404", 404)
            
            if not session:
                return err_resp("Session not found.", "session_404", 404)

            # Check if student belongs to the session's group
            if student.group_id != session.group_id:
                current_app.logger.warning(
                    f"Student {student.id} does not belong to group {session.group_id} of session {session.id}"
                )
                return err_resp(
                    "Student does not belong to the group of this session.",
                    "student_group_mismatch",
                    403,
                )

            # 4. Authorization Check
            if current_user_role == "teacher" and session.teacher_id != int(current_user_id):
                current_app.logger.warning(
                    f"Forbidden: Teacher {current_user_id} attempted to record absence for session {session.id} taught by teacher {session.teacher_id}."
                )
                return err_resp(
                    "Forbidden: You can only record absences for sessions you teach.",
                    "session_teacher_mismatch",
                    403,
                )
            # Admins are allowed

            # 5. Validate Reason if Justified
            if data.get("justified") and not data.get("reason"):
                return err_resp(
                    "Reason is required if absence is justified.",
                    "justification_reason_missing",
                    400,
                )

            # 6. Create Instance & Commit
            new_absence = Absence(
                student_id=data["student_id"],
                session_id=data["session_id"],
                justified=data.get("justified", False),
                reason=data.get("reason")
            )
            db.session.add(new_absence)
            db.session.commit()
            current_app.logger.info(
                f"Absence record created successfully with ID: {new_absence.id} by User ID: {current_user_id}"
            )

            # 7. Serialize & Respond using dump_data
            absence_resp_data = dump_data(new_absence)
            resp = message(True, "Absence recorded successfully.")
            resp["absence"] = absence_resp_data
            return resp, 201

        except ValidationError as err:
            db.session.rollback()
            current_app.logger.warning(
                f"Schema validation error creating absence: {err.messages}. Data: {data}"
            )
            return validation_error(False, err.messages), 400
        except (
            IntegrityError
        ) as error:  # Catches the unique constraint (_student_session_uc)
            db.session.rollback()
            current_app.logger.warning(
                f"Integrity error creating absence (likely duplicate): {error}. Data: {data}",
                exc_info=True,
            )
            if "_student_session_uc" in str(error.orig):
                return err_resp(
                    "An absence record for this student in this session already exists.",
                    "duplicate_absence",
                    409,
                )
            return internal_err_resp()
        except SQLAlchemyError as error:
            db.session.rollback()
            current_app.logger.error(
                f"Database error creating absence: {error}. Data: {data}", exc_info=True
            )
            return internal_err_resp()
        except Exception as error:
            db.session.rollback()
            current_app.logger.error(
                f"Unexpected error creating absence: {error}. Data: {data}",
                exc_info=True,
            )
            return internal_err_resp()

    # --- UPDATE (Teacher/Admin) ---
    @staticmethod
    # Add type hints
    def update_absence(
        absence_id: int, data: dict, current_user_id: int, current_user_role: str
    ):
        """Update an existing absence record (justification, reason). Assumes @roles_required handled base role."""
        # Eager load session and teacher for auth check
        absence = Absence.query.options(
            joinedload(Absence.session).joinedload(Session.teacher)
        ).get(absence_id)

        if not absence:
            current_app.logger.info(
                f"Attempted update for non-existent absence ID: {absence_id}"
            )
            return err_resp("Absence record not found!", "absence_404", 404)

        # --- Record-Level Authorization Check ---
        can_update = (current_user_role == "admin") or (
            absence.session and absence.session.teacher_id == int(current_user_id)
        )

        if not can_update:
            teacher_info = (
                f"teacher {absence.session.teacher_id}"
                if absence.session
                else "unknown teacher"
            )
            current_app.logger.warning(
                f"Forbidden: User {current_user_id} (Role: {current_user_role}) attempted to update absence {absence_id} linked to session with {teacher_info}."
            )
            return err_resp(
                "Forbidden: You cannot update this absence record.",
                "update_forbidden",
                403,
            )

        if not data:
            current_app.logger.warning(
                f"Attempted update for absence {absence_id} with empty data."
            )
            return err_resp(
                "Request body cannot be empty for update.", "empty_update_data", 400
            )

        try:
            # 1. Schema Validation & Deserialization
            from app.models.Schemas import AbsenceSchema  # Temp import
            absence_update_schema = AbsenceSchema(partial=True, only=("justified", "reason"))
            validated_data = absence_update_schema.load(data)

            current_app.logger.debug(
                f"Absence data validated by schema for update ID: {absence_id}"
            )

            # 2. Update fields if provided
            updated = False
            if "justified" in data:
                absence.justified = data["justified"]
                updated = True

            if "reason" in data:
                absence.reason = data["reason"]
                updated = True

            if not updated:
                return err_resp(
                    "No valid fields provided for update.", "no_update_fields", 400
                )

            # 3. Validate Reason if Justified (after potential updates)
            if absence.justified and not absence.reason:
                return err_resp(
                    "Reason is required if absence is justified.",
                    "justification_reason_missing",
                    400,
                )

            # 4. Commit Changes
            db.session.add(absence)
            db.session.commit()
            current_app.logger.info(
                f"Absence record updated successfully for ID: {absence_id} by User ID: {current_user_id}"
            )

            # 5. Serialize & Respond using dump_data
            absence_resp_data = dump_data(absence)
            resp = message(True, "Absence record updated successfully.")
            resp["absence"] = absence_resp_data
            return resp, 200

        except ValidationError as err:
            db.session.rollback()
            current_app.logger.warning(
                f"Schema validation error updating absence {absence_id}: {err.messages}. Data: {data}"
            )
            return validation_error(False, err.messages), 400
        except SQLAlchemyError as error:
            db.session.rollback()
            current_app.logger.error(
                f"Database error updating absence {absence_id}: {error}. Data: {data}",
                exc_info=True,
            )
            return internal_err_resp()
        except Exception as error:
            db.session.rollback()
            current_app.logger.error(
                f"Unexpected error updating absence {absence_id}: {error}. Data: {data}",
                exc_info=True,
            )
            return internal_err_resp()

    # --- DELETE (Teacher/Admin) ---
    @staticmethod
    # Add type hint
    def delete_absence(absence_id: int, current_user_id: int, current_user_role: str):
        """Delete an absence record. Assumes @roles_required handled base role."""
        # Eager load session and teacher for auth check
        absence = Absence.query.options(
            joinedload(Absence.session).joinedload(Session.teacher)
        ).get(absence_id)

        if not absence:
            current_app.logger.info(
                f"Attempted delete for non-existent absence ID: {absence_id}"
            )
            return err_resp("Absence record not found!", "absence_404", 404)

        # --- Record-Level Authorization Check ---
        can_delete = (current_user_role == "admin") or (
            absence.session and absence.session.teacher_id == int(current_user_id)
        )

        if not can_delete:
            teacher_info = (
                f"teacher {absence.session.teacher_id}"
                if absence.session
                else "unknown teacher"
            )
            current_app.logger.warning(
                f"Forbidden: User {current_user_id} (Role: {current_user_role}) attempted to delete absence {absence_id} linked to session with {teacher_info}."
            )
            return err_resp(
                "Forbidden: You cannot delete this absence record.",
                "delete_forbidden",
                403,
            )

        try:
            current_app.logger.warning(
                f"User {current_user_id} (Role: {current_user_role}) attempting to delete absence record {absence_id}."
            )

            db.session.delete(absence)
            db.session.commit()

            current_app.logger.info(
                f"Absence record {absence_id} deleted successfully by User ID: {current_user_id}."
            )
            return None, 204

        except SQLAlchemyError as error:
            db.session.rollback()
            current_app.logger.error(
                f"Database error deleting absence {absence_id}: {error}", exc_info=True
            )
            return err_resp(
                "Could not delete absence record due to a database constraint or error.",
                "delete_error_db",
                500,
            )
        except Exception as error:
            db.session.rollback()
            current_app.logger.error(
                f"Unexpected error deleting absence {absence_id}: {error}",
                exc_info=True,
            )
            return internal_err_resp()
