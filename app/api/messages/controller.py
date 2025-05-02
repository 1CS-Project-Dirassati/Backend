# Added current_app
from flask import request, current_app
from flask_restx import Resource
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt

# Import shared extensions/decorators
from app.extensions import limiter
from app.api.decorators import roles_required

# Import message-specific modules
from .service import MessageService
from .dto import MessageDto

# Get the API namespace and DTOs
api = MessageDto.api
data_resp = MessageDto.data_resp
list_data_resp = MessageDto.list_data_resp
message_create_input = MessageDto.message_create_input
message_update_input = MessageDto.message_update_input
# Get the filter/pagination parser
message_filter_parser = MessageDto.message_filter_parser


# --- Helper to get current user info ---
def get_current_user_info():
    user_id = get_jwt_identity()
    claims = get_jwt()
    role = claims.get("role")
    current_app.logger.debug(
        f"Current user info: ID={user_id}, Role={role}"
    )  # Log user info
    return user_id, role


# --- Route for listing/creating messages ---
@api.route("/")
class MessageList(Resource):

    @api.doc(
        "List messages for a chat",
        security="Bearer",
        parser=message_filter_parser,
        description="Get a paginated list of messages for a specific chat (chat_id is required). Access restricted to chat participants or Admin.",
        responses={
            200: ("Success", list_data_resp),
            400: "Bad Request (chat_id missing)",
            401: "Unauthorized",
            403: "Forbidden (Not participant/admin)",
            404: "Not Found (Chat not found)",
            429: "Too Many Requests",
            500: "Internal Server Error",
        },
    )
    @jwt_required()
    @roles_required("admin", "parent", "teacher")  # Base roles allowed
    # Use config for rate limit
    @limiter.limit(
        lambda: current_app.config.get("RATE_LIMIT_MESSAGE_LIST", "100/minute")
    )
    def get(self):
        """Get a list of messages for a specific chat"""
        user_id, role = get_current_user_info()
        args = message_filter_parser.parse_args()
        chat_id = args.get("chat_id")

        # chat_id is REQUIRED for listing messages
        if chat_id is None:
            return {
                "status": False,
                "message": "chat_id query parameter is required.",
            }, 400

        current_app.logger.debug(
            f"Received GET request for messages list with args: {args}"
        )

        # Pass filter, pagination, and user info to service for scoping/auth
        return MessageService.get_all_messages(
            chat_id=chat_id,
            sender_id=args.get("sender_id"),  # Optional filter
            start_date=args.get("start_date"),  # Optional filter
            end_date=args.get("end_date"),  # Optional filter
            page=args.get("page"),
            per_page=args.get("per_page"),
            current_user_id=user_id,
            current_user_role=role,
        )

    @api.doc(
        "Send a new message",
        security="Bearer",
        description="Send a new message to a specific chat conversation. Sender info is inferred from JWT. Access restricted to chat participants.",
        responses={
            201: ("Created", data_resp),
            400: "Validation Error/Invalid Data/Chat ID missing",
            401: "Unauthorized",
            403: "Forbidden (Not participant)",
            404: "Not Found (Chat not found)",
            429: "Too Many Requests",
            500: "Internal Server Error",
        },
    )
    @api.expect(message_create_input, validate=True)
    @jwt_required()
    @roles_required("parent", "teacher")  # Only participants can send messages
    # Use config for rate limit
    @limiter.limit(
        lambda: current_app.config.get("RATE_LIMIT_MESSAGE_CREATE", "60/minute")
    )
    def post(self):
        """Send a new message to a chat"""
        user_id, role = get_current_user_info()  # Get user info for service logic
        data = request.get_json()
        current_app.logger.debug(
            f"Received POST request to create message with data: {data}"
        )
        user_id = get_jwt_identity()  # Get user ID from JWT
        role = get_jwt()["role"]  # Get user role from JWT claims
        # Service handles authorization (is participant) and sets sender info
        return MessageService.create_message(data, user_id, role)


# --- Route for specific message operations ---
@api.route("/<int:message_id>")
@api.param("message_id", "The unique identifier of the message")
class MessageResource(Resource):

    @api.doc(
        "Get a specific message by ID",
        security="Bearer",
        description="Get data for a specific message. Access restricted to participants of the message's chat or Admin.",
        responses={
            200: ("Success", data_resp),
            401: "Unauthorized",
            403: "Forbidden",
            404: "Not Found",
            429: "Too Many Requests",
            500: "Internal Server Error",
        },
    )
    @jwt_required()
    @roles_required("admin", "parent", "teacher")  # Base roles allowed
    # Use config for rate limit
    @limiter.limit(
        lambda: current_app.config.get("RATE_LIMIT_MESSAGE_GET", "120/minute")
    )
    # Add type hint
    def get(self, message_id: int):
        """Get a specific message's data by ID (with record-level access control)"""
        current_app.logger.debug(f"Received GET request for message ID: {message_id}")
        # Pass user info for record-level check
        user_id = get_jwt_identity()  # Get user ID from JWT
        role = get_jwt()["role"]  # Get user role from JWT claims
        return MessageService.get_message_data(message_id, user_id, role)

    @api.doc(
        "Update a message",
        security="Bearer",
        description="Update the content of a message (Sender only).",
        responses={
            200: ("Success", data_resp),
            400: "Validation Error/Invalid Data/Empty Body",
            401: "Unauthorized",
            403: "Forbidden (Not sender)",
            404: "Not Found",
            429: "Too Many Requests",
            500: "Internal Server Error",
        },
    )
    @api.expect(message_update_input, validate=True)
    @jwt_required()
    @roles_required("parent", "teacher")  # Only potential senders
    # Use config for rate limit
    @limiter.limit(
        lambda: current_app.config.get("RATE_LIMIT_MESSAGE_UPDATE", "30/minute")
    )
    # Add type hint
    def patch(self, message_id: int):
        """Update an existing message (content)"""
        data = request.get_json()
        current_app.logger.debug(
            f"Received PATCH request for message ID {message_id} with data: {data}"
        )
        # Service layer handles authorization (is sender)
        user_id = get_jwt_identity()  # Get user ID from JWT
        role = get_jwt()["role"]
        return MessageService.update_message(message_id, data, user_id, role)

    @api.doc(
        "Delete a message",
        security="Bearer",
        description="Delete a message (Sender or Admin only).",
        responses={
            204: "No Content - Success",
            401: "Unauthorized",
            403: "Forbidden",
            404: "Not Found",
            429: "Too Many Requests",
            500: "Internal Server Error",
        },
    )
    @jwt_required()
    @roles_required("admin", "parent", "teacher")  # Base roles allowed
    # Use config for rate limit
    @limiter.limit(
        lambda: current_app.config.get("RATE_LIMIT_MESSAGE_DELETE", "30/minute")
    )
    # Add type hint
    def delete(self, message_id: int):
        """Delete a message"""
        current_app.logger.debug(
            f"Received DELETE request for message ID: {message_id}"
        )
        user_id = get_jwt_identity()
        role = get_jwt()["role"]
        # Service layer handles authorization (is sender or admin)
        return MessageService.delete_message(message_id, user_id, role)
