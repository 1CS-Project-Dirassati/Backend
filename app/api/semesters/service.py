# Added current_app
from flask import current_app
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from marshmallow import ValidationError
from sqlalchemy.orm import joinedload

# Import DB instance and models
from app import db
from app.models import Semester, Level

# Import shared utilities
from app.utils import (
    err_resp,
    message,
    internal_err_resp,
    validation_error,
)

# Import serialization/deserialization utilities from local utils.py
from .utils import dump_data, load_data


class SemesterService:

    # --- GET Single ---
    @staticmethod
    def get_semester_data(semester_id, current_user_id, current_user_role):
        """Get semester data by ID"""
        semester = Semester.query.get(semester_id)

        if not semester:
            return err_resp("Semester not found!", "semester_404", 404)

        try:
            semester_data = dump_data(semester)
            resp = message(True, "Semester data sent successfully")
            resp["semester"] = semester_data
            return resp, 200
        except Exception as error:
            current_app.logger.error(
                f"Error getting semester data for ID {semester_id}: {error}",
                exc_info=True,
            )
            return internal_err_resp()

    # --- GET List with Filters ---
    @staticmethod
    def get_all_semesters(
        level_id=None,
        start_date=None,
        end_date=None,
        page=None,
        per_page=None,
        current_user_id=None,
        current_user_role=None,
    ):
        """Get a list of semesters, filtered and paginated"""
        page = page or 1
        per_page = per_page or 10

        try:
            query = Semester.query

            # Apply filters
            if level_id is not None:
                query = query.filter(Semester.level_id == level_id)
            if start_date is not None:
                query = query.filter(Semester.start_date >= start_date)
            if end_date is not None:
                query = query.filter(Semester.start_date <= end_date)

            # Add ordering
            query = query.order_by(Semester.start_date.desc())

            # Implement pagination
            paginated_semesters = query.paginate(
                page=page, per_page=per_page, error_out=False
            )

            # Serialize results using dump_data
            semesters_data = dump_data(paginated_semesters.items, many=True)

            resp = message(True, "Semesters list retrieved successfully")
            resp["semesters"] = semesters_data
            resp["total"] = paginated_semesters.total
            resp["pages"] = paginated_semesters.pages
            resp["current_page"] = paginated_semesters.page
            resp["per_page"] = paginated_semesters.per_page
            resp["has_next"] = paginated_semesters.has_next
            resp["has_prev"] = paginated_semesters.has_prev

            return resp, 200

        except Exception as error:
            current_app.logger.error(
                f"Error getting all semesters with filters: {error}",
                exc_info=True,
            )
            return internal_err_resp()

    # --- CREATE ---
    @staticmethod
    def create_semester(data, current_user_id, current_user_role):
        """Create a new semester"""
        try:
            # Check foreign key
            level = Level.query.get(data["level_id"])
            if not level:
                return err_resp(
                    f"Level with ID {data['level_id']} not found.", "level_404", 404
                )

            # Create instance
            new_semester = load_data(data)

            db.session.add(new_semester)
            db.session.commit()

            semester_data = dump_data(new_semester)
            resp = message(True, "Semester created successfully.")
            resp["semester"] = semester_data
            return resp, 201

        except ValidationError as err:
            current_app.logger.warning(
                f"Validation error creating semester: {err.messages}"
            )
            return validation_error(False, err.messages), 400
        except IntegrityError as error:
            db.session.rollback()
            current_app.logger.warning(
                f"Integrity error creating semester: {error}", exc_info=True
            )
            return internal_err_resp()
        except SQLAlchemyError as error:
            db.session.rollback()
            current_app.logger.error(
                f"Database error creating semester: {error}", exc_info=True
            )
            return internal_err_resp()
        except Exception as error:
            db.session.rollback()
            current_app.logger.error(f"Error creating semester: {error}", exc_info=True)
            return internal_err_resp()

    # --- UPDATE ---
    @staticmethod
    def update_semester(semester_id, data, current_user_id, current_user_role):
        """Update an existing semester"""
        semester = Semester.query.get(semester_id)
        if not semester:
            return err_resp("Semester not found!", "semester_404", 404)

        try:
            # Update fields
            if "name" in data:
                semester.name = data["name"]
            if "start_date" in data:
                semester.start_date = data["start_date"]
            if "duration" in data:
                semester.duration = data["duration"]

            db.session.commit()

            semester_data = dump_data(semester)
            resp = message(True, "Semester updated successfully.")
            resp["semester"] = semester_data
            return resp, 200

        except ValidationError as err:
            db.session.rollback()
            current_app.logger.warning(
                f"Validation error updating semester: {err.messages}"
            )
            return validation_error(False, err.messages), 400
        except Exception as error:
            db.session.rollback()
            current_app.logger.error(f"Error updating semester: {error}", exc_info=True)
            return internal_err_resp()

    # --- DELETE ---
    @staticmethod
    def delete_semester(semester_id, current_user_id, current_user_role):
        """Delete a semester"""
        semester = Semester.query.get(semester_id)
        if not semester:
            return err_resp("Semester not found!", "semester_404", 404)

        try:
            db.session.delete(semester)
            db.session.commit()
            return None, 204  # No Content

        except SQLAlchemyError as error:
            db.session.rollback()
            current_app.logger.error(
                f"Database error deleting semester: {error}", exc_info=True
            )
            return err_resp(
                "Could not delete semester due to a database constraint or error.",
                "delete_error_db",
                500,
            )
        except Exception as error:
            db.session.rollback()
            current_app.logger.error(f"Error deleting semester: {error}", exc_info=True)
            return internal_err_resp()
