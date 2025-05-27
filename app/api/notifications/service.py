from flask import current_app
from typing import cast, Optional  # Added Optional
from sqlalchemy.exc import SQLAlchemyError

# from marshmallow import ValidationError # Keep if other methods use DTOs that might raise this
from sqlalchemy import func

from app import db
from app.models import Notification, User  # User needed for recipient check
from app.models import NotificationType  # Import the Enum

from app.utils import err_resp, message, internal_err_resp, validation_error
from .utils import (
    dump_data,
)  # load_data might not be needed here if trigger service is robust

# Import the NotificationTriggerService
from app.services.notification_trigger_service import NotificationTriggerService


class NotificationApiService:

    @staticmethod
    def _verify_ownership(
        notification: Notification, recipient_id: int, recipient_type: str
    ) -> bool:
        # recipient_id is User.id
        return cast(
            "bool",
            notification
            and notification.recipient_id == recipient_id
            and notification.recipient_type == recipient_type,
        )

    @staticmethod
    def get_notification_data(
        notification_id: int, current_user_id: int, current_user_role: str
    ):
        # current_user_id is User.id
        notification = Notification.query.get(notification_id)
        if not notification:
            return err_resp("Notification not found!", "notification_404", 404)

        if not NotificationApiService._verify_ownership(
            notification, current_user_id, current_user_role
        ):
            return err_resp(
                "Forbidden: You do not have permission to access this notification.",
                "record_access_denied",
                403,
            )
        try:
            notification_data = dump_data(
                notification
            )  # dump_data uses NotificationSchema
            resp = message(True, "Notification data sent successfully")
            resp["notification"] = notification_data
            return resp, 200
        except Exception as error:
            current_app.logger.error(
                f"Error serializing notification data for ID {notification_id}: {error}",
                exc_info=True,
            )
            return internal_err_resp()

    @staticmethod
    def get_my_notifications(
        recipient_type: str,
        recipient_id: int,
        is_read: Optional[bool] = None,  # Made explicit Optional
        notification_type_filter_str: Optional[
            str
        ] = None,  # Renamed from notification_type
        page: Optional[int] = None,
        per_page: Optional[int] = None,
    ):
        page = page or 1
        per_page = per_page or 15
        try:
            query = Notification.query.filter(
                Notification.recipient_type == recipient_type,
                Notification.recipient_id == recipient_id,  # recipient_id is User.id
            )
            if is_read is not None:
                query = query.filter(Notification.is_read == is_read)

            if notification_type_filter_str is not None and NotificationType:
                try:
                    type_enum_val = NotificationType(
                        notification_type_filter_str.lower()
                    )
                    # Filter by the main Enum field Notification.notification_type
                    query = query.filter(
                        Notification.notification_type == type_enum_val
                    )
                except ValueError:
                    valid_types = ", ".join([t.value for t in NotificationType])
                    return err_resp(
                        f"Invalid notification_type filter: '{notification_type_filter_str}'. Valid: {valid_types}.",
                        "invalid_filter_notification_type",
                        400,
                    )

            query = query.order_by(Notification.created_at.desc())
            paginated_notifications = query.paginate(
                page=page, per_page=per_page, error_out=False
            )
            # dump_data uses NotificationSchema which now includes 'notification_type' correctly
            notifications_data = dump_data(paginated_notifications.items, many=True)

            resp = message(True, "Notifications list retrieved successfully")
            resp.update(
                {
                    "notifications": notifications_data,
                    "total": paginated_notifications.total,
                    "pages": paginated_notifications.pages,
                    "current_page": paginated_notifications.page,
                    "per_page": paginated_notifications.per_page,
                    "has_next": paginated_notifications.has_next,
                    "has_prev": paginated_notifications.has_prev,
                }
            )
            return resp, 200
        except Exception as error:
            current_app.logger.error(
                f"Error getting notifications list for User {recipient_id} ({recipient_type}): {error}",
                exc_info=True,
            )
            return internal_err_resp()

    @staticmethod
    def create_notification_by_admin(data: dict):
        """
        Handles an Admin's API request to create a notification.
        The 'notification_type' (Enum) will be defaulted to SYSTEM.
        Input `data` DTO should contain: recipient_type, recipient_id, message, link (optional).
        """
        recipient_type_str = data.get("recipient_type")
        recipient_id_val = data.get("recipient_id")  # This is User.id
        message_content = data.get("message")
        link_url = data.get("link")

        # Default the main notification_type (Enum) to SYSTEM for admin-created notifications
        # The NotificationType Enum must be imported.
        if not NotificationType:
            current_app.logger.error(
                "NotificationType Enum not available for defaulting in create_notification_by_admin."
            )
            return internal_err_resp(
                message="Server configuration error: Notification types unavailable."
            )

        default_notification_enum_value = (
            NotificationType.SYSTEM.value
        )  # e.g., "system"

        current_app.logger.info(
            f"Admin creating notification for {recipient_type_str} {recipient_id_val}. "
            f"Message: '{message_content[:50]}...'. Link: '{link_url}'. "
            f"Defaulting NotificationType (Enum) to: '{default_notification_enum_value}'."
        )

        if not all([recipient_type_str, recipient_id_val, message_content]):
            return err_resp(
                "Missing required fields: recipient_type, recipient_id, or message.",
                "missing_fields_admin_create_notification",
                400,
            )

        try:
            recipient_id_int = int(recipient_id_val)
            if not User.query.get(recipient_id_int):  # Validate User.id exists
                current_app.logger.warning(
                    f"Admin create notification: Recipient User ID {recipient_id_int} not found."
                )
                return err_resp(
                    f"Recipient User ID {recipient_id_int} not found.",
                    "recipient_user_not_found",
                    404,
                )
        except (ValueError, TypeError):
            current_app.logger.warning(
                f"Admin create notification: Invalid recipient_id format '{recipient_id_val}'."
            )
            return err_resp(
                f"Invalid recipient_id format: '{recipient_id_val}'.",
                "invalid_recipient_id_format",
                400,
            )

        # Call the NotificationTriggerService
        # The optional string 'type' field is gone from model, so no optional_type_string param.
        created_notification_obj = NotificationTriggerService.trigger_notification(
            recipient_type=recipient_type_str,
            recipient_id=recipient_id_int,
            message=message_content,
            notification_type_value=default_notification_enum_value,  # Pass the string value of the Enum
            link=link_url,
        )

        if created_notification_obj:
            # dump_data uses NotificationSchema which now includes 'notification_type' correctly
            notification_resp_data = dump_data(created_notification_obj)
            resp = message(True, "Notification created successfully by Admin.")
            resp["notification"] = notification_resp_data
            return resp, 201
        else:
            return err_resp(
                "Failed to create notification via trigger service. Check service logs.",
                "notification_trigger_failed",
                400,
            )

    @staticmethod
    def update_notification_read_status(
        notification_id: int, data: dict, current_user_id: int, current_user_role: str
    ):
        # current_user_id is User.id
        notification = Notification.query.get(notification_id)
        if not notification:
            return err_resp("Notification not found!", "notification_404_update", 404)
        if not NotificationApiService._verify_ownership(
            notification, current_user_id, current_user_role
        ):
            return err_resp(
                "Forbidden: You cannot update this notification.",
                "update_forbidden",
                403,
            )

        if "is_read" not in data or not isinstance(data["is_read"], bool):
            return err_resp(
                "Invalid input: 'is_read' (boolean) is required.",
                "invalid_is_read_payload",
                400,
            )
        try:
            new_status = data["is_read"]
            if notification.is_read != new_status:
                notification.is_read = new_status
                db.session.commit()
            notification_resp_data = dump_data(notification)
            resp = message(True, "Notification read status updated successfully.")
            resp["notification"] = notification_resp_data
            return resp, 200
        except Exception as error:
            db.session.rollback()
            current_app.logger.error(
                f"Error updating notification {notification_id} read status: {error}",
                exc_info=True,
            )
            return internal_err_resp()

    @staticmethod
    def delete_notification(
        notification_id: int, current_user_id: int, current_user_role: str
    ):
        # current_user_id is User.id
        notification = Notification.query.get(notification_id)
        if not notification:
            return err_resp("Notification not found!", "notification_404_delete", 404)
        if not NotificationApiService._verify_ownership(
            notification, current_user_id, current_user_role
        ):
            return err_resp(
                "Forbidden: You cannot delete this notification.",
                "delete_forbidden",
                403,
            )
        try:
            db.session.delete(notification)
            db.session.commit()
            return None, 204
        except Exception as error:
            db.session.rollback()
            current_app.logger.error(
                f"Error deleting notification {notification_id}: {error}", exc_info=True
            )
            return internal_err_resp()

    @staticmethod
    def mark_all_as_read(current_user_id: int, current_user_role: str):
        # current_user_id is User.id
        try:
            update_count = Notification.query.filter(
                Notification.recipient_type == current_user_role,
                Notification.recipient_id == current_user_id,
                Notification.is_read == False,
            ).update({"is_read": True}, synchronize_session="fetch")
            db.session.commit()
            return (
                message(True, f"{update_count or 0} notifications marked as read."),
                200,
            )
        except Exception as error:
            db.session.rollback()
            current_app.logger.error(
                f"Error marking all notifications read for User {current_user_id} ({current_user_role}): {error}",
                exc_info=True,
            )
            return internal_err_resp()

    @staticmethod
    def get_unread_count(current_user_id: int, current_user_role: str):
        # current_user_id is User.id
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
            return {"status": True, "unread_count": unread_count or 0}, 200
        except Exception as error:
            current_app.logger.error(
                f"Error getting unread count for User {current_user_id} ({current_user_role}): {error}",
                exc_info=True,
            )
            return internal_err_resp()
