# Added current_app
from flask import request, current_app
from flask_restx import Resource
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt

# Import shared extensions/decorators
from app.extensions import limiter
from app.api.decorators import roles_required

# Import chat-specific modules
from .service import ChatService
from .dto import ChatDto

# Get the API namespace and DTOs
api = ChatDto.api
data_resp = ChatDto.data_resp
list_data_resp = ChatDto.list_data_resp
chat_create_input = ChatDto.chat_create_input
# Get the filter/pagination parser
chat_filter_parser = ChatDto.chat_filter_parser


# --- Helper to get current user info ---
def get_current_user_info():
    user_id = get_jwt_identity()
    claims = get_jwt()
    role = claims.get("role")
    current_app.logger.debug(
        f"Current user info: ID={user_id}, Role={role}"
    )  # Log user info
    return user_id, role


# --- Route for listing/creating chats ---
@api.route("/")
class ChatList(Resource):

    @api.doc(
        "List chats",
        security="Bearer",
        parser=chat_filter_parser,
        description="Get a paginated list of chat conversations the current user (parent/teacher) is part of. Filterable by the other participant.",
        responses={
            200: ("Success", list_data_resp),
            401: "Unauthorized",
            403: "Forbidden",  # If role is not parent/teacher
            429: "Too Many Requests",
            500: "Internal Server Error",
        },
    )
    @jwt_required()
    @roles_required("parent", "teacher")  # Only participants can list their chats
    # Use config for rate limit
    @limiter.limit(lambda: current_app.config.get("RATE_LIMIT_CHAT_LIST", "50/minute"))
    def get(self):
        """Get a list of chats for the current user"""
        user_id, role = get_current_user_info()
        args = chat_filter_parser.parse_args()
        current_app.logger.debug(
            f"Received GET request for chats list with args: {args}"
        )

        # Pass filter, pagination, and user info to service for scoping
        return ChatService.get_all_chats(
            other_participant_id=args.get(
                "other_participant_id"
            ),  # ID of teacher (if user is parent) or parent (if user is teacher)
            page=args.get("page"),
            per_page=args.get("per_page"),
            current_user_id=user_id,
            current_user_role=role,
        )

    @api.doc(
        "Create a new chat",
        security="Bearer",
        description="Create a new chat conversation between the current user (parent/teacher) and another specified participant (teacher/parent). Idempotent: returns existing chat if one exists.",
        responses={
            200: ("Success (Existing Chat)", data_resp),  # Return existing if found
            201: ("Created", data_resp),
            400: "Validation Error/Invalid Participant ID",
            401: "Unauthorized",
            403: "Forbidden (e.g., trying to create chat with self, invalid role)",
            404: "Not Found (Other participant not found)",
            429: "Too Many Requests",
            500: "Internal Server Error",
        },
    )
    @api.expect(chat_create_input, validate=True)
    @jwt_required()
    @roles_required("parent", "teacher")  # Only participants can create chats
    # Use config for rate limit
    @limiter.limit(
        lambda: current_app.config.get("RATE_LIMIT_CHAT_CREATE", "10/minute")
    )
    def post(self):
        """Create a new chat or retrieve existing one"""
        user_id, role = get_current_user_info()  # Get user info for service logic
        data = request.get_json()
        current_app.logger.debug(
            f"Received POST request to create chat with data: {data}"
        )
        # Service handles finding/creating chat based on participants
        return ChatService.find_or_create_chat(data, user_id, role)


# --- Route for specific chat operations ---
@api.route("/<int:chat_id>")
@api.param("chat_id", "The unique identifier of the chat conversation")
class ChatResource(Resource):

    @api.doc(
        "Get a specific chat by ID",
        security="Bearer",
        description="Get metadata for a specific chat conversation. Access restricted to participants or Admin.",
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
    @limiter.limit(lambda: current_app.config.get("RATE_LIMIT_CHAT_GET", "100/minute"))
    # Add type hint
    def get(self, chat_id: int):
        """Get a specific chat's metadata by ID (with record-level access control)"""
        user_id, role = get_current_user_info()
        current_app.logger.debug(f"Received GET request for chat ID: {chat_id}")
        # Pass user info for record-level check
        return ChatService.get_chat_data(chat_id, user_id, role)

    @api.doc(
        "Delete a chat",
        security="Bearer",
        description="Delete a chat conversation and all its messages (Admin only).",
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
    @roles_required("admin")  # Only admins can delete chats
    # Use config for rate limit
    @limiter.limit(
        lambda: current_app.config.get("RATE_LIMIT_CHAT_DELETE", "10/minute")
    )
    # Add type hint
    def delete(self, chat_id: int):
        """Delete a chat conversation"""
        user_id, role = get_current_user_info()
        current_app.logger.debug(f"Received DELETE request for chat ID: {chat_id}")
        # Service layer handles authorization
        return ChatService.delete_chat(chat_id, user_id, role)
