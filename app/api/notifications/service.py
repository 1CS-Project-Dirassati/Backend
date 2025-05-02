# Added current_app
from flask import current_app
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from marshmallow import ValidationError
from sqlalchemy.orm import joinedload

# Import DB instance and models
from app import db
# Import related models needed for checks and context
from app.models import Notification, Parent, NotificationType # Import Enum

# Import shared utilities
from app.utils import (
    err_resp,
    message,
    internal_err_resp,
    validation_error,
)

# Import serialization/deserialization utilities from local utils.py
from .utils import dump_data, load_data


class NotificationService:

    # --- Helper: Verify Ownership ---
    @staticmethod
    def _verify_parent_ownership(notification: Notification, parent_id: int) -> bool:
        """Checks if the notification belongs to the given parent ID."""
        return notification and notification.parent_id == parent_id

    # --- GET Single (for Parent) ---
    @staticmethod
    # Add type hints
    def get_notification_data(notification_id: int, current_parent_id: int):
        """Get notification data by ID, verifying parent ownership."""
        notification = Notification.query.get(notification_id)

        if not notification:
            current_app.logger.info(f"Notification with ID {notification_id} not found.")
            return err_resp("Notification not found!", "notification_404", 404)

        # --- Ownership Check ---
        if not NotificationService._verify_parent_ownership(notification, current_parent_id):
            current_app.logger.warning(f"Forbidden: Parent {current_parent_id} attempted to access notification {notification_id} belonging to parent {notification.parent_id}.")
            return err_resp(
                "Forbidden: You do not have permission to access this notification.",
                "record_access_denied",
                403,
            )
        current_app.logger.debug(f"Ownership verified for parent {current_parent_id} accessing notification {notification_id}.")

        try:
            notification_data = dump_data(notification)
            resp = message(True, "Notification data sent successfully")
            resp["notification"] = notification_data
            current_app.logger.debug(f"Successfully retrieved notification ID {notification_id}")
            return resp, 200
        except Exception as error:
            current_app.logger.error(
                f"Error serializing notification data for ID {notification_id}: {error}",
                exc_info=True,
            )
            return internal_err_resp()

    # --- GET List (for Parent) ---
    @staticmethod
    # Add type hints
    def get_all_notifications_for_parent(
        parent_id: int, # Explicitly require parent_id for scoping
        is_read=None,
        notification_type=None,
        page=None,
        per_page=None,
    ):
        """Get a paginated list of notifications for a specific parent, filtered."""
        page = page or 1
        per_page = per_page or 15 # Default for notifications

        try:
            # Start query scoped to the parent
            query = Notification.query.filter(Notification.parent_id == parent_id)
            current_app.logger.debug(f"Scoping notifications list for parent ID: {parent_id}")

            # Apply Filters
            filters_applied = {'parent_id': parent_id}
            if is_read is not None:
                filters_applied['is_read'] = is_read
                query = query.filter(Notification.is_read == is_read)
            if notification_type is not None:
                 # Convert string filter to Enum value for query
                 try:
                     type_enum = NotificationType(notification_type.lower())
                     filters_applied['notification_type'] = notification_type
                     query = query.filter(Notification.notification_type == type_enum)
                 except ValueError:
                     # Invalid type provided in filter
                     return err_resp(f"Invalid notification_type filter value: '{notification_type}'. Valid types are: system, payment, attendance, message.", "invalid_filter_type", 400)


            if filters_applied:
                 current_app.logger.debug(f"Applying notification list filters: {filters_applied}")

            # Add ordering (newest first)
            query = query.order_by(Notification.created_at.desc())

            # Implement pagination
            current_app.logger.debug(f"Paginating notifications: page={page}, per_page={per_page}")
            paginated_notifications = query.paginate(page=page, per_page=per_page, error_out=False)
            current_app.logger.debug(f"Paginated notifications items count: {len(paginated_notifications.items)}")

            # Serialize results using dump_data
            notifications_data = dump_data(paginated_notifications.items, many=True)

            current_app.logger.debug(f"Serialized {len(notifications_data)} notifications")
            resp = message(True, "Notifications list retrieved successfully")
            # Add pagination metadata
            resp["notifications"] = notifications_data
            resp["total"] = paginated_notifications.total
            resp["pages"] = paginated_notifications.pages
            resp["current_page"] = paginated_notifications.page
            resp["per_page"] = paginated_notifications.per_page
            resp["has_next"] = paginated_notifications.has_next
            resp["has_prev"] = paginated_notifications.has_prev

            current_app.logger.debug(f"Successfully retrieved notifications page {page} for parent {parent_id}. Total: {paginated_notifications.total}")
            return resp, 200

        except Exception as error:
            log_msg = f"Error getting notifications list for parent {parent_id}"
            if page: log_msg += f", page {page}"
            current_app.logger.error(f"{log_msg}: {error}", exc_info=True)
            return internal_err_resp()

    # --- CREATE (Admin Only via API) ---
    @staticmethod
    # Add type hints
    def create_notification(data: dict, current_user_id: int, current_user_role: str):
        """Creates a notification. Assumes @roles_required('admin') handled authorization."""
        # No role check needed here due to decorator
        try:
            # 1. Schema Validation & Deserialization
            # Using temporary manual load until load_data adjusted/confirmed.
            from app.models.Schemas import NotificationSchema # Temp import
            notification_create_schema = NotificationSchema() # Temp instance
            validated_data = notification_create_schema.load(data)
            # End Temporary block

            parent_id = validated_data['parent_id']
            message_content = validated_data['message']
            notification_type_str = validated_data['notification_type'] # Marshmallow should return the enum by now if schema is set up

            # 2. Validate Parent Exists
            if not Parent.query.get(parent_id):
                 current_app.logger.warning(f"Admin {current_user_id} tried to create notification for non-existent parent ID: {parent_id}")
                 return err_resp(f"Parent with ID {parent_id} not found.", "parent_not_found", 404)

            # 3. Validate Notification Type (already handled by schema if enum validation is correct)
            # Ensure notification_type is the Enum object
            if isinstance(notification_type_str, str): # Fallback if schema didn't convert
                try:
                    notification_type_enum = NotificationType(notification_type_str.lower())
                except ValueError:
                     return err_resp(f"Invalid notification_type: '{notification_type_str}'.", "invalid_notification_type", 400)
            elif isinstance(notification_type_str, NotificationType):
                 notification_type_enum = notification_type_str
            else:
                 return err_resp(f"Invalid notification_type format.", "invalid_notification_type", 400)


            # 4. Create Instance & Commit
            new_notification = load_data(data)
            db.session.add(new_notification)
            db.session.commit()
            current_app.logger.info(f"Notification created successfully with ID: {new_notification.id} for Parent {parent_id} by Admin {current_user_id}")

            # 5. Serialize & Respond
            notification_resp_data = dump_data(new_notification)
            resp = message(True, "Notification created successfully.")
            resp["notification"] = notification_resp_data
            return resp, 201

        except ValidationError as err:
             db.session.rollback()
             current_app.logger.warning(f"Schema validation error creating notification: {err.messages}. Data: {data}")
             return validation_error(False, err.messages), 400
        except SQLAlchemyError as error:
            db.session.rollback()
            current_app.logger.error(f"Database error creating notification: {error}. Data: {data}", exc_info=True)
            return internal_err_resp()
        except Exception as error:
            db.session.rollback()
            current_app.logger.error(f"Unexpected error creating notification: {error}. Data: {data}", exc_info=True)
            return internal_err_resp()


    # --- UPDATE (Parent marking as read/unread) ---
    @staticmethod
    # Add type hints
    def update_notification_read_status(notification_id: int, data: dict, current_parent_id: int):
        """Update the read status of a notification, verifying parent ownership."""
        notification = Notification.query.get(notification_id)

        if not notification:
            current_app.logger.info(f"Attempted update for non-existent notification ID: {notification_id}")
            return err_resp("Notification not found!", "notification_404", 404)

        # --- Ownership Check ---
        if not NotificationService._verify_parent_ownership(notification, current_parent_id):
            current_app.logger.warning(f"Forbidden: Parent {current_parent_id} attempted to update notification {notification_id} belonging to parent {notification.parent_id}.")
            return err_resp(
                "Forbidden: You cannot update this notification.", "update_forbidden", 403
            )

        if 'is_read' not in data:
            current_app.logger.warning(f"Attempted update for notification {notification_id} without 'is_read' field.")
            return err_resp(
                "Request body must contain 'is_read' (boolean) field.", "missing_update_field", 400
            )

        try:
            # 1. Schema Validation (Only is_read)
            # Using temporary manual load until load_data adjusted/confirmed.
            from app.models.Schemas import NotificationSchema # Temp import
            notification_update_schema = NotificationSchema(partial=True, only=("is_read",)) # Temp instance
            validated_data = notification_update_schema.load(data)
            # End Temporary block

            current_app.logger.debug(f"Read status validated by schema for update ID: {notification_id}")

            # 2. Update is_read status
            new_status = validated_data["is_read"]
            if notification.is_read != new_status:
                notification.is_read = new_status
                current_app.logger.info(f"Notification {notification_id} read status updated to {new_status} by parent {current_parent_id}")
                # Commit Changes
                db.session.add(notification) # Add modified object to session
                db.session.commit()
            else:
                 current_app.logger.info(f"Notification {notification_id} read status already {new_status}. No update needed.")


            # 3. Serialize & Respond using dump_data
            notification_resp_data = dump_data(notification)
            resp = message(True, "Notification read status updated successfully.")
            resp["notification"] = notification_resp_data
            return resp, 200

        except ValidationError as err:
            db.session.rollback()
            current_app.logger.warning(f"Schema validation error updating notification {notification_id}: {err.messages}. Data: {data}")
            return validation_error(False, err.messages), 400
        except SQLAlchemyError as error:
             db.session.rollback()
             current_app.logger.error(f"Database error updating notification {notification_id}: {error}. Data: {data}", exc_info=True)
             return internal_err_resp()
        except Exception as error:
            db.session.rollback()
            current_app.logger.error(f"Unexpected error updating notification {notification_id}: {error}. Data: {data}", exc_info=True)
            return internal_err_resp()

    # --- DELETE (Parent deleting their notification) ---
    @staticmethod
    # Add type hint
    def delete_notification(notification_id: int, current_parent_id: int):
        """Delete a notification, verifying parent ownership."""
        notification = Notification.query.get(notification_id)

        if not notification:
            current_app.logger.info(f"Attempted delete for non-existent notification ID: {notification_id}")
            return err_resp("Notification not found!", "notification_404", 404)

        # --- Ownership Check ---
        if not NotificationService._verify_parent_ownership(notification, current_parent_id):
            current_app.logger.warning(f"Forbidden: Parent {current_parent_id} attempted to delete notification {notification_id} belonging to parent {notification.parent_id}.")
            return err_resp(
                "Forbidden: You cannot delete this notification.", "delete_forbidden", 403
            )

        try:
            current_app.logger.warning(f"Parent {current_parent_id} attempting to delete notification {notification_id}.")

            db.session.delete(notification)
            db.session.commit()

            current_app.logger.info(f"Notification {notification_id} deleted successfully by parent {current_parent_id}.")
            return None, 204

        except SQLAlchemyError as error:
            db.session.rollback()
            current_app.logger.error(f"Database error deleting notification {notification_id}: {error}", exc_info=True)
            return err_resp("Could not delete notification due to a database constraint or error.", "delete_error_db", 500)
        except Exception as error:
            db.session.rollback()
            current_app.logger.error(f"Unexpected error deleting notification {notification_id}: {error}", exc_info=True)
            return internal_err_resp()
