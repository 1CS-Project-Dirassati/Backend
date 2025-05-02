# Added current_app
from flask import request, current_app
from flask_restx import Resource
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt

# Import shared extensions/decorators
from app.extensions import limiter
from app.api.decorators import roles_required

# Import notification-specific modules
from .service import NotificationService
from .dto import NotificationDto

# Get the API namespace and DTOs
api = NotificationDto.api
data_resp = NotificationDto.data_resp
list_data_resp = NotificationDto.list_data_resp
notification_create_input = NotificationDto.notification_create_input # Added create input DTO
notification_update_input = NotificationDto.notification_update_input
# Get the filter/pagination parser
notification_filter_parser = NotificationDto.notification_filter_parser


# --- Helper to get current user info ---
def get_current_user_info():
    user_id = get_jwt_identity()
    claims = get_jwt()
    role = claims.get("role")
    # Assuming the user_id in JWT for a parent *is* the parent.id
    current_app.logger.debug(f"Current user info: ID={user_id}, Role={role}")
    return user_id, role


# --- Route for listing/creating notifications ---
@api.route("/")
class NotificationList(Resource):

    @api.doc(
        "List my notifications",
        security="Bearer",
        parser=notification_filter_parser,
        description="Get a paginated list of notifications for the currently logged-in parent. Filterable by read status and notification type.",
        responses={
            200: ("Success", list_data_resp),
            401: "Unauthorized",
            403: "Forbidden (Not a parent)",
            429: "Too Many Requests",
            500: "Internal Server Error",
        },
    )
    @jwt_required()
    @roles_required("parent") # Only parents can see their notifications via this route
    # Use config for rate limit
    @limiter.limit(lambda: current_app.config.get("RATE_LIMIT_NOTIFICATION_LIST", "60/minute"))
    def get(self):
        """Get a list of my notifications"""
        user_id, role = get_current_user_info() # user_id is parent_id
        args = notification_filter_parser.parse_args()
        current_app.logger.debug(f"Received GET request for parent {user_id}'s notifications list with args: {args}")

        # Service scopes results to the current_user_id (parent_id)
        return NotificationService.get_all_notifications_for_parent(
            parent_id=user_id, # Pass parent_id for clarity and scoping
            is_read=args.get("is_read"),
            notification_type=args.get("notification_type"),
            page=args.get('page'),
            per_page=args.get('per_page'),
        )

    # --- ADDED POST ENDPOINT FOR ADMIN ---
    @api.doc(
        "Create a notification (Admin Only)",
        security="Bearer",
        description="Create a notification targeted at a specific parent (Admin access required).",
        responses={
            201: ("Created", data_resp),
            400: "Validation Error/Invalid Data",
            401: "Unauthorized",
            403: "Forbidden (Not Admin)",
            404: "Not Found (Parent not found)",
            429: "Too Many Requests",
            500: "Internal Server Error",
        },
    )
    @api.expect(notification_create_input, validate=True)
    @jwt_required()
    @roles_required("admin") # Only admins can create notifications via API
    # Use config for rate limit
    @limiter.limit(lambda: current_app.config.get("RATE_LIMIT_NOTIFICATION_ADMIN_CREATE", "20/minute"))
    def post(self):
        """Create a new notification (Admin only)"""
        data = request.get_json()
        # Service handles validation and creation
        user_id = get_jwt_identity()
        current_app.logger.debug(f"Received POST request by Admin {user_id} to create notification with data: {data}")
        role = get_jwt()["role"]
        return NotificationService.create_notification(data, user_id, role)


# --- Route for specific notification operations (for the logged-in parent) ---
@api.route("/<int:notification_id>")
@api.param("notification_id", "The unique identifier of the notification")
class NotificationResource(Resource):

    @api.doc(
        "Get a specific notification by ID",
        security="Bearer",
        description="Get data for a specific notification belonging to the logged-in parent.",
        responses={
            200: ("Success", data_resp),
            401: "Unauthorized",
            403: "Forbidden (Not parent or not owner)",
            404: "Not Found",
            429: "Too Many Requests",
            500: "Internal Server Error",
        },
    )
    @jwt_required()
    @roles_required("parent") # Only parents access their specific notifications
    # Use config for rate limit
    @limiter.limit(lambda: current_app.config.get("RATE_LIMIT_NOTIFICATION_GET", "100/minute"))
    # Add type hint
    def get(self, notification_id: int):
        """Get a specific notification's data by ID (requires ownership)"""
        user_id, role = get_current_user_info() # user_id is parent_id
        current_app.logger.debug(f"Received GET request for notification ID: {notification_id} by parent {user_id}")
        # Service verifies ownership (parent_id == user_id)
        return NotificationService.get_notification_data(notification_id, user_id)

    @api.doc(
        "Mark notification as read/unread",
        security="Bearer",
        description="Update the read status of a notification belonging to the logged-in parent.",
        responses={
            200: ("Success", data_resp),
            400: "Validation Error/Invalid Data/Empty Body",
            401: "Unauthorized",
            403: "Forbidden (Not parent or not owner)",
            404: "Not Found",
            429: "Too Many Requests",
            500: "Internal Server Error",
        },
    )
    @api.expect(notification_update_input, validate=True)
    @jwt_required()
    @roles_required("parent") # Only parents modify their notifications
    # Use config for rate limit
    @limiter.limit(lambda: current_app.config.get("RATE_LIMIT_NOTIFICATION_UPDATE", "80/minute"))
    # Add type hint
    def patch(self, notification_id: int):
        """Update a notification's read status (requires ownership)"""
        user_id, role = get_current_user_info() # user_id is parent_id
        data = request.get_json()
        current_app.logger.debug(f"Received PATCH request for notification ID {notification_id} by parent {user_id} with data: {data}")
        # Service verifies ownership and updates is_read
        return NotificationService.update_notification_read_status(notification_id, data, user_id)

    @api.doc(
        "Delete a notification",
        security="Bearer",
        description="Delete a notification belonging to the logged-in parent.",
        responses={
            204: "No Content - Success",
            401: "Unauthorized",
            403: "Forbidden (Not parent or not owner)",
            404: "Not Found",
            429: "Too Many Requests",
            500: "Internal Server Error",
        },
    )
    @jwt_required()
    @roles_required("parent") # Only parents delete their notifications
    # Use config for rate limit
    @limiter.limit(lambda: current_app.config.get("RATE_LIMIT_NOTIFICATION_DELETE", "50/minute"))
    # Add type hint
    def delete(self, notification_id: int):
        """Delete a notification (requires ownership)"""
        user_id, role = get_current_user_info() # user_id is parent_id
        current_app.logger.debug(f"Received DELETE request for notification ID: {notification_id} by parent {user_id}")
        # Service verifies ownership before deleting
        return NotificationService.delete_notification(notification_id, user_id)

