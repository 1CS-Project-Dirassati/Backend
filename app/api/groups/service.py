from flask import current_app
from sqlalchemy.exc import SQLAlchemyError
from marshmallow import ValidationError

# Import your DB instance and Group model
from app import db
from app.models import Group

# Import shared utilities and the schema
from app.models.Schemas import GroupSchema
from app.utils import (
    err_resp,
    message,
    internal_err_resp,
    validation_error,
)  # Assuming validation_error helper exists

# --- Schema instances FOR VALIDATION (.load) ---
group_create_schema = GroupSchema()
group_update_schema = GroupSchema(partial=True)

# --- Utility for SERIALIZATION (.dump) ---
from .utils import load_data


class GroupService:
    @staticmethod
    def get_group_data(group_id):
        """Get group data by its ID"""
        # (If you added role filtering here before, keep it)
        group = Group.query.get(group_id)
        if not group:
            return err_resp("Group not found!", "group_404", 404)
        try:
            group_data = load_data(group)
            resp = message(True, "Group data sent successfully")
            resp["group"] = group_data
            return resp, 200
        except Exception as error:
            current_app.logger.error(
                f"Error getting group data for ID {group_id}: {error}", exc_info=True
            )
            return internal_err_resp()

    @staticmethod
    # --- Updated to accept optional level_id filter ---
    def get_all_groups(level_id=None):
        """Get a list of all groups, optionally filtered by level_id"""
        try:
            # Start with the base query
            query = Group.query

            # Apply the filter if level_id is provided
            if level_id is not None:
                # Add a filter condition to the query
                query = query.filter(Group.level_id == level_id)  # type: ignore[reportGeneralTypeIssues]
                # Optional: Check if the level_id actually exists?
                # from app.models import Level
                # if not Level.query.get(level_id):
                #     # Return empty list if filtering by non-existent level
                #     # Or you could raise a 404, but empty list is common for filters
                #     resp = message(True, "Level specified in filter not found, returning empty list.")
                #     resp["groups"] = []
                #     return resp, 200 # Or 404 if preferred

            # Add ordering and execute the query
            groups = query.order_by(Group.name).all()  # type: ignore[reportGeneralTypeIssues]

            # Serialize the results
            groups_data = load_data(groups, many=True)
            resp = message(True, "Groups list retrieved successfully")
            resp["groups"] = groups_data
            return resp, 200
        except Exception as error:
            # Log specific error if level_id filter caused it, otherwise generic
            log_msg = f"Error getting all groups"
            if level_id is not None:
                log_msg += f" with level_id filter {level_id}"
            current_app.logger.error(f"{log_msg}: {error}", exc_info=True)
            return internal_err_resp()

    # --- CREATE, UPDATE, DELETE methods remain unchanged ---
    @staticmethod
    def create_group(data):
        """Create a new group after validating input data"""
        try:
            validated_data = group_create_schema.load(data)
            new_group = Group(**validated_data)
            db.session.add(new_group)
            db.session.commit()
            group_data = load_data(new_group)
            resp = message(True, "Group created successfully")
            resp["group"] = group_data
            return resp, 201
        except ValidationError as err:
            current_app.logger.warning(
                f"Validation error creating group: {err.messages}"
            )
            return validation_error(False, err.messages), 400
        except SQLAlchemyError as error:
            db.session.rollback()
            current_app.logger.error(
                f"Database error creating group: {error}", exc_info=True
            )
            return internal_err_resp()
        except Exception as error:
            db.session.rollback()
            current_app.logger.error(f"Error creating group: {error}", exc_info=True)
            return internal_err_resp()

    @staticmethod
    def update_group(group_id, data):
        """Update an existing group by ID after validating input data"""
        group = Group.query.get(group_id)
        if not group:
            return err_resp("Group not found!", "group_404", 404)
        try:
            validated_data = group_update_schema.load(data)
            for key, value in validated_data.items():
                setattr(group, key, value)
            db.session.add(group)
            db.session.commit()
            group_data = load_data(group)
            resp = message(True, "Group updated successfully")
            resp["group"] = group_data
            return resp, 200
        except ValidationError as err:
            db.session.rollback()
            current_app.logger.warning(
                f"Validation error updating group {group_id}: {err.messages}"
            )
            return validation_error(False, err.messages), 400
        except SQLAlchemyError as error:
            db.session.rollback()
            current_app.logger.error(
                f"Database error updating group {group_id}: {error}", exc_info=True
            )
            return internal_err_resp()
        except Exception as error:
            db.session.rollback()
            current_app.logger.error(
                f"Error updating group {group_id}: {error}", exc_info=True
            )
            return internal_err_resp()

    @staticmethod
    def delete_group(group_id):
        """Delete a group by ID"""
        group = Group.query.get(group_id)
        if not group:
            return err_resp("Group not found!", "group_404", 404)
        try:
            db.session.delete(group)
            db.session.commit()
            return None, 204
        except SQLAlchemyError as error:
            db.session.rollback()
            current_app.logger.error(
                f"Database error deleting group {group_id}: {error}", exc_info=True
            )
            return err_resp(
                f"Could not delete group due to a database constraint or error.",
                "delete_error_db",
                500,
            )
        except Exception as error:
            db.session.rollback()
            current_app.logger.error(
                f"Error deleting group {group_id}: {error}", exc_info=True
            )
            return internal_err_resp()
