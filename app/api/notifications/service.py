from flask import current_app
from typing import cast
from sqlalchemy.exc import SQLAlchemyError
from marshmallow import ValidationError
from sqlalchemy import func

from app import db
from app.models import Notification, Parent, Student, Teacher, Admin

try:
    from app.models import NotificationType
except ImportError:
    NotificationType = None

from app.utils import err_resp, message, internal_err_resp, validation_error
from .utils import (
    dump_data,
    load_data,
)  # Assuming load_data is not strictly needed for create_by_admin if trigger service takes raw args

# Import the new trigger service
from app.services.notification_trigger_service import (
    NotificationTriggerService,
)  # Adjust path if needed

# RECIPIENT_MODELS map is now primarily used by NotificationTriggerService,
# but can be kept here if NotificationApiService still does direct validation for other reasons.
# For create_notification_by_admin, this validation is now delegated.
# RECIPIENT_MODELS = {
#     "parent": Parent,
#     "student": Student,
#     "teacher": Teacher,
#     "admin": Admin,
# }


class NotificationApiService:

    @staticmethod
    def _verify_ownership(
        notification: Notification, recipient_id: int, recipient_type: str
    ) -> bool:
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
            notification_data = dump_data(notification)
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
        is_read=None,
        notification_type=None,
        page=None,
        per_page=None,
    ):
        page = page or 1
        per_page = per_page or 15
        try:
            query = Notification.query.filter(
                Notification.recipient_type == recipient_type,
                Notification.recipient_id == recipient_id,
            )
            if is_read is not None:
                query = query.filter(Notification.is_read == is_read)
            if notification_type is not None and NotificationType:
                try:
                    type_enum = NotificationType(notification_type.lower())
                    query = query.filter(Notification.type == type_enum)
                except ValueError:
                    valid_types = ", ".join([t.value for t in NotificationType])
                    return err_resp(
                        f"Invalid type filter value: '{notification_type}'. Valid types are: {valid_types}.",
                        "invalid_filter_type",
                        400,
                    )
            elif notification_type is not None:
                query = query.filter(Notification.type == notification_type)

            query = query.order_by(Notification.created_at.desc())
            paginated_notifications = query.paginate(
                page=page, per_page=per_page, error_out=False
            )
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
    def create_notification_by_admin(
        data: dict,
    ):  # Data comes from notification_create_input DTO
        """
        Handles an Admin's API request to create a notification.
        Uses the NotificationTriggerService for the actual creation logic.
        """
        # The input `data` is already validated by `api.expect(notification_create_input)`
        # It contains: recipient_type, recipient_id, message, link (optional), type (optional string value)

        recipient_type_str = data.get("recipient_type")
        recipient_id_val = data.get("recipient_id")
        message_content = data.get("message")
        notification_type_str = data.get("type")  # This is the string value from DTO
        link_url = data.get("link")

        # Basic validation that core fields are present (DTO should ensure this, but good defense)
        if not all([recipient_type_str, recipient_id_val, message_content]):
            return err_resp(
                "Missing required fields: recipient_type, recipient_id, or message.",
                "missing_fields_admin_create_notification",
                400,
            )

        # Call the new trigger service
        # The trigger service handles validation of recipient existence and notification_type string to Enum.
        if (
            not recipient_type_str
            or not recipient_id_val
            or not message_content
            or not notification_type_str
            or not link_url
        ):
            return err_resp(
                "Missing required fields: recipient_type, recipient_id, message, type, or link.",
                "missing_fields_admin_create_notification",
                400,
            )

        created_notification = NotificationTriggerService.trigger_notification(
            recipient_type=recipient_type_str,
            recipient_id=recipient_id_val,
            message=message_content,
            notification_type_value=notification_type_str,  # Pass the string value
            link=link_url,
            # created_by_id could be the admin's ID if you want to log who used the API
            # created_by_id = get_jwt_identity() # If needed
        )

        if created_notification:
            notification_resp_data = dump_data(created_notification)
            resp = message(True, "Notification created successfully by Admin.")
            resp["notification"] = notification_resp_data
            return resp, 201
        else:
            # Errors would have been logged by NotificationTriggerService.
            # Determine a more specific error based on what trigger_notification might imply by returning None.
            # For now, a generic error. Could check if recipient was not found based on logs.
            # The NotificationTriggerService now handles specific error logging for recipient not found etc.
            # So, if it returns None, it implies a failure during the trigger process.
            return err_resp(
                "Failed to create notification. Check logs for details (e.g., invalid recipient or type).",
                "notification_trigger_failed",
                400,  # Or 500 if it's an internal trigger service failure
            )

    @staticmethod
    def update_notification_read_status(
        notification_id: int, data: dict, current_user_id: int, current_user_role: str
    ):
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

        # `data` is expected to be like {"is_read": true/false} from notification_update_input DTO
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
                current_app.logger.info(
                    f"Notification {notification_id} read status updated to {new_status}"
                )
            else:
                current_app.logger.info(
                    f"Notification {notification_id} read status already {new_status}. No update."
                )

            notification_resp_data = dump_data(notification)
            resp = message(True, "Notification read status updated successfully.")
            resp["notification"] = notification_resp_data
            return resp, 200
        except Exception as error:
            db.session.rollback()
            current_app.logger.error(
                f"Error updating notification {notification_id}: {error}", exc_info=True
            )
            return internal_err_resp()

    @staticmethod
    def delete_notification(
        notification_id: int, current_user_id: int, current_user_role: str
    ):
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
        try:
            update_count = Notification.query.filter(
                Notification.recipient_type == current_user_role,
                Notification.recipient_id == current_user_id,
                Notification.is_read == False,
            ).update(
                {"is_read": True}, synchronize_session="fetch"
            )  # synchronize_session strategy
            db.session.commit()
            return (
                message(True, f"{update_count or 0} notifications marked as read."),
                200,
            )
        except Exception as error:
            db.session.rollback()
            current_app.logger.error(
                f"Error marking all notifications read for User {current_user_id}: {error}",
                exc_info=True,
            )
            return internal_err_resp()

    @staticmethod
    def get_unread_count(current_user_id: int, current_user_role: str):
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
                f"Error getting unread count for User {current_user_id}: {error}",
                exc_info=True,
            )
            return internal_err_resp()
