from flask_restx import Namespace, fields
from flask_restx.reqparse import RequestParser

# Import the NotificationType Enum directly
try:
    from app.models import NotificationType

    notification_type_enum_choices = [t.value for t in NotificationType]
except ImportError:
    notification_type_enum_choices = [
        "system",
        "payment",
        "absence",
        "grade",
        "message",
    ]  # Fallback


class NotificationDto:
    """Data Transfer Objects and Request Parsers for the Notification API."""

    api = Namespace(
        "notifications", description="Notification related operations for users."
    )

    # --- Parser for Query Parameters (Filters and Pagination) ---
    notification_filter_parser = RequestParser(bundle_errors=True)
    notification_filter_parser.add_argument(
        "is_read",
        type=bool,
        location="args",
        required=False,
        help="Filter notifications by read status (true/false).",
    )
    notification_filter_parser.add_argument(
        "notification_type",  # Changed from "type" to "notification_type" for clarity
        type=str,
        location="args",
        required=False,
        choices=notification_type_enum_choices,  # Use enum values for choices
        help=f"Filter by notification type. Valid types: {', '.join(notification_type_enum_choices)}.",
    )
    notification_filter_parser.add_argument(
        "page",
        type=int,
        location="args",
        required=False,
        default=1,
        help="Page number for pagination (default: 1).",
    )
    notification_filter_parser.add_argument(
        "per_page",
        type=int,
        location="args",
        required=False,
        default=15,
        help="Number of items per page (default: 15).",
    )

    # Define the core 'notification' object model
    notification = api.model(
        "Notification Object",
        {
            "id": fields.Integer(
                readonly=True, description="Notification unique identifier"
            ),
            "recipient_type": fields.String(
                required=True,
                readonly=True,
                description="Role of the recipient (e.g., parent, admin)",
            ),
            "recipient_id": fields.Integer(
                required=True,
                readonly=True,
                description="ID of the recipient user (User.id)",
            ),
            "notification_type": fields.String(  # Changed from 'type' to 'notification_type'
                required=True,
                readonly=True,
                description="Type of the notification (e.g., system, grade)",
                enum=notification_type_enum_choices,  # Document possible enum values
            ),
            "message": fields.String(
                required=True, readonly=True, description="Content of the notification"
            ),
            "link": fields.String(
                readonly=True,
                description="Optional frontend link related to the notification",
            ),
            "is_read": fields.Boolean(
                required=True, description="Indicates if the notification has been read"
            ),
            "created_at": fields.DateTime(
                readonly=True,
                description="Timestamp when the notification was created (UTC)",
            ),
            "updated_at": fields.DateTime(
                readonly=True,
                description="Timestamp when the notification was last updated (e.g., read) (UTC)",
            ),
        },
    )

    # Standard response for a single notification
    data_resp = api.model(
        "Notification Data Response",
        {
            "status": fields.Boolean(description="Indicates success or failure"),
            "message": fields.String(description="Response message"),
            "notification": fields.Nested(
                notification, description="The notification data"
            ),
        },
    )

    # Standard response for a list of notifications (includes pagination)
    list_data_resp = api.model(
        "Notification List Response",
        {
            "status": fields.Boolean(description="Indicates success or failure"),
            "message": fields.String(description="Response message"),
            "notifications": fields.List(
                fields.Nested(notification), description="List of notification data"
            ),
            "total": fields.Integer(
                description="Total number of notifications matching the query"
            ),
            "pages": fields.Integer(description="Total number of pages"),
            "current_page": fields.Integer(description="The current page number"),
            "per_page": fields.Integer(description="Number of items per page"),
            "has_next": fields.Boolean(description="True if there is a next page"),
            "has_prev": fields.Boolean(description="True if there is a previous page"),
        },
    )

    # DTO for Admin creating a notification
    # 'notification_type' is NO LONGER expected from the admin in the request body.
    notification_create_input = api.model(
        "Notification Create Input (Admin)",
        {
            "recipient_type": fields.String(
                required=True,
                description="Role of the recipient (e.g., parent, student, teacher, admin)",
                example="student",
            ),
            "recipient_id": fields.Integer(
                required=True, description="User ID of the recipient", example=101
            ),
            "message": fields.String(
                required=True,
                description="Content of the notification",
                example="Your report is ready.",
            ),
            "link": fields.String(
                required=False,  # Link is optional
                description="Optional frontend link related to the notification",
                example="/reports/123",
            ),
            # 'notification_type' field is removed from input, will be defaulted by the service.
            "type": fields.String(
                required=False,
                description="Type of the notification (e.g., system, grade). Defaults to 'system'.",
                example="system",
                default="system",  # Default value if not provided
            ),
        },
    )

    # Update input remains the same (only targets is_read)
    notification_update_input = api.model(
        "Notification Update Input",
        {
            "is_read": fields.Boolean(
                required=True, description="Set the read status (true or false)"
            ),
        },
    )

    # DTO for Unread Count
    unread_count_resp = api.model(
        "Unread Count Response",
        {
            "status": fields.Boolean(default=True),
            "unread_count": fields.Integer(
                required=True, description="Number of unread notifications"
            ),
        },
    )
