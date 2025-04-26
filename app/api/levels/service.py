from flask import current_app
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from marshmallow import ValidationError

# Import DB instance and Level model
from app import db
from app.models import Level

# Import shared utilities and the schema CLASS
from app.models.Schemas import LevelSchema
from app.utils import err_resp, message, internal_err_resp, validation_error

# --- Schema instances FOR VALIDATION (.load) ---
level_create_schema = LevelSchema()  # Schema for creating
level_update_schema = LevelSchema(partial=True)  # Schema for updating

# --- Utility for SERIALIZATION (.dump) ---
from .utils import load_data


class LevelService:
    @staticmethod
    def get_level_data(level_id):
        """Get level data by its ID"""
        level = Level.query.get(level_id)
        if not level:
            return err_resp("Level not found!", "level_404", 404)
        try:
            level_data = load_data(level)
            resp = message(True, "Level data sent successfully")
            resp["level"] = level_data
            return resp, 200
        except Exception as error:
            current_app.logger.error(
                f"Error getting level data for ID {level_id}: {error}", exc_info=True
            )
            return internal_err_resp()

    @staticmethod
    def get_all_levels():
        """Get a list of all levels"""
        try:
            levels = Level.query.order_by(Level.name).all()
            levels_data = load_data(levels, many=True)
            resp = message(True, "Levels list retrieved successfully")
            resp["levels"] = levels_data
            return resp, 200
        except Exception as error:
            current_app.logger.error(
                f"Error getting all levels: {error}", exc_info=True
            )
            return internal_err_resp()

    # --- CREATE ---
    @staticmethod
    def create_level(data):
        """Create a new level after validating input data"""
        try:
            validated_data = level_create_schema.load(data)
            new_level = Level(**validated_data)

            db.session.add(new_level)
            db.session.commit()

            level_data = load_data(new_level)
            resp = message(True, "Level created successfully")
            resp["level"] = level_data
            return resp, 201  # 201 Created

        except ValidationError as err:
            current_app.logger.warning(
                f"Validation error creating level: {err.messages}"
            )
            return validation_error(False, err.messages), 400
        except (
            IntegrityError
        ) as error:  # Catch unique constraint violations (e.g., duplicate name)
            db.session.rollback()
            current_app.logger.warning(
                f"Integrity error creating level: {error}", exc_info=True
            )
            # Check if the error is related to the unique name constraint
            if "level_name_key" in str(
                error
            ) or "UNIQUE constraint failed: level.name" in str(error):
                return err_resp(
                    f"Level name '{data.get('name')}' already exists.",
                    "duplicate_name",
                    409,
                )  # 409 Conflict
            return internal_err_resp(
            )  # Generic integrity error
        except SQLAlchemyError as error:
            db.session.rollback()
            current_app.logger.error(
                f"Database error creating level: {error}", exc_info=True
            )
            return internal_err_resp()
        except Exception as error:
            db.session.rollback()
            current_app.logger.error(f"Error creating level: {error}", exc_info=True)
            return internal_err_resp()

    # --- UPDATE ---
    @staticmethod
    def update_level(level_id, data):
        """Update an existing level by ID after validating input data"""
        level = Level.query.get(level_id)
        if not level:
            return err_resp("Level not found!", "level_404", 404)

        if not data:  # Handle empty request body
            return err_resp(
                "Request body cannot be empty for update.", "empty_update_data", 400
            )

        try:
            validated_data = level_update_schema.load(data)

            # Update the model fields using the validated data dictionary
            for key, value in validated_data.items():
                setattr(level, key, value)

            db.session.add(level)
            db.session.commit()

            level_data = load_data(level)
            resp = message(True, "Level updated successfully")
            resp["level"] = level_data
            return resp, 200  # 200 OK

        except ValidationError as err:
            db.session.rollback()
            current_app.logger.warning(
                f"Validation error updating level {level_id}: {err.messages}"
            )
            return validation_error(False, err.messages), 400
        except (
            IntegrityError
        ) as error:  # Catch unique constraint violations (e.g., duplicate name)
            db.session.rollback()
            current_app.logger.warning(
                f"Integrity error updating level {level_id}: {error}", exc_info=True
            )
            if "level_name_key" in str(
                error
            ) or "UNIQUE constraint failed: level.name" in str(error):
                return err_resp(
                    f"Level name '{data.get('name')}' already exists.",
                    "duplicate_name",
                    409,
                )  # 409 Conflict
            return internal_err_resp(
            )  # Generic integrity error
        except SQLAlchemyError as error:
            db.session.rollback()
            current_app.logger.error(
                f"Database error updating level {level_id}: {error}", exc_info=True
            )
            return internal_err_resp()
        except Exception as error:
            db.session.rollback()
            current_app.logger.error(
                f"Error updating level {level_id}: {error}", exc_info=True
            )
            return internal_err_resp()

    # --- DELETE ---
    @staticmethod
    def delete_level(level_id):
        """Delete a level by ID"""
        level = Level.query.get(level_id)
        if not level:
            return err_resp("Level not found!", "level_404", 404)

        try:
            # Check for dependencies before deleting (important!)
            if (
                level.groups
                or level.students
                or level.module_associations
                or level.semesters
            ):
                # Construct a more informative message based on what exists
                dependencies = []
                if level.groups:
                    dependencies.append("groups")
                if level.students:
                    dependencies.append("students")
                if level.module_associations:
                    dependencies.append("teaching units")
                if level.semesters:
                    dependencies.append("semesters")
                return err_resp(
                    f"Cannot delete level: It is associated with existing {', '.join(dependencies)}.",
                    "delete_conflict",
                    409,
                )  # 409 Conflict

            db.session.delete(level)
            db.session.commit()
            return None, 204  # 204 No Content

        except SQLAlchemyError as error:
            db.session.rollback()
            current_app.logger.error(
                f"Database error deleting level {level_id}: {error}", exc_info=True
            )
            # Could be a constraint error if cascade is not set up perfectly or other DB issue
            return err_resp(
                f"Could not delete level due to a database constraint or error.",
                "delete_error_db",
                500,
            )
        except Exception as error:
            db.session.rollback()
            current_app.logger.error(
                f"Error deleting level {level_id}: {error}", exc_info=True
            )
            return internal_err_resp()
