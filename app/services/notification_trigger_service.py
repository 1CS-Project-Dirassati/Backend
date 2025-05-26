from flask import current_app  # For logging
from sqlalchemy.exc import SQLAlchemyError

from app.api.notifications.utils import load_data, dump_data
from app import db
from app.models import (
    Notification,
    Parent,
    Student,
    Teacher,
    Admin,
)  # Import all user types

# Import Enum if available and used
try:
    from app.models import NotificationType  # Assuming NotificationType is your Enum
except ImportError:
    NotificationType = None  # Handle gracefully if not defined yet, though it's expected for this service

# Map role strings to model classes for validating recipient existence
RECIPIENT_MODELS = {
    "parent": Parent,
    "student": Student,
    "teacher": Teacher,
    "admin": Admin,
}


class NotificationTriggerService:
    """
    A general-purpose service to trigger and save notifications.
    This service is intended to be called by other services/endpoints within the application.
    """

    @staticmethod
    def trigger_notification(
        recipient_type: str,
        recipient_id: int,
        message: str,
        notification_type_value: str,  # Expecting the string value of the enum
        link: str | None = None,
        created_by_id: (
            int | None
        ) = None,  # Optional: ID of the user/system entity creating it
        created_by_type: str | None = None,  # Optional: Type of the user/system entity
    ) -> Notification | None:
        """
        Creates and saves a new notification.

        Args:
            recipient_type (str): The role/type of the recipient (e.g., 'parent', 'student').
            recipient_id (int): The ID of the recipient.
            message (str): The notification message content.
            notification_type_value (str): The string value of the notification type (e.g., 'payment', 'attendance').
            link (str, optional): An optional URL link associated with the notification.
            created_by_id (int, optional): ID of the entity that triggered this notification.
            created_by_type (str, optional): Type of the entity that triggered this notification.


        Returns:
            Notification: The created Notification object if successful, None otherwise.
        """
        current_app.logger.info(
            f"Attempting to trigger notification for {recipient_type} {recipient_id} of type '{notification_type_value}' with message: '{message[:50]}...'"
        )

        # 1. Validate Recipient Type
        RecipientModel = RECIPIENT_MODELS.get(recipient_type.lower())
        if not RecipientModel:
            current_app.logger.error(
                f"Invalid recipient_type provided: '{recipient_type}'"
            )
            return None

        # 2. Validate Recipient Exists
        # Also check if recipient is archived, if applicable to your user models
        recipient = RecipientModel.query.get(recipient_id)
        if not recipient:
            current_app.logger.error(
                f"Recipient {recipient_type} with ID {recipient_id} not found."
            )
            return None

        # Example: Prevent notifications to archived users (if your user models have 'archived' attribute)
        if hasattr(recipient, "archived") and recipient.archived:
            current_app.logger.warning(
                f"Attempted to send notification to archived {recipient_type} {recipient_id}. Notification not sent."
            )
            return None

        # 3. Validate and Convert Notification Type (Enum)
        actual_notification_type_enum = None
        if NotificationType:  # Check if the Enum is defined and imported
            try:
                actual_notification_type_enum = NotificationType(
                    notification_type_value.lower()
                )
            except ValueError:
                current_app.logger.error(
                    f"Invalid notification_type_value provided: '{notification_type_value}'. "
                    f"Valid types are: {[t.value for t in NotificationType]}"
                )
                return None
        elif (
            notification_type_value
        ):  # If Enum not available, store as string if provided
            actual_notification_type_enum = (
                notification_type_value  # Store as string if Enum not used/found
            )
        else:
            actual_notification_type_enum = (
                None  # Or a default string type like 'general'
            )

        # 4. Create Notification Object
        notification_data = {
            "recipient_type": recipient_type.lower(),  # Ensure lowercase for consistency
            "recipient_id": recipient_id,
            "message": message,
            "type": actual_notification_type_enum,  # This will be the Enum member or string
            "link": link,
            "is_read": False,  # Notifications are unread by default
        }

        new_notification = load_data(notification_data)

        try:
            db.session.add(new_notification)
            db.session.commit()
            current_app.logger.info(
                f"Notification (ID: {new_notification.id}) successfully created for {recipient_type} {recipient_id}."
            )
            return new_notification
        except SQLAlchemyError as e:
            db.session.rollback()
            current_app.logger.error(
                f"Database error while creating notification for {recipient_type} {recipient_id}: {e}",
                exc_info=True,
            )
            return None
        except Exception as e:
            db.session.rollback()  # Should be caught by SQLAlchemyError mostly, but as a safeguard
            current_app.logger.error(
                f"Unexpected error while creating notification for {recipient_type} {recipient_id}: {e}",
                exc_info=True,
            )
            return None
