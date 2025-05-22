from flask import current_app
from typing import cast
from sqlalchemy.exc import SQLAlchemyError
from marshmallow import ValidationError  # Keep for create/update validation
from sqlalchemy import func  # For count

# Import DB instance and models (assuming Notification model uses polymorphic fields now)
from app import db
from app.models import (
    Notification,
    Parent,
    Student,
    Teacher,
    Admin,
)  # Import all user types

# Import Enum if available
try:
    from app.models import NotificationType
except ImportError:
    NotificationType = None  # Handle gracefully if not defined yet


# Import shared utilities
from app.utils import err_resp, message, internal_err_resp, validation_error

# Import serialization/deserialization utilities from local utils.py
from .utils import dump_data, load_data


# Map role strings to model classes for validation during creation
RECIPIENT_MODELS = {
    "parent": Parent,
    "student": Student,
    "teacher": Teacher,
    "admin": Admin,
}


# Renamed service to reflect its role handling API requests
class NotificationApiService:

    # --- Helper: Verify Ownership (Polymorphic) ---
    @staticmethod
    def _verify_ownership(
        notification: Notification, recipient_id: int, recipient_type: str
    ) -> bool:
        """Checks if the notification belongs to the given recipient."""
        return cast(
            "bool",
            notification
            and notification.recipient_id == recipient_id
            and notification.recipient_type == recipient_type,
        )

    # --- GET Single (Polymorphic) ---
    @staticmethod
    def get_notification_data(
        notification_id: int, current_user_id: int, current_user_role: str
    ):
        """Get notification data by ID, verifying ownership."""
        notification = Notification.query.get(notification_id)

        if not notification:
            current_app.logger.info(
                f"Notification with ID {notification_id} not found."
            )
            return err_resp("Notification not found!", "notification_404", 404)

        # --- Ownership Check ---
        if not NotificationApiService._verify_ownership(
            notification, current_user_id, current_user_role
        ):
            current_app.logger.warning(
                f"Forbidden: User {current_user_id} ({current_user_role}) attempted to access notification {notification_id} belonging to {notification.recipient_type} {notification.recipient_id}."
            )
            return err_resp(
                "Forbidden: You do not have permission to access this notification.",
                "record_access_denied",
                403,
            )

        current_app.logger.debug(
            f"Ownership verified for user {current_user_id} ({current_user_role}) accessing notification {notification_id}."
        )

        try:
            notification_data = dump_data(notification)
            resp = message(True, "Notification data sent successfully")
            resp["notification"] = notification_data
            current_app.logger.debug(
                f"Successfully retrieved notification ID {notification_id}"
            )
            return resp, 200
        except Exception as error:
            current_app.logger.error(
                f"Error serializing notification data for ID {notification_id}: {error}",
                exc_info=True,
            )
            return internal_err_resp()

    # --- GET List (Polymorphic - for /me route) ---
    @staticmethod
    def get_my_notifications(
        recipient_type: str,
        recipient_id: int,
        is_read=None,
        notification_type=None,  # Parameter name matches DTO parser ('type')
        page=None,
        per_page=None,
    ):
        """Get a paginated list of notifications for a specific user, filtered."""
        page = page or 1
        per_page = per_page or 15

        try:
            # Start query scoped to the specific user
            current_app.logger.debug(
                f"Starting notifications query for User {recipient_id} ({recipient_type})"
            )
            query = Notification.query.filter(
                Notification.recipient_type == recipient_type,
                Notification.recipient_id == recipient_id,
            )

            # Apply Filters
            filters_applied = {
                "recipient_type": recipient_type,
                "recipient_id": recipient_id,
            }
            if is_read is not None:
                filters_applied["is_read"] = is_read
                query = query.filter(Notification.is_read == is_read)

            if (
                notification_type is not None and NotificationType
            ):  # Check if enum is available
                # Convert string filter to Enum value for query
                try:
                    type_enum = NotificationType(notification_type.lower())
                    filters_applied["type"] = notification_type
                    query = query.filter(Notification.type == type_enum)
                except ValueError:
                    valid_types = ", ".join([t.value for t in NotificationType])
                    return err_resp(
                        f"Invalid type filter value: '{notification_type}'. Valid types are: {valid_types}.",
                        "invalid_filter_type",
                        400,
                    )
            elif (
                notification_type is not None
            ):  # If enum not available, filter by string
                filters_applied["type"] = notification_type
                query = query.filter(Notification.type == notification_type)

            if len(filters_applied) > 2:  # More than just recipient filters
                current_app.logger.debug(
                    f"Applying notification list filters: {filters_applied}"
                )

            # Add ordering (newest first)
            query = query.order_by(Notification.created_at.desc())

            # Implement pagination
            current_app.logger.debug(
                f"Paginating notifications: page={page}, per_page={per_page}"
            )
            paginated_notifications = query.paginate(
                page=page, per_page=per_page, error_out=False
            )
            current_app.logger.debug(
                f"Paginated notifications items count: {len(paginated_notifications.items)}"
            )

            # Serialize results
            notifications_data = dump_data(paginated_notifications.items, many=True)

            current_app.logger.debug(
                f"Serialized {len(notifications_data)} notifications"
            )
            resp = message(True, "Notifications list retrieved successfully")
            # Add pagination metadata
            resp["notifications"] = notifications_data
            resp["total"] = paginated_notifications.total
            resp["pages"] = paginated_notifications.pages
            resp["current_page"] = paginated_notifications.page
            resp["per_page"] = paginated_notifications.per_page
            resp["has_next"] = paginated_notifications.has_next
            resp["has_prev"] = paginated_notifications.has_prev

            current_app.logger.debug(
                f"Successfully retrieved notifications page {page} for User {recipient_id} ({recipient_type}). Total: {paginated_notifications.total}"
            )
            return resp, 200

        except Exception as error:
            log_msg = f"Error getting notifications list for User {recipient_id} ({recipient_type})"
            if page:
                log_msg += f", page {page}"
            current_app.logger.error(f"{log_msg}: {error}", exc_info=True)
            return internal_err_resp()

    # --- CREATE (Admin Only via API - Polymorphic) ---
    @staticmethod
    def create_notification_by_admin(data: dict):
        """Creates a notification by an Admin. Assumes @roles_required('admin') handled authorization."""
        try:
            # 1. Schema Validation & Deserialization (using load_data)
            # load_data uses NotificationSchema which should handle enum conversion if set up
            new_notification = load_data(
                data
            )  # Create new instance from validated data

            recipient_type = new_notification.recipient_type
            recipient_id = new_notification.recipient_id

            # 2. Validate Recipient Exists
            RecipientModel = RECIPIENT_MODELS.get(recipient_type)
            if not RecipientModel:
                return err_resp(
                    f"Invalid recipient_type: '{recipient_type}'.",
                    "invalid_recipient_type",
                    400,
                )
            if not RecipientModel.query.get(recipient_id):
                current_app.logger.warning(
                    f"Admin tried to create notification for non-existent {recipient_type} ID: {recipient_id}"
                )
                return err_resp(
                    f"{recipient_type.capitalize()} with ID {recipient_id} not found.",
                    f"{recipient_type}_not_found",
                    404,
                )

            # 3. Validate Notification Type (Enum)
            # This should be handled by Marshmallow schema if NotificationSchema.type uses fields.Enum
            if NotificationType and not isinstance(
                new_notification.type, NotificationType
            ):
                # Fallback check if schema didn't enforce Enum properly
                try:
                    if new_notification.type:  # Check if a type string was provided
                        new_notification.type = NotificationType(
                            str(new_notification.type).lower()
                        )
                    # If type was None/empty, leave it as None in DB
                except (ValueError, TypeError):
                    return err_resp(
                        f"Invalid notification type provided: '{new_notification.type}'.",
                        "invalid_notification_type",
                        400,
                    )

            # 4. Commit (new_notification instance already has data from load_data)
            db.session.add(new_notification)
            db.session.commit()
            current_app.logger.info(
                f"Notification created successfully with ID: {new_notification.id} for {recipient_type} {recipient_id} by Admin."
            )

            # 5. Serialize & Respond
            notification_resp_data = dump_data(new_notification)
            resp = message(True, "Notification created successfully.")
            resp["notification"] = notification_resp_data
            return resp, 201

        except ValidationError as err:
            db.session.rollback()
            current_app.logger.warning(
                f"Schema validation error creating notification: {err.messages}. Data: {data}"
            )
            return validation_error(False, err.messages), 400
        except SQLAlchemyError as error:
            db.session.rollback()
            current_app.logger.error(
                f"Database error creating notification: {error}. Data: {data}",
                exc_info=True,
            )
            return internal_err_resp()
        except Exception as error:
            db.session.rollback()
            current_app.logger.error(
                f"Unexpected error creating notification: {error}. Data: {data}",
                exc_info=True,
            )
            return internal_err_resp()

    # --- UPDATE (Marking as read/unread - Polymorphic) ---
    @staticmethod
    def update_notification_read_status(
        notification_id: int, data: dict, current_user_id: int, current_user_role: str
    ):
        """Update the read status of a notification, verifying ownership."""
        notification = Notification.query.get(notification_id)

        if not notification:
            current_app.logger.info(
                f"Attempted update for non-existent notification ID: {notification_id}"
            )
            return err_resp("Notification not found!", "notification_404", 404)

        # --- Ownership Check ---
        if not NotificationApiService._verify_ownership(
            notification, current_user_id, current_user_role
        ):
            current_app.logger.warning(
                f"Forbidden: User {current_user_id} ({current_user_role}) attempted to update notification {notification_id} belonging to {notification.recipient_type} {notification.recipient_id}."
            )
            return err_resp(
                "Forbidden: You cannot update this notification.",
                "update_forbidden",
                403,
            )

        # Use load_data for validation and applying partial update
        try:
            # Validate and load 'is_read' into the existing instance
            updated_notification = load_data(data, partial=True, instance=notification)
            new_status = updated_notification.is_read  # Get the validated status

            current_app.logger.debug(
                f"Read status validated by schema for update ID: {notification_id}"
            )

            # Check if status actually changed to avoid unnecessary commit
            if notification.is_read != new_status:
                # No need to set notification.is_read = new_status; load_data did it
                current_app.logger.info(
                    f"Notification {notification_id} read status updated to {new_status} by User {current_user_id} ({current_user_role})"
                )
                db.session.commit()  # Commit the change applied by load_data
            else:
                current_app.logger.info(
                    f"Notification {notification_id} read status already {new_status}. No update needed."
                )

            # Serialize & Respond
            notification_resp_data = dump_data(updated_notification)
            resp = message(True, "Notification read status updated successfully.")
            resp["notification"] = notification_resp_data
            return resp, 200

        except ValidationError as err:
            db.session.rollback()
            current_app.logger.warning(
                f"Schema validation error updating notification {notification_id}: {err.messages}. Data: {data}"
            )
            # Check if error is specifically about 'is_read' field
            if "is_read" in err.messages:
                return err_resp(
                    "Request body must contain 'is_read' (boolean) field.",
                    "missing_or_invalid_field",
                    400,
                )
            else:
                return (
                    validation_error(False, err.messages),
                    400,
                )  # Other validation issues
        except SQLAlchemyError as error:
            db.session.rollback()
            current_app.logger.error(
                f"Database error updating notification {notification_id}: {error}. Data: {data}",
                exc_info=True,
            )
            return internal_err_resp()
        except Exception as error:
            db.session.rollback()
            current_app.logger.error(
                f"Unexpected error updating notification {notification_id}: {error}. Data: {data}",
                exc_info=True,
            )
            return internal_err_resp()

    # --- DELETE (Polymorphic) ---
    @staticmethod
    def delete_notification(
        notification_id: int, current_user_id: int, current_user_role: str
    ):
        """Delete a notification, verifying ownership."""
        notification = Notification.query.get(notification_id)

        if not notification:
            current_app.logger.info(
                f"Attempted delete for non-existent notification ID: {notification_id}"
            )
            return err_resp("Notification not found!", "notification_404", 404)

        # --- Ownership Check ---
        if not NotificationApiService._verify_ownership(
            notification, current_user_id, current_user_role
        ):
            current_app.logger.warning(
                f"Forbidden: User {current_user_id} ({current_user_role}) attempted to delete notification {notification_id} belonging to {notification.recipient_type} {notification.recipient_id}."
            )
            return err_resp(
                "Forbidden: You cannot delete this notification.",
                "delete_forbidden",
                403,
            )

        try:
            current_app.logger.warning(
                f"User {current_user_id} ({current_user_role}) attempting to delete notification {notification_id}."
            )
            db.session.delete(notification)
            db.session.commit()
            current_app.logger.info(
                f"Notification {notification_id} deleted successfully by User {current_user_id} ({current_user_role})."
            )
            return None, 204

        except SQLAlchemyError as error:
            db.session.rollback()
            current_app.logger.error(
                f"Database error deleting notification {notification_id}: {error}",
                exc_info=True,
            )
            return err_resp(
                "Could not delete notification due to a database constraint or error.",
                "delete_error_db",
                500,
            )
        except Exception as error:
            db.session.rollback()
            current_app.logger.error(
                f"Unexpected error deleting notification {notification_id}: {error}",
                exc_info=True,
            )
            return internal_err_resp()

    # --- Mark All As Read ---
    @staticmethod
    def mark_all_as_read(current_user_id: int, current_user_role: str):
        """Marks all unread notifications for the current user as read."""
        try:
            update_count = Notification.query.filter(
                Notification.recipient_type == current_user_role,
                Notification.recipient_id == current_user_id,
                Notification.is_read == False,
            ).update(
                {"is_read": True}
            )  # Use synchronize_session=False if issues arise

            db.session.commit()
            current_app.logger.info(
                f"Marked {update_count} notifications as read for User {current_user_id} ({current_user_role})."
            )
            return message(True, f"{update_count} notifications marked as read."), 200

        except SQLAlchemyError as error:
            db.session.rollback()
            current_app.logger.error(
                f"Database error marking all notifications read for User {current_user_id} ({current_user_role}): {error}",
                exc_info=True,
            )
            return internal_err_resp()
        except Exception as error:
            db.session.rollback()
            current_app.logger.error(
                f"Unexpected error marking all notifications read for User {current_user_id} ({current_user_role}): {error}",
                exc_info=True,
            )
            return internal_err_resp()

    # --- Get Unread Count ---
    @staticmethod
    def get_unread_count(current_user_id: int, current_user_role: str):
        """Gets the count of unread notifications for the current user."""
        try:
            unread_count = (
                db.session.query(func.count(Notification.id))
                .filter(
                    Notification.recipient_type == current_user_role,
                    Notification.recipient_id == current_user_id,
                    Notification.is_read == False,
                )
                .scalar()
            )

            current_app.logger.debug(
                f"Unread notification count for User {current_user_id} ({current_user_role}): {unread_count}"
            )
            return {"status": True, "unread_count": unread_count or 0}, 200

        except Exception as error:
            current_app.logger.error(
                f"Error getting unread count for User {current_user_id} ({current_user_role}): {error}",
                exc_info=True,
            )
            return internal_err_resp()
