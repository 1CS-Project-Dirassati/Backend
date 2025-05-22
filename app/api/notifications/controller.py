from flask import request, current_app
from flask_restx import Resource
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt

# Import shared extensions/decorators
from app.extensions import limiter
from app.api.decorators import roles_required

# Import notification-specific modules
from .service import NotificationApiService # Renamed service for clarity
from .dto import NotificationDto

# Get the API namespace and DTOs
api = NotificationDto.api
data_resp = NotificationDto.data_resp
list_data_resp = NotificationDto.list_data_resp
unread_count_resp = NotificationDto.unread_count_resp # Added unread count DTO
notification_create_input = NotificationDto.notification_create_input
notification_update_input = NotificationDto.notification_update_input
notification_filter_parser = NotificationDto.notification_filter_parser


# --- Helper to get current user info ---
def get_current_user_info():
    user_id = get_jwt_identity()
    claims = get_jwt()
    role = claims.get("role")
    # Validate role against expected roles if necessary
    if not role:
        current_app.logger.error(f"JWT for user {user_id} is missing 'role' claim.")
        # This should ideally be caught by @roles_required, but good defense
        raise ValueError("User role not found in token claims.")
    current_app.logger.debug(f"Current user info: ID={user_id}, Role={role}")
    return user_id, role


# --- NEW Route for current user's notifications ---
@api.route("/me")
class MyNotificationList(Resource):

    @api.doc(
        "List my notifications",
        security="Bearer",
        parser=notification_filter_parser,
        description="Get a paginated list of notifications for the currently logged-in user (any role). Filterable by read status and notification type.",
        responses={
            200: ("Success", list_data_resp),
            401: "Unauthorized",
            403: "Forbidden (Role missing in token)", # Should be caught by @roles_required
            429: "Too Many Requests",
            500: "Internal Server Error",
        },
    )
    @jwt_required()
    # Allow all valid roles to access their own notifications
    @roles_required("parent", "student", "teacher", "admin")
    @limiter.limit(lambda: current_app.config.get("RATE_LIMIT_NOTIFICATION_LIST", "60/minute"))
    def get(self):
        """Get a list of my notifications"""
        try:
            user_id, role = get_current_user_info()
        except ValueError as e:
             return {"status": False, "message": str(e)}, 403 # Role missing

        args = notification_filter_parser.parse_args()
        current_app.logger.debug(
            f"Received GET request for User {user_id} ({role}) notifications list with args: {args}"
        )

        # Service scopes results to the current user using role and id
        return NotificationApiService.get_my_notifications(
            recipient_type=role,
            recipient_id=user_id,
            is_read=args.get("is_read"),
            notification_type=args.get("type"), # Use 'type' from parser
            page=args.get("page"),
            per_page=args.get("per_page"),
        )

# --- Route for Admin creating notifications ---
# Keeping '/' for admin creation for now, could be moved to /admin/notifications later
@api.route("/")
class NotificationAdminCreate(Resource):

    @api.doc(
        "Create a notification (Admin Only)",
        security="Bearer",
        description="Create a notification targeted at a specific user (Admin access required).",
        responses={
            201: ("Created", data_resp),
            400: "Validation Error/Invalid Data",
            401: "Unauthorized",
            403: "Forbidden (Not Admin)",
            404: "Not Found (Recipient user not found)",
            429: "Too Many Requests",
            500: "Internal Server Error",
        },
    )
    @api.expect(notification_create_input, validate=True)
    @jwt_required()
    @roles_required("admin")
    @limiter.limit(lambda: current_app.config.get("RATE_LIMIT_NOTIFICATION_ADMIN_CREATE", "20/minute"))
    def post(self):
        """Create a new notification (Admin only)"""
        data = request.get_json()
        try:
            admin_id, _ = get_current_user_info() # Get admin ID for logging
        except ValueError:
             return {"status": False, "message": "Admin role missing in token"}, 403

        current_app.logger.debug(
            f"Received POST request by Admin {admin_id} to create notification with data: {data}"
        )
        # Service handles validation and creation
        return NotificationApiService.create_notification_by_admin(data)


# --- Route for specific notification operations (for the owner) ---
@api.route("/<int:notification_id>")
@api.param("notification_id", "The unique identifier of the notification")
class NotificationResource(Resource):

    @api.doc(
        "Get a specific notification by ID",
        security="Bearer",
        description="Get data for a specific notification belonging to the logged-in user.",
        responses={
            200: ("Success", data_resp),
            401: "Unauthorized",
            403: "Forbidden (Not owner)",
            404: "Not Found",
            429: "Too Many Requests",
            500: "Internal Server Error",
        },
    )
    @jwt_required()
    # Allow all roles to get their own specific notification
    @roles_required("parent", "student", "teacher", "admin")
    @limiter.limit(lambda: current_app.config.get("RATE_LIMIT_NOTIFICATION_GET", "100/minute"))
    def get(self, notification_id: int):
        """Get a specific notification's data by ID (requires ownership)"""
        try:
            user_id, role = get_current_user_info()
        except ValueError as e:
             return {"status": False, "message": str(e)}, 403

        current_app.logger.debug(
            f"Received GET request for notification ID: {notification_id} by User {user_id} ({role})"
        )
        # Service verifies ownership using role and id
        return NotificationApiService.get_notification_data(notification_id, user_id, role)

    @api.doc(
        "Mark notification as read/unread",
        security="Bearer",
        description="Update the read status of a notification belonging to the logged-in user.",
        responses={
            200: ("Success", data_resp),
            400: "Validation Error/Invalid Data/Empty Body",
            401: "Unauthorized",
            403: "Forbidden (Not owner)",
            404: "Not Found",
            429: "Too Many Requests",
            500: "Internal Server Error",
        },
    )
    @api.expect(notification_update_input, validate=True)
    @jwt_required()
    # Allow all roles to update their own notifications
    @roles_required("parent", "student", "teacher", "admin")
    @limiter.limit(lambda: current_app.config.get("RATE_LIMIT_NOTIFICATION_UPDATE", "80/minute"))
    def patch(self, notification_id: int):
        """Update a notification's read status (requires ownership)"""
        try:
            user_id, role = get_current_user_info()
        except ValueError as e:
             return {"status": False, "message": str(e)}, 403

        data = request.get_json()
        current_app.logger.debug(
            f"Received PATCH request for notification ID {notification_id} by User {user_id} ({role}) with data: {data}"
        )
        # Service verifies ownership and updates is_read
        return NotificationApiService.update_notification_read_status(
            notification_id, data, user_id, role
        )

    @api.doc(
        "Delete a notification",
        security="Bearer",
        description="Delete a notification belonging to the logged-in user.",
        responses={
            204: "No Content - Success",
            401: "Unauthorized",
            403: "Forbidden (Not owner)",
            404: "Not Found",
            429: "Too Many Requests",
            500: "Internal Server Error",
        },
    )
    @jwt_required()
    # Allow all roles to delete their own notifications
    @roles_required("parent", "student", "teacher", "admin")
    @limiter.limit(lambda: current_app.config.get("RATE_LIMIT_NOTIFICATION_DELETE", "50/minute"))
    def delete(self, notification_id: int):
        """Delete a notification (requires ownership)"""
        try:
            user_id, role = get_current_user_info()
        except ValueError as e:
             return {"status": False, "message": str(e)}, 403

        current_app.logger.debug(
            f"Received DELETE request for notification ID: {notification_id} by User {user_id} ({role})"
        )
        # Service verifies ownership before deleting
        return NotificationApiService.delete_notification(notification_id, user_id, role)

# --- Optional: Routes for batch operations ---
@api.route("/read-all")
class NotificationReadAll(Resource):
    @api.doc(
        "Mark all my notifications as read",
        security="Bearer",
        description="Marks all unread notifications for the logged-in user as read.",
        responses={
            200: ("Success"),
            401: "Unauthorized",
            403: "Forbidden",
            429: "Too Many Requests",
            500: "Internal Server Error",
        },
    )
    @jwt_required()
    @roles_required("parent", "student", "teacher", "admin")
    @limiter.limit(lambda: current_app.config.get("RATE_LIMIT_NOTIFICATION_READ_ALL", "10/minute"))
    def post(self): # Using POST for a bulk update action
        """Mark all my notifications as read"""
        try:
            user_id, role = get_current_user_info()
        except ValueError as e:
             return {"status": False, "message": str(e)}, 403
        current_app.logger.info(f"Received POST request to mark all notifications read for User {user_id} ({role})")
        return NotificationApiService.mark_all_as_read(user_id, role)

@api.route("/unread-count")
class NotificationUnreadCount(Resource):
    @api.doc(
        "Get my unread notification count",
        security="Bearer",
        description="Gets the count of unread notifications for the logged-in user.",
        responses={
            200: ("Success", unread_count_resp),
            401: "Unauthorized",
            403: "Forbidden",
            429: "Too Many Requests",
            500: "Internal Server Error",
        },
    )
    @jwt_required()
    @roles_required("parent", "student", "teacher", "admin")
    @limiter.limit(lambda: current_app.config.get("RATE_LIMIT_NOTIFICATION_UNREAD_COUNT", "60/minute"))
    def get(self):
        """Get my unread notification count"""
        try:
            user_id, role = get_current_user_info()
        except ValueError as e:
             return {"status": False, "message": str(e)}, 403
        current_app.logger.debug(f"Received GET request for unread count for User {user_id} ({role})")
        return NotificationApiService.get_unread_count(user_id, role)

