from flask_restx import Namespace, fields
from flask_restx.reqparse import RequestParser

# Assuming Enum is defined in models, adjust path if needed
# from app.models import NotificationType

# Placeholder if NotificationType enum isn't available yet
# notification_type_choices = ["system", "payment", "attendance", "message", "grade", "application_submitted"]
# Real implementation should fetch from Enum:
try:
    from app.models import NotificationType

    notification_type_choices = [t.value for t in NotificationType]
except ImportError:
    print("Warning: NotificationType enum not found, using placeholder choices.")
    notification_type_choices = [
        "system",
        "payment",
        "attendance",
        "message",
        "grade",
        "application_submitted",
    ]


class NotificationDto:
    """Data Transfer Objects and Request Parsers for the Notification API."""

    # Updated namespace description
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
        "type",
        type=str,
        location="args",
        required=False,  # Renamed to 'type' for consistency
        choices=notification_type_choices,  # Use choices if enum is available
        help="Filter notifications by type.",
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

    # Define the core 'notification' object model (using polymorphic fields)
    notification = api.model(
        "Notification Object",
        {
            "id": fields.Integer(
                readonly=True, description="Notification unique identifier"
            ),
            # Replaced parent_id with polymorphic fields
            "recipient_type": fields.String(
                required=True,
                readonly=True,
                description="Role of the recipient (e.g., parent, admin)",
            ),
            "recipient_id": fields.Integer(
                required=True, readonly=True, description="ID of the recipient user"
            ),
            "message": fields.String(
                required=True, readonly=True, description="Content of the notification"
            ),
            "link": fields.String(
                readonly=True,
                description="Optional frontend link related to the notification",
            ),  # Added link
            # Renamed notification_type to type
            "type": fields.String(
                required=False,
                readonly=True,
                description="Type/category of notification",
                enum=notification_type_choices,
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
            ),  # Added updated_at
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

    # --- DTOs for POST/PATCH ---
    # Updated create input to be polymorphic
    notification_create_input = api.model(
        "Notification Create Input (Admin)",
        {
            "recipient_type": fields.String(
                required=True,
                description="Role of the recipient (e.g., parent, student, teacher, admin)",
            ),
            "recipient_id": fields.Integer(
                required=True, description="ID of the recipient user"
            ),
            "message": fields.String(
                required=True, description="Content of the notification"
            ),
            "link": fields.String(
                required=False,
                description="Optional frontend link related to the notification",
            ),
            "type": fields.String(
                required=False,
                description="Type/category of notification",
                enum=notification_type_choices,
            ),
            # is_read defaults to False
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

    # --- NEW DTO for Unread Count ---
    unread_count_resp = api.model(
        "Unread Count Response",
        {
            "status": fields.Boolean(default=True),
            "unread_count": fields.Integer(
                required=True, description="Number of unread notifications"
            ),
        },
    )
