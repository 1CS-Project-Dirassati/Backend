from flask import current_app
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from marshmallow import ValidationError

# Import DB instance and Level model
from app import db
from app.models import Level  # Keep Level model import

# Import shared utilities
from app.utils import (
    err_resp,
    message,
    internal_err_resp,
    validation_error,
)

# Import serialization/deserialization utilities from local utils.py
from .utils import dump_data, load_data  # Use local utils


class LevelService:
    @staticmethod
    def get_level_data(
        level_id: int,
    ):  # -> Tuple[Dict[str, Any], int]: # Suggestion: Add type hints
        """Get level data by its ID"""
        level = Level.query.get(level_id)
        if not level:
            current_app.logger.info(
                f"Level with ID {level_id} not found."
            )  # Add logging
            return err_resp("Level not found!", "level_404", 404)
        try:
            # Use dump_data for serialization
            level_data = dump_data(level)
            resp = message(True, "Level data sent successfully")
            resp["level"] = level_data
            current_app.logger.debug(
                f"Successfully retrieved level ID {level_id}"
            )  # Add logging
            return resp, 200
        except Exception as error:
            current_app.logger.error(
                f"Error serializing level data for ID {level_id}: {error}",
                exc_info=True,  # Update log message
            )
            return internal_err_resp()

    @staticmethod
    def get_all_levels(
        page=None, per_page=None
    ):  # -> Tuple[Dict[str, Any], int]: # Suggestion: Add type hints
        """Get a list of all levels, paginated."""
        page = page or 1  # Ensure page defaults to 1 if None
        per_page = per_page or 10  # Get per_page from config or default

        try:
            query = Level.query

            # Add ordering
            query = query.order_by(Level.name)

            # Implement pagination
            current_app.logger.debug(
                f"Paginating levels: page={page}, per_page={per_page}"
            )  # Add logging
            paginated_levels = query.paginate(
                page=page, per_page=per_page, error_out=False
            )
            current_app.logger.debug(
                f"Paginated levels items count: {len(paginated_levels.items)}"
            )  # Add logging

            # Serialize the results using dump_data
            levels_data = dump_data(
                paginated_levels.items, many=True
            )  # Use .items for paginated list

            current_app.logger.debug(
                f"Serialized {len(levels_data)} levels"
            )  # Add logging
            resp = message(True, "Levels list retrieved successfully")
            # Add pagination metadata to the response
            resp["levels"] = levels_data
            resp["total"] = paginated_levels.total
            resp["pages"] = paginated_levels.pages
            resp["current_page"] = paginated_levels.page
            resp["per_page"] = paginated_levels.per_page
            resp["has_next"] = paginated_levels.has_next
            resp["has_prev"] = paginated_levels.has_prev

            current_app.logger.debug(
                f"Successfully retrieved levels page {page}. Total: {paginated_levels.total}"
            )  # Add logging
            return resp, 200

        except Exception as error:
            log_msg = f"Error getting levels"
            if page is not None:
                log_msg += f", page {page}"
            current_app.logger.error(f"{log_msg}: {error}", exc_info=True)
            return internal_err_resp()

    # --- CREATE ---
    @staticmethod
    def create_level(
        data: dict,
    ):  # -> Tuple[Dict[str, Any], int]: # Suggestion: Add type hints
        """Create a new level after validating input data"""
        try:
            # Use load_data utility for validation and deserialization
            new_level = load_data(data)  # Use util, no instance needed

            current_app.logger.debug(
                f"Level data validated successfully. Adding to session."
            )  # Add logging

            db.session.add(new_level)
            db.session.commit()
            current_app.logger.info(
                f"Level created successfully with ID: {new_level.id}"
            )  # Add logging

            # Use dump_data utility for serialization
            level_data = dump_data(new_level)
            resp = message(True, "Level created successfully")
            resp["level"] = level_data
            return resp, 201

        except ValidationError as err:
            db.session.rollback()  # Ensure rollback on validation error too
            current_app.logger.warning(
                f"Validation error creating level: {err.messages}. Data: {data}"
            )
            return validation_error(False, err.messages), 400
        except IntegrityError as error:
            db.session.rollback()
            current_app.logger.warning(
                f"Integrity error creating level: {error}. Data: {data}",
                exc_info=True,  # Log data
            )
            if "level_name_key" in str(
                error.orig  # Access original DBAPI error if needed
            ) or "UNIQUE constraint failed: level.name" in str(error.orig):
                return err_resp(
                    f"Level name '{data.get('name')}' already exists.",
                    "duplicate_name",
                    409,
                )
            return internal_err_resp()
        except SQLAlchemyError as error:
            db.session.rollback()
            current_app.logger.error(
                f"Database error creating level: {error}. Data: {data}",
                exc_info=True,  # Log data
            )
            return internal_err_resp()
        except Exception as error:
            db.session.rollback()
            current_app.logger.error(
                f"Unexpected error creating level: {error}. Data: {data}", exc_info=True
            )  # Log data
            return internal_err_resp()

    # --- UPDATE ---
    @staticmethod
    def update_level(
        level_id: int, data: dict
    ):  # -> Tuple[Dict[str, Any], int]: # Suggestion: Add type hints
        """Update an existing level by ID after validating input data"""
        level = Level.query.get(level_id)
        if not level:
            current_app.logger.info(
                f"Attempted to update non-existent level ID: {level_id}"
            )  # Add logging
            return err_resp("Level not found!", "level_404", 404)

        if not data:
            current_app.logger.warning(
                f"Attempted update for level {level_id} with empty data."
            )  # Add logging
            return err_resp(
                "Request body cannot be empty for update.", "empty_update_data", 400
            )

        try:
            # Use load_data utility for validation and deserialization into the existing instance
            # Pass partial=True and the level instance
            updated_level = load_data(
                data, partial=True, instance=level
            )  # Use util with instance loading

            current_app.logger.debug(
                f"Level data validated successfully for update. Committing changes for ID: {level_id}"
            )  # Add logging

            # db.session.add(updated_level) # Not strictly necessary when modifying instance loaded in session
            db.session.commit()
            current_app.logger.info(
                f"Level updated successfully for ID: {level_id}"
            )  # Add logging

            # Use dump_data utility for serialization
            level_data = dump_data(updated_level)
            resp = message(True, "Level updated successfully")
            resp["level"] = level_data
            return resp, 200

        except ValidationError as err:
            db.session.rollback()
            current_app.logger.warning(
                f"Validation error updating level {level_id}: {err.messages}. Data: {data}"
            )
            return validation_error(False, err.messages), 400
        except IntegrityError as error:
            db.session.rollback()
            current_app.logger.warning(
                f"Integrity error updating level {level_id}: {error}. Data: {data}",
                exc_info=True,  # Log data
            )
            if "level_name_key" in str(
                error.orig  # Access original DBAPI error if needed
            ) or "UNIQUE constraint failed: level.name" in str(error.orig):
                return err_resp(
                    f"Level name '{data.get('name', level.name)}' already exists.",  # Show attempted name
                    "duplicate_name",
                    409,
                )
            return internal_err_resp()
        except SQLAlchemyError as error:
            db.session.rollback()
            current_app.logger.error(
                f"Database error updating level {level_id}: {error}. Data: {data}",
                exc_info=True,  # Log data
            )
            return internal_err_resp()
        except Exception as error:
            db.session.rollback()
            current_app.logger.error(
                f"Unexpected error updating level {level_id}: {error}. Data: {data}",
                exc_info=True,  # Log data
            )
            return internal_err_resp()

    # --- DELETE ---
    @staticmethod
    def delete_level(
        level_id: int,
    ):  # -> Tuple[None, int]: # Suggestion: Add type hints
        """Delete a level by ID"""
        level = Level.query.get(level_id)
        if not level:
            current_app.logger.info(
                f"Attempted to delete non-existent level ID: {level_id}"
            )  # Add logging
            return err_resp("Level not found!", "level_404", 404)

        try:
            # Check for dependencies before deleting
            # Adjust based on actual relationships defined in Level model
            dependencies = []
            if (
                hasattr(level, "groups") and level.groups
            ):  # Check if relationship exists and has items
                dependencies.append("groups")
            if hasattr(level, "students") and level.students:
                dependencies.append("students")
            if hasattr(level, "module_associations") and level.module_associations:
                dependencies.append("teaching units")
            if hasattr(level, "semesters") and level.semesters:
                dependencies.append("semesters")
            # Add other relevant dependencies if they exist

            if dependencies:
                dependency_str = ", ".join(dependencies)
                current_app.logger.warning(
                    f"Attempted to delete level {level_id} with existing dependencies: {dependency_str}"
                )
                return err_resp(
                    f"Cannot delete level: It is associated with existing {dependency_str}.",
                    "delete_conflict",
                    409,
                )

            current_app.logger.debug(f"Deleting level ID: {level_id}")  # Add logging
            db.session.delete(level)
            db.session.commit()
            current_app.logger.info(
                f"Level deleted successfully: ID {level_id}"
            )  # Add logging
            return None, 204

        except SQLAlchemyError as error:
            db.session.rollback()
            # More specific error checking could be added here if needed
            current_app.logger.error(
                f"Database error deleting level {level_id}: {error}", exc_info=True
            )
            return err_resp(
                f"Could not delete level due to a database error.",  # Simplified message
                "delete_error_db",
                500,  # Use 500 for generic DB error during delete
            )
        except Exception as error:
            db.session.rollback()
            current_app.logger.error(
                f"Unexpected error deleting level {level_id}: {error}", exc_info=True
            )
            return internal_err_resp()
