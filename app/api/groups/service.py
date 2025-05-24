from flask import current_app
from sqlalchemy.exc import SQLAlchemyError
from marshmallow import ValidationError

# Import your DB instance and Group model
from app import db
from app.models import Group, Level  # Import Group and Level models

# Import shared utilities
from app.utils import (
    err_resp,
    message,
    internal_err_resp,
    validation_error,
)

# Import serialization/deserialization utilities
from .utils import dump_data, load_data


class GroupService:
    @staticmethod
    def get_group_data(group_id: int):
        """Get group data by its ID"""
        group = Group.query.get(group_id)
        if not group:
            current_app.logger.info(
                f"Group with ID {group_id} not found."
            )  # Suggestion: Add logging
            return err_resp("Group not found!", "group_404", 404)
        try:
            group_data = dump_data(group)
            resp = message(True, "Group data sent successfully")
            resp["group"] = group_data
            current_app.logger.debug(
                f"Successfully retrieved group ID {group_id}"
            )  # Suggestion: Add logging
            return resp, 200
        except Exception as error:
            current_app.logger.error(
                f"Error serializing group data for ID {group_id}: {error}",
                exc_info=True,
            )
            return internal_err_resp()

    @staticmethod
    def get_all_groups(
        level_id=None, page=None, per_page=None, teacher_id=None
    ):
        """Get a list of all groups, optionally filtered by level_id and paginated."""
        page = page or 1
        per_page = per_page or 10

        try:
            # If teacher_id is provided (from current user), get only their groups
            if teacher_id is not None:
                current_app.logger.debug(
                    f"Getting groups for current teacher (ID: {teacher_id})"
                )
                # Get unique groups from teacher's sessions
                query = Group.query.join(Group.sessions).filter(
                    Group.sessions.any(teacher_id=teacher_id)
                ).distinct()
            else:
                # For non-teachers, get all groups
                query = Group.query

            # Apply the level filter if level_id is provided
            if level_id is not None:
                current_app.logger.debug(
                    f"Filtering groups by level_id: {level_id}"
                )
                level_exists = (
                    db.session.query(Level.id).filter_by(id=level_id).scalar()
                    is not None
                )
                if not level_exists:
                    current_app.logger.info(
                        f"Attempted to filter groups by non-existent level_id: {level_id}"
                    )
                    return err_resp(
                        "Level specified in filter not found", "level_filter_404", 404
                    )

                query = query.filter(Group.level_id == level_id)

            # Add ordering
            query = query.order_by(Group.name)

            # Implement pagination
            current_app.logger.debug(
                f"Paginating groups: page={page}, per_page={per_page}"
            )
            paginated_groups = query.paginate(
                page=page, per_page=per_page, error_out=False
            )
            current_app.logger.debug(
                f"Paginated groups: {paginated_groups.items}"
            )

            # Serialize the results using dump_data
            groups_data = dump_data(
                paginated_groups.items, many=True
            )

            current_app.logger.debug(
                f"Serialized {len(groups_data)} groups"
            )
            resp = message(True, "Groups list retrieved successfully")
            # Add pagination metadata to the response
            resp["groups"] = groups_data
            resp["total"] = paginated_groups.total
            resp["pages"] = paginated_groups.pages
            resp["current_page"] = paginated_groups.page
            resp["per_page"] = paginated_groups.per_page
            resp["has_next"] = paginated_groups.has_next
            resp["has_prev"] = paginated_groups.has_prev

            current_app.logger.debug(
                f"Successfully retrieved groups page {page}. Total: {paginated_groups.total}"
            )
            return resp, 200

        except Exception as error:
            log_msg = f"Error getting groups"
            if level_id is not None:
                log_msg += f" with level_id filter {level_id}"
            if teacher_id is not None:
                log_msg += f" for teacher {teacher_id}"
            if page is not None:
                log_msg += f", page {page}"
            current_app.logger.error(f"{log_msg}: {error}", exc_info=True)
            return internal_err_resp()

    @staticmethod
    def create_group(
        data: dict,
    ):  # -> Tuple[Dict[str, Any], int]: # Suggestion: Add type hints
        """Create a new group after validating input data"""
        try:
            # Use load_data utility for validation and deserialization
            # No partial=True needed for creation

            if not Level.query.get(data["level_id"]):  # Check if level_id exists
                raise ValidationError(
                    {"level_id": ["Level ID does not exist."]},
                    field_names=["level_id"],
                )

            new_group = load_data(data)  # Use util, no instance needed

            # print("this happens 5") # Suggestion: Replace print with logging
            # current_app.logger.debug(f"Group data validated successfully. Adding to session.") # Suggestion: Add logging

            db.session.add(new_group)
            db.session.commit()
            # current_app.logger.info(f"Group created successfully with ID: {new_group.id}") # Suggestion: Add logging

            # Use dump_data utility for serialization
            group_data = dump_data(new_group)
            resp = message(True, "Group created successfully")
            resp["group"] = group_data
            return resp, 201

        except ValidationError as err:
            db.session.rollback()  # Ensure rollback on validation error too
            current_app.logger.warning(
                f"Validation error creating group: {err.messages}. Data: {data}"
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
            current_app.logger.error(
                f"Unexpected error creating group: {error}", exc_info=True
            )
            return internal_err_resp()

    @staticmethod
    def update_group(
        group_id: int, data: dict
    ):  # -> Tuple[Dict[str, Any], int]: # Suggestion: Add type hints
        """Update an existing group by ID after validating input data"""
        group = Group.query.get(group_id)
        if not group:
            current_app.logger.info(
                f"Attempted to update non-existent group ID: {group_id}"
            )  # Suggestion: Add logging
            return err_resp("Group not found!", "group_404", 404)

        try:
            # Use load_data utility for validation and deserialization into the existing instance
            # Pass partial=True and the group instance
            updated_group = load_data(
                data, partial=True, instance=group
            )  # Use util with instance loading

            current_app.logger.debug(
                f"Group data validated successfully for update. Committing changes for ID: {group_id}"
            )  # Suggestion: Add logging

            db.session.commit()
            current_app.logger.info(
                f"Group updated successfully for ID: {group_id}"
            )  # Suggestion: Add logging

            # Use dump_data utility for serialization
            group_data = dump_data(updated_group)
            resp = message(True, "Group updated successfully")
            resp["group"] = group_data
            return resp, 200

        except ValidationError as err:
            db.session.rollback()
            current_app.logger.warning(
                f"Validation error updating group {group_id}: {err.messages}. Data: {data}"
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
                f"Unexpected error updating group {group_id}: {error}", exc_info=True
            )
            return internal_err_resp()

    @staticmethod
    def delete_group(group_id: int):
        """Delete a group by ID"""
        group = Group.query.get(group_id)
        if not group:
            current_app.logger.info(
                f"Attempted to delete non-existent group ID: {group_id}"
            )  # Suggestion: Add logging
            return err_resp("Group not found!", "group_404", 404)
        try:
            current_app.logger.debug(
                f"Deleting group ID: {group_id}"
            )  # Suggestion: Add logging
            db.session.delete(group)
            db.session.commit()
            current_app.logger.info(
                f"Group deleted successfully: ID {group_id}"
            )  # Suggestion: Add logging
            return None, 204
        except SQLAlchemyError as error:
            db.session.rollback()
            # Check for specific constraint violation if possible/needed
            if "FOREIGN KEY constraint failed" in str(error):
                current_app.logger.warning(
                    f"Attempted to delete group {group_id} with existing dependencies: {error}"
                )
                return err_resp(
                    "Cannot delete group. It may have associated students or other dependencies.",
                    "delete_conflict",
                    409,
                )
            current_app.logger.error(
                f"Database error deleting group {group_id}: {error}", exc_info=True
            )
            return err_resp(
                f"Could not delete group due to a database error.",  # Simplified message
                "delete_error_db",
                409,
            )
        except Exception as error:
            db.session.rollback()
            current_app.logger.error(
                f"Unexpected error deleting group {group_id}: {error}", exc_info=True
            )
            return internal_err_resp()
