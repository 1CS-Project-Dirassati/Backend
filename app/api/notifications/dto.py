from flask_restx import Namespace, fields
from flask_restx.reqparse import RequestParser
# Import the Enum to use its values in choices
from app.models import NotificationType # Adjust import path if necessary

# Get the Enum values for the choices parameter
notification_type_choices = [t.value for t in NotificationType]

class NotificationDto:
    """Data Transfer Objects and Request Parsers for the Notification API."""

    # Define the namespace
    api = Namespace("notification", description="Parent notification related operations.") # Singular resource name

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
        "notification_type",
        type=str, # Pass as string
        location="args",
        required=False,
        choices=notification_type_choices, # Add choices for Swagger UI
        help="Filter notifications by type.", # Simplified help
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
        default=15, # Default number of notifications per page
        help="Number of items per page (default: 15).",
    )

    # Define the core 'notification' object model
    notification = api.model(
        "Notification Object",
        {
            "id": fields.Integer(readonly=True, description="Notification unique identifier"),
            "parent_id": fields.Integer(required=True, readonly=True, description="ID of the parent recipient"),
            "message": fields.String(required=True, readonly=True, description="Content of the notification"),
            "notification_type": fields.String(required=True, readonly=True, description="Type of notification", enum=notification_type_choices), # Use enum for choices
            "is_read": fields.Boolean(required=True, description="Indicates if the notification has been read"),
            "created_at": fields.DateTime(readonly=True, description="Timestamp when the notification was created (UTC)"),
        },
    )

    # Standard response for a single notification
    data_resp = api.model(
        "Notification Data Response",
        {
            "status": fields.Boolean(description="Indicates success or failure"),
            "message": fields.String(description="Response message"),
            "notification": fields.Nested(notification, description="The notification data"),
        },
    )

    # Standard response for a list of notifications (includes pagination)
    list_data_resp = api.model(
        "Notification List Response",
        {
            "status": fields.Boolean(description="Indicates success or failure"),
            "message": fields.String(description="Response message"),
            "notifications": fields.List(fields.Nested(notification), description="List of notification data"),
            "total": fields.Integer(description="Total number of notifications matching the query"),
            "pages": fields.Integer(description="Total number of pages"),
            "current_page": fields.Integer(description="The current page number"),
            "per_page": fields.Integer(description="Number of items per page"),
            "has_next": fields.Boolean(description="True if there is a next page"),
            "has_prev": fields.Boolean(description="True if there is a previous page"),
        },
    )

    # --- DTOs for POST/PATCH ---
    # Added notification_create_input
    notification_create_input = api.model(
        "Notification Create Input (Admin)",
        {
            "parent_id": fields.Integer(required=True, description="ID of the parent recipient"),
            "message": fields.String(required=True, description="Content of the notification"),
            "notification_type": fields.String(required=True, description="Type of notification", enum=notification_type_choices), # Use enum for choices
            # is_read defaults to False
        }
    )

    notification_update_input = api.model(
        "Notification Update Input (Parent)", # Clarified user role
        {
            "is_read": fields.Boolean(required=True, description="Set the read status (true or false)"),
            # Only is_read can be updated by the parent
        },
    )
