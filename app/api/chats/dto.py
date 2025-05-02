from flask_restx import Namespace, fields
from flask_restx.reqparse import RequestParser


class ChatDto:
    """Data Transfer Objects and Request Parsers for the Chat API."""

    # Define the namespace
    api = Namespace(
        "chat", description="Chat conversation related operations."
    )  # Changed from 'chats'

    # --- Parser for Query Parameters (Filters and Pagination) ---
    chat_filter_parser = RequestParser(bundle_errors=True)
    chat_filter_parser.add_argument(
        "other_participant_id",
        type=int,
        location="args",
        required=False,
        help="Filter chats by the ID of the other participant (teacher ID if user is parent, parent ID if user is teacher).",
    )
    chat_filter_parser.add_argument(
        "page",
        type=int,
        location="args",
        required=False,
        default=1,
        help="Page number for pagination (default: 1).",
    )
    chat_filter_parser.add_argument(
        "per_page",
        type=int,
        location="args",
        required=False,
        default=10,
        help="Number of items per page (default: 10).",
    )

    # Define the core 'chat' object model
    chat = api.model(
        "Chat Object",
        {
            "id": fields.Integer(readonly=True, description="Chat unique identifier"),
            "parent_id": fields.Integer(
                required=True, description="ID of the parent participant"
            ),
            "teacher_id": fields.Integer(
                required=True, description="ID of the teacher participant"
            ),
            "created_at": fields.DateTime(
                readonly=True, description="Timestamp when the chat was created (UTC)"
            ),
            # Consider adding participant names/details via service enrichment if needed
            # "parent_name": fields.String(attribute="parent.user.name", readonly=True),
            # "teacher_name": fields.String(attribute="teacher.user.name", readonly=True),
        },
    )

    # Standard response for a single chat
    data_resp = api.model(
        "Chat Data Response",
        {
            "status": fields.Boolean(description="Indicates success or failure"),
            "message": fields.String(description="Response message"),
            "chat": fields.Nested(chat, description="The chat conversation data"),
        },
    )

    # Standard response for a list of chats (includes pagination)
    list_data_resp = api.model(
        "Chat List Response",
        {
            "status": fields.Boolean(description="Indicates success or failure"),
            "message": fields.String(description="Response message"),
            "chats": fields.List(
                fields.Nested(chat), description="List of chat conversation data"
            ),
            "total": fields.Integer(
                description="Total number of chats matching the query"
            ),
            "pages": fields.Integer(description="Total number of pages"),
            "current_page": fields.Integer(description="The current page number"),
            "per_page": fields.Integer(description="Number of items per page"),
            "has_next": fields.Boolean(description="True if there is a next page"),
            "has_prev": fields.Boolean(description="True if there is a previous page"),
        },
    )

    # --- DTOs for POST ---
    chat_create_input = api.model(
        "Chat Create Input",
        {
            # Depending on role, one of these will be required
            "parent_id": fields.Integer(
                required=False,
                description="ID of the parent participant (required if user is teacher)",
            ),
            "teacher_id": fields.Integer(
                required=False,
                description="ID of the teacher participant (required if user is parent)",
            ),
        },
    )
