from flask_restx import Namespace, fields
from flask_restx.reqparse import RequestParser


class MessageDto:
    """Data Transfer Objects and Request Parsers for the Message API."""

    # Define the namespace
    api = Namespace(
        "message", description="Chat message related operations."
    )  # Changed from 'messages'

    # --- Parser for Query Parameters (Filters and Pagination) ---
    message_filter_parser = RequestParser(bundle_errors=True)
    message_filter_parser.add_argument(
        "chat_id",
        type=int,
        location="args",
        required=True,  # CRITICAL: chat_id is required to list messages
        help="Filter messages by the ID of the chat conversation (Required).",
    )
    message_filter_parser.add_argument(
        "sender_id",
        type=int,
        location="args",
        required=False,
        help="Filter messages by the ID of the sender (parent or teacher).",
    )
    message_filter_parser.add_argument(
        "start_date",
        type=str,  # Expecting YYYY-MM-DD or ISO format string
        location="args",
        required=False,
        help="Filter messages sent on or after this date/time (YYYY-MM-DD or ISO format).",
    )
    message_filter_parser.add_argument(
        "end_date",
        type=str,  # Expecting YYYY-MM-DD or ISO format string
        location="args",
        required=False,
        help="Filter messages sent on or before this date/time (YYYY-MM-DD or ISO format).",
    )
    message_filter_parser.add_argument(
        "page",
        type=int,
        location="args",
        required=False,
        default=1,
        help="Page number for pagination (default: 1).",
    )
    message_filter_parser.add_argument(
        "per_page",
        type=int,
        location="args",
        required=False,
        default=20,  # Higher default for messages?
        help="Number of items per page (default: 20).",
    )

    # Define the core 'message' object model
    message = api.model(
        "Message Object",
        {
            "id": fields.Integer(
                readonly=True, description="Message unique identifier"
            ),
            "chat_id": fields.Integer(
                required=True,
                description="ID of the chat conversation this message belongs to",
            ),
            "sender_id": fields.Integer(
                required=True,
                readonly=True,
                description="ID of the sender (parent or teacher)",
            ),
            "sender_role": fields.String(
                required=True,
                readonly=True,
                description="Role of the sender ('parent' or 'teacher')",
            ),
            "content": fields.String(
                required=True, description="Content of the message"
            ),  # Using String, Text is for DB
            "created_at": fields.DateTime(
                readonly=True, description="Timestamp when the message was sent (UTC)"
            ),
        },
    )

    # Standard response for a single message
    data_resp = api.model(
        "Message Data Response",
        {
            "status": fields.Boolean(description="Indicates success or failure"),
            "message": fields.String(description="Response message"),
            "message": fields.Nested(message, description="The message data"),
        },
    )

    # Standard response for a list of messages (includes pagination)
    list_data_resp = api.model(
        "Message List Response",
        {
            "status": fields.Boolean(description="Indicates success or failure"),
            "message": fields.String(description="Response message"),
            "messages": fields.List(
                fields.Nested(message), description="List of message data"
            ),
            "total": fields.Integer(
                description="Total number of messages matching the query"
            ),
            "pages": fields.Integer(description="Total number of pages"),
            "current_page": fields.Integer(description="The current page number"),
            "per_page": fields.Integer(description="Number of items per page"),
            "has_next": fields.Boolean(description="True if there is a next page"),
            "has_prev": fields.Boolean(description="True if there is a previous page"),
        },
    )

    # --- DTOs for POST/PATCH ---
    message_create_input = api.model(
        "Message Create Input",
        {
            "chat_id": fields.Integer(
                required=True,
                description="ID of the chat conversation to send the message to",
            ),
            "content": fields.String(
                required=True, description="Content of the message"
            ),
            # sender_id and sender_role are inferred from JWT
        },
    )

    message_update_input = api.model(
        "Message Update Input",
        {
            "content": fields.String(
                required=True, description="Updated content of the message"
            ),
            # chat_id, sender_id, sender_role cannot be changed
        },
    )
