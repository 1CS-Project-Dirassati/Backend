from flask import current_app
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from marshmallow import ValidationError

# from sqlalchemy.orm import joinedload # Not strictly needed for these changes

from app import db
from app.models import Semester, Level  # Level is needed for FK check

from app.utils import (
    err_resp,
    message,
    internal_err_resp,
    validation_error,
)

from .utils import dump_data, load_data  # Assuming these handle SemesterSchema


class SemesterService:

    @staticmethod
    def get_semester_data(semester_id, current_user_id, current_user_role):
        """Get semester data by ID"""
        # Consider adding authorization checks if needed for specific roles beyond basic existence
        semester = Semester.query.get(semester_id)

        if not semester:
            current_app.logger.info(f"Semester with ID {semester_id} not found.")
            return err_resp("Semester not found!", "semester_404", 404)

        try:
            semester_data = dump_data(
                semester
            )  # Assumes dump_data uses SemesterSchema which now includes semester_index
            resp = message(True, "Semester data sent successfully")
            resp["semester"] = semester_data
            current_app.logger.debug(
                f"Successfully retrieved semester ID {semester_id}"
            )
            return resp, 200
        except Exception as error:
            current_app.logger.error(
                f"Error getting semester data for ID {semester_id}: {error}",
                exc_info=True,
            )
            return internal_err_resp()

    @staticmethod
    def get_all_semesters(
        level_id=None,
        semester_index=None,  # ADDED semester_index parameter
        start_date=None,
        end_date=None,
        page=None,
        per_page=None,
        current_user_id=None,  # Kept for consistency, might be used for role-specific filtering later
        current_user_role=None,
    ):
        """Get a list of semesters, filtered and paginated"""
        page = page or 1
        per_page = per_page or 10

        try:
            query = Semester.query
            filters_applied = {}

            if level_id is not None:
                filters_applied["level_id"] = level_id
                query = query.filter(Semester.level_id == level_id)
            if semester_index is not None:  # ADDED filter logic
                filters_applied["semester_index"] = semester_index
                query = query.filter(Semester.semester_index == semester_index)
            if start_date is not None:
                filters_applied["start_date"] = start_date
                # Assuming start_date is a string YYYY-MM-DD, direct comparison should work with date columns
                query = query.filter(Semester.start_date >= start_date)
            if (
                end_date is not None
            ):  # Corrected logic for end_date if it implies semester ends by this date
                filters_applied["end_date"] = end_date
                # This filter might need adjustment based on how 'end_date' is meant to be used.
                # If it means semesters that end on or before this date, you'd need to calculate semester end date.
                # For now, assuming it filters based on the semester's start_date.
                # A more accurate filter would be: query = query.filter(Semester.start_date + timedelta(weeks=Semester.duration) <= end_date)
                # but that requires timedelta and is more complex for a direct query filter here.
                # Sticking to start_date for simplicity unless end_date is strictly defined for the semester model itself.
                query = query.filter(
                    Semester.start_date <= end_date
                )  # Example: semesters that have started by this date

            if filters_applied:
                current_app.logger.debug(
                    f"Applying semester list filters: {filters_applied}"
                )

            query = query.order_by(
                Semester.level_id, Semester.semester_index, Semester.start_date.desc()
            )

            paginated_semesters = query.paginate(
                page=page, per_page=per_page, error_out=False
            )
            current_app.logger.debug(
                f"Paginated semesters items count: {len(paginated_semesters.items)}"
            )

            semesters_data = dump_data(paginated_semesters.items, many=True)
            current_app.logger.debug(f"Serialized {len(semesters_data)} semesters")

            resp = message(True, "Semesters list retrieved successfully")
            resp["semesters"] = semesters_data
            resp["total"] = paginated_semesters.total
            resp["pages"] = paginated_semesters.pages
            resp["current_page"] = paginated_semesters.page
            resp["per_page"] = paginated_semesters.per_page
            resp["has_next"] = paginated_semesters.has_next
            resp["has_prev"] = paginated_semesters.has_prev

            current_app.logger.debug(
                f"Successfully retrieved semesters page {page}. Total: {paginated_semesters.total}"
            )
            return resp, 200

        except Exception as error:
            log_msg = f"Error getting all semesters with filters"
            current_app.logger.error(f"{log_msg}: {error}", exc_info=True)
            return internal_err_resp()

    @staticmethod
    def create_semester(data, current_user_id, current_user_role):
        """Create a new semester, including semester_index."""
        try:
            # Validate foreign key: level_id
            level = Level.query.get(data.get("level_id"))
            if not level:
                current_app.logger.warning(
                    f"Level with ID {data.get('level_id')} not found during semester creation."
                )
                return err_resp(
                    f"Level with ID {data.get('level_id')} not found.",
                    "level_404",
                    400,  # 400 as it's bad input
                )

            # Validate semester_index is positive
            semester_idx = data.get("semester_index")
            if not isinstance(semester_idx, int) or semester_idx <= 0:
                current_app.logger.warning(
                    f"Invalid semester_index provided: {semester_idx}"
                )
                return err_resp(
                    "Semester index must be a positive integer.",
                    "invalid_semester_index",
                    400,
                )

            # Check for uniqueness of (level_id, semester_index)
            existing_semester_by_index = Semester.query.filter_by(
                level_id=data["level_id"], semester_index=semester_idx
            ).first()
            if existing_semester_by_index:
                current_app.logger.warning(
                    f"Semester with level_id {data['level_id']} and semester_index {semester_idx} already exists."
                )
                return err_resp(
                    f"A semester with index {semester_idx} for level {data['level_id']} already exists.",
                    "duplicate_semester_index",
                    409,  # Conflict
                )

            # Check for name uniqueness (optional, but often desired)
            # existing_semester_by_name = Semester.query.filter_by(name=data["name"]).first()
            # if existing_semester_by_name:
            #     return err_resp(
            #         f"Semester with name '{data['name']}' already exists.",
            #         "duplicate_semester_name",
            #         409,
            #     )

            # load_data should use SemesterSchema which now expects semester_index
            new_semester = load_data(
                data
            )  # Assumes SemesterSchema handles all fields including semester_index

            db.session.add(new_semester)
            db.session.commit()
            current_app.logger.info(
                f"Semester created successfully with ID: {new_semester.id}"
            )

            semester_data = dump_data(new_semester)
            resp = message(True, "Semester created successfully.")
            resp["semester"] = semester_data
            return resp, 201

        except ValidationError as err:  # Marshmallow validation error from load_data
            db.session.rollback()
            current_app.logger.warning(
                f"Schema validation error creating semester: {err.messages}. Data: {data}"
            )
            return validation_error(False, err.messages), 400
        except (
            IntegrityError
        ) as error:  # DB integrity error (e.g. unique name if not caught above)
            db.session.rollback()
            current_app.logger.warning(
                f"Database integrity error creating semester: {error}. Data: {data}",
                exc_info=True,
            )
            # Check if it's a name conflict if you have a unique constraint on name
            if "semester_name_key" in str(
                error.orig
            ) or "UNIQUE constraint failed: semester.name" in str(
                error.orig
            ):  # Adjust if your constraint name is different
                return err_resp(
                    f"Semester name '{data.get('name')}' already exists.",
                    "duplicate_semester_name_db",
                    409,
                )
            return internal_err_resp()
        except SQLAlchemyError as error:  # Other DB errors
            db.session.rollback()
            current_app.logger.error(
                f"Database error creating semester: {error}. Data: {data}",
                exc_info=True,
            )
            return internal_err_resp()
        except Exception as error:  # Catch-all for other unexpected errors
            db.session.rollback()
            current_app.logger.error(
                f"Unexpected error creating semester: {error}. Data: {data}",
                exc_info=True,
            )
            return internal_err_resp()

    @staticmethod
    def update_semester(semester_id, data, current_user_id, current_user_role):
        """Update an existing semester, potentially including semester_index."""
        semester = Semester.query.get(semester_id)
        if not semester:
            current_app.logger.info(
                f"Semester with ID {semester_id} not found for update."
            )
            return err_resp("Semester not found!", "semester_404", 404)

        if not data:  # Check if data is empty
            return err_resp(
                "Request body cannot be empty for update.", "empty_update_data", 400
            )

        try:
            # If semester_index is being updated, check for uniqueness with the existing level_id
            if (
                "semester_index" in data
                and data["semester_index"] != semester.semester_index
            ):
                new_semester_idx = data["semester_index"]
                if not isinstance(new_semester_idx, int) or new_semester_idx <= 0:
                    current_app.logger.warning(
                        f"Invalid semester_index for update: {new_semester_idx}"
                    )
                    return err_resp(
                        "Semester index must be a positive integer.",
                        "invalid_semester_index_update",
                        400,
                    )

                existing_semester_check = Semester.query.filter(
                    Semester.level_id == semester.level_id,
                    Semester.semester_index == new_semester_idx,
                    Semester.id
                    != semester_id,  # Exclude the current semester from the check
                ).first()
                if existing_semester_check:
                    current_app.logger.warning(
                        f"Attempt to update semester {semester_id} to semester_index {new_semester_idx} for level {semester.level_id}, which already exists."
                    )
                    return err_resp(
                        f"A semester with index {new_semester_idx} for level {semester.level_id} already exists.",
                        "duplicate_semester_index_update",
                        409,
                    )

            # If name is being updated, check for name uniqueness (optional)
            # if "name" in data and data["name"] != semester.name:
            #     existing_name_check = Semester.query.filter(
            #         Semester.name == data["name"],
            #         Semester.id != semester_id
            #     ).first()
            #     if existing_name_check:
            #         return err_resp(f"Semester name '{data['name']}' already exists.", "duplicate_name_update", 409)

            # Use load_data for partial updates. Ensure SemesterSchema allows partial updates.
            # level_id is typically not updatable for an existing semester.
            # If it were, uniqueness checks for (level_id, semester_index) would be more complex.
            updated_semester = load_data(data, partial=True, instance=semester)
            current_app.logger.debug(
                f"Semester data validated by schema for update. Committing changes for ID: {semester_id}"
            )

            db.session.commit()
            current_app.logger.info(f"Semester ID {semester_id} updated successfully.")

            semester_data = dump_data(updated_semester)
            resp = message(True, "Semester updated successfully.")
            resp["semester"] = semester_data
            return resp, 200

        except ValidationError as err:  # Marshmallow validation error
            db.session.rollback()
            current_app.logger.warning(
                f"Schema validation error updating semester {semester_id}: {err.messages}. Data: {data}"
            )
            return validation_error(False, err.messages), 400
        except IntegrityError as error:  # DB integrity error
            db.session.rollback()
            current_app.logger.warning(
                f"Database integrity error updating semester {semester_id}: {error}. Data: {data}",
                exc_info=True,
            )
            # Add specific checks, e.g., if name has a unique constraint
            if "semester_name_key" in str(
                error.orig
            ) or "UNIQUE constraint failed: semester.name" in str(error.orig):
                return err_resp(
                    f"Semester name '{data.get('name')}' already exists.",
                    "duplicate_semester_name_db_update",
                    409,
                )
            return internal_err_resp()
        except SQLAlchemyError as error:  # Other DB errors
            db.session.rollback()
            current_app.logger.error(
                f"Database error updating semester {semester_id}: {error}. Data: {data}",
                exc_info=True,
            )
            return internal_err_resp()
        except Exception as error:  # Catch-all
            db.session.rollback()
            current_app.logger.error(
                f"Unexpected error updating semester {semester_id}: {error}. Data: {data}",
                exc_info=True,
            )
            return internal_err_resp()

    @staticmethod
    def delete_semester(semester_id, current_user_id, current_user_role):
        """Delete a semester"""
        semester = Semester.query.get(semester_id)
        if not semester:
            current_app.logger.info(
                f"Semester with ID {semester_id} not found for deletion."
            )
            return err_resp("Semester not found!", "semester_404", 404)

        try:
            # Consider implications: if sessions are linked, how should they be handled?
            # Add pre-delete checks if necessary (e.g., if semester has active sessions)
            # For now, assuming direct delete is allowed.
            # Cascade deletes for linked entities (like Modules in this Semester, or Sessions in this Semester)
            # should be configured at the model relationship level (e.g., cascade="all, delete-orphan")
            # or via database ON DELETE CASCADE.

            current_app.logger.warning(
                f"Attempting to delete semester ID {semester_id}."
            )
            db.session.delete(semester)
            db.session.commit()
            current_app.logger.info(f"Semester ID {semester_id} deleted successfully.")
            return None, 204

        except (
            IntegrityError
        ) as error:  # Catch if DB constraints prevent deletion (e.g., linked sessions without cascade)
            db.session.rollback()
            current_app.logger.error(
                f"Integrity error deleting semester {semester_id}: {error}. Possibly due to linked records.",
                exc_info=True,
            )
            return err_resp(
                "Could not delete semester. It may be in use or linked to other records that prevent deletion.",
                "delete_integrity_error",
                409,  # Conflict
            )
        except SQLAlchemyError as error:
            db.session.rollback()
            current_app.logger.error(
                f"Database error deleting semester {semester_id}: {error}",
                exc_info=True,
            )
            return internal_err_resp()  # Or a more specific error
        except Exception as error:
            db.session.rollback()
            current_app.logger.error(
                f"Unexpected error deleting semester {semester_id}: {error}",
                exc_info=True,
            )
            return internal_err_resp()
