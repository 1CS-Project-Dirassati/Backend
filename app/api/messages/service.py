# Added current_app
from flask import current_app
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from marshmallow import ValidationError
from sqlalchemy.orm import joinedload
from datetime import datetime  # For date parsing

# Import DB instance and models
from app import db

# Import related models needed for checks and context
from app.models import Message, Chat, Parent, Teacher

# Import shared utilities
from app.utils import (
    err_resp,
    message,
    internal_err_resp,
    validation_error,
)

# Import serialization/deserialization utilities from local utils.py
from .utils import dump_data, load_data


class MessageService:

    # --- Helper: Check if user can access chat ---
    @staticmethod
    def _can_access_chat(chat: Chat, user_id: int, user_role: str) -> bool:
        """Checks if the user is an admin or a participant of the chat."""
        if not chat:
            return False
        if user_role == "admin":
            return True
        if user_role == "parent" and chat.parent_id == user_id:
            return True
        if user_role == "teacher" and chat.teacher_id == user_id:
            return True
        return False

    # --- GET Single ---
    @staticmethod
    # Add type hints
    def get_message_data(message_id: int, current_user_id: int, current_user_role: str):
        """Get message data by ID, with record-level authorization check"""
        # Eager load chat for auth check
        message_obj = Message.query.options(joinedload(Message.chat)).get(message_id)

        if not message_obj:
            current_app.logger.info(f"Message with ID {message_id} not found.")
            return err_resp("Message not found!", "message_404", 404)

        # --- Record-Level Authorization Check ---
        if not MessageService._can_access_chat(
            message_obj.chat, current_user_id, current_user_role
        ):
            current_app.logger.warning(
                f"Forbidden: User {current_user_id} (Role: {current_user_role}) attempted to access message {message_id} in chat {message_obj.chat_id}."
            )
            return err_resp(
                "Forbidden: You do not have permission to access this message.",
                "record_access_denied",
                403,
            )
        current_app.logger.debug(
            f"Record access granted for user {current_user_id} to message {message_id}."
        )

        try:
            message_data = dump_data(message_obj)
            resp = message(True, "Message data sent successfully")
            resp["message"] = message_data
            current_app.logger.debug(f"Successfully retrieved message ID {message_id}")
            return resp, 200
        except Exception as error:
            current_app.logger.error(
                f"Error serializing message data for ID {message_id}: {error}",
                exc_info=True,
            )
            return internal_err_resp()

    # --- GET List with Filters, Pagination & Authorization ---
    @staticmethod
    # Add type hints
    def get_all_messages(
        chat_id: int,  # Required
        sender_id=None,
        start_date=None,
        end_date=None,
        page=None,
        per_page=None,
        current_user_id=None,
        current_user_role=None,
    ):
        """Get a paginated list of messages for a specific chat, filtered"""
        page = page or 1
        per_page = per_page or 20  # Default for messages

        try:
            # 1. Verify Chat Exists and User Can Access It
            chat = Chat.query.get(chat_id)
            if not chat:
                current_app.logger.info(
                    f"Chat ID {chat_id} not found when listing messages."
                )
                return err_resp(f"Chat with ID {chat_id} not found.", "chat_404", 404)
            if not current_user_id:
                current_app.logger.warning(
                    f"User ID is required to check chat access for chat {chat_id}."
                )
                return err_resp(
                    "User ID is required to check chat access.",
                    "user_id_required",
                    400,
                )
            if not current_user_role:
                current_app.logger.warning(
                    f"User role is required to check chat access for chat {chat_id}."
                )
                return err_resp(
                    "User role is required to check chat access.",
                    "user_role_required",
                    400,
                )

            if not MessageService._can_access_chat(
                chat, current_user_id, current_user_role
            ):
                current_app.logger.warning(
                    f"Forbidden: User {current_user_id} (Role: {current_user_role}) attempted to list messages for chat {chat_id}."
                )
                return err_resp(
                    "Forbidden: You do not have permission to access messages in this chat.",
                    "chat_access_denied",
                    403,
                )

            # 2. Build Query
            query = Message.query.filter(Message.chat_id == chat_id)

            # 3. Apply Filters
            filters_applied = {"chat_id": chat_id}
            if sender_id is not None:
                filters_applied["sender_id"] = sender_id
                query = query.filter(Message.sender_id == sender_id)

            # Date filters
            try:
                if start_date:
                    # Attempt to parse ISO format first, then YYYY-MM-DD
                    try:
                        start_dt = datetime.fromisoformat(
                            start_date.replace("Z", "+00:00")
                        )
                    except ValueError:
                        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
                    filters_applied["start_date"] = start_date
                    query = query.filter(Message.created_at >= start_dt)
                if end_date:
                    try:
                        end_dt = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
                    except ValueError:
                        # Add time component for date-only string to include the whole day
                        end_dt = datetime.strptime(end_date, "%Y-%m-%d").replace(
                            hour=23, minute=59, second=59, microsecond=999999
                        )
                    filters_applied["end_date"] = end_date
                    query = query.filter(Message.created_at <= end_dt)
            except ValueError:
                return err_resp(
                    "Invalid date format. Use YYYY-MM-DD or ISO 8601 format.",
                    "invalid_date_format",
                    400,
                )

            if filters_applied:
                current_app.logger.debug(
                    f"Applying message list filters: {filters_applied}"
                )

            # 4. Add ordering (typically newest first for chat)
            query = query.order_by(Message.created_at.desc())

            # 5. Implement pagination
            current_app.logger.debug(
                f"Paginating messages: page={page}, per_page={per_page}"
            )
            paginated_messages = query.paginate(
                page=page, per_page=per_page, error_out=False
            )
            current_app.logger.debug(
                f"Paginated messages items count: {len(paginated_messages.items)}"
            )

            # 6. Serialize results using dump_data
            messages_data = dump_data(paginated_messages.items, many=True)

            current_app.logger.debug(f"Serialized {len(messages_data)} messages")
            resp = message(True, "Messages list retrieved successfully")
            # Add pagination metadata
            resp["messages"] = messages_data
            resp["total"] = paginated_messages.total
            resp["pages"] = paginated_messages.pages
            resp["current_page"] = paginated_messages.page
            resp["per_page"] = paginated_messages.per_page
            resp["has_next"] = paginated_messages.has_next
            resp["has_prev"] = paginated_messages.has_prev

            current_app.logger.debug(
                f"Successfully retrieved messages page {page} for chat {chat_id}. Total: {paginated_messages.total}"
            )
            return resp, 200

        except Exception as error:
            log_msg = f"Error getting messages list (role: {current_user_role}, chat: {chat_id})"
            if page:
                log_msg += f", page {page}"
            current_app.logger.error(f"{log_msg}: {error}", exc_info=True)
            return internal_err_resp()

    # --- CREATE (Parent/Teacher) ---
    @staticmethod
    # Add type hints
    def create_message(data: dict, current_user_id: int, current_user_role: str):
        """Send a new message to a chat. Assumes @roles_required handled base role."""
        try:
            # 1. Schema Validation (Requires chat_id, content)
            # Using temporary manual load until load_data adjusted/confirmed.
            from app.models.Schemas import MessageSchema  # Temp import

            # Exclude sender info as it's derived
            message_create_schema = MessageSchema(
                exclude=("sender_id", "sender_role")
            )  # Temp instance
            validated_data = message_create_schema.load(data)
            # End Temporary block

            chat_id = validated_data["chat_id"]
            content = validated_data["content"]
            current_app.logger.debug(
                f"Message data validated by schema for chat {chat_id}."
            )

            # 2. Verify Chat Exists and User Can Access It
            chat = Chat.query.get(chat_id)
            if not chat:
                current_app.logger.info(
                    f"Chat ID {chat_id} not found when creating message."
                )
                return err_resp(f"Chat with ID {chat_id} not found.", "chat_404", 404)

            if not MessageService._can_access_chat(
                chat, current_user_id, current_user_role
            ):
                current_app.logger.warning(
                    f"Forbidden: User {current_user_id} (Role: {current_user_role}) attempted to send message to chat {chat_id}."
                )
                return err_resp(
                    "Forbidden: You cannot send messages to this chat.",
                    "chat_access_denied",
                    403,
                )

            # 3. Create Instance & Commit
            new_message = load_data(data)
            db.session.add(new_message)
            db.session.commit()
            current_app.logger.info(
                f"Message created successfully with ID: {new_message.id} in chat {chat_id} by User ID: {current_user_id} ({current_user_role})"
            )

            # 4. Serialize & Respond using dump_data
            message_resp_data = dump_data(new_message)
            resp = message(True, "Message sent successfully.")
            resp["message"] = message_resp_data
            return resp, 201

        except ValidationError as err:
            db.session.rollback()
            current_app.logger.warning(
                f"Schema validation error creating message: {err.messages}. Data: {data}"
            )
            return validation_error(False, err.messages), 400
        except SQLAlchemyError as error:
            db.session.rollback()
            current_app.logger.error(
                f"Database error creating message: {error}. Data: {data}", exc_info=True
            )
            return internal_err_resp()
        except Exception as error:
            db.session.rollback()
            current_app.logger.error(
                f"Unexpected error creating message: {error}. Data: {data}",
                exc_info=True,
            )
            return internal_err_resp()

    # --- UPDATE (Sender Only) ---
    @staticmethod
    # Add type hints
    def update_message(
        message_id: int, data: dict, current_user_id: int, current_user_role: str
    ):
        """Update an existing message (content). Assumes @roles_required handled base role."""
        message_obj = Message.query.get(message_id)
        if not message_obj:
            current_app.logger.info(
                f"Attempted update for non-existent message ID: {message_id}"
            )
            return err_resp("Message not found!", "message_404", 404)

        # --- Record-Level Authorization Check ---
        # Only the original sender can update
        if (
            message_obj.sender_id != current_user_id
            or message_obj.sender_role != current_user_role
        ):
            current_app.logger.warning(
                f"Forbidden: User {current_user_id} ({current_user_role}) attempted to update message {message_id} sent by user {message_obj.sender_id} ({message_obj.sender_role})."
            )
            return err_resp(
                "Forbidden: You can only update messages you sent.",
                "update_forbidden",
                403,
            )

        if not data or "content" not in data:
            current_app.logger.warning(
                f"Attempted update for message {message_id} with empty or invalid data."
            )
            return err_resp(
                "Request body must contain 'content' for update.",
                "empty_update_data",
                400,
            )

        try:
            # 1. Schema Validation & Deserialization (partial, only content)
            # Using temporary manual load until load_data adjusted/confirmed.
            from app.models.Schemas import MessageSchema  # Temp import

            message_update_schema = MessageSchema(
                partial=True, only=("content",)
            )  # Temp instance
            validated_data = message_update_schema.load(data)
            # End Temporary block

            current_app.logger.debug(
                f"Message data validated by schema for update ID: {message_id}"
            )

            # 2. Update content
            message_obj.content = validated_data["content"]
            updated = True  # Assume updated if validation passed

            # 3. Commit Changes
            db.session.add(message_obj)  # Add modified object to session
            db.session.commit()
            current_app.logger.info(
                f"Message updated successfully for ID: {message_id} by User ID: {current_user_id}"
            )

            # 4. Serialize & Respond using dump_data
            message_resp_data = dump_data(message_obj)
            resp = message(True, "Message updated successfully.")
            resp["message"] = message_resp_data
            return resp, 200

        except ValidationError as err:
            db.session.rollback()
            current_app.logger.warning(
                f"Schema validation error updating message {message_id}: {err.messages}. Data: {data}"
            )
            return validation_error(False, err.messages), 400
        except SQLAlchemyError as error:
            db.session.rollback()
            current_app.logger.error(
                f"Database error updating message {message_id}: {error}. Data: {data}",
                exc_info=True,
            )
            return internal_err_resp()
        except Exception as error:
            db.session.rollback()
            current_app.logger.error(
                f"Unexpected error updating message {message_id}: {error}. Data: {data}",
                exc_info=True,
            )
            return internal_err_resp()

    # --- DELETE (Sender or Admin) ---
    @staticmethod
    # Add type hint
    def delete_message(message_id: int, current_user_id: int, current_user_role: str):
        """Delete a message. Assumes @roles_required handled base role."""
        message_obj = Message.query.get(message_id)
        if not message_obj:
            current_app.logger.info(
                f"Attempted delete for non-existent message ID: {message_id}"
            )
            return err_resp("Message not found!", "message_404", 404)

        # --- Record-Level Authorization Check ---
        can_delete = (current_user_role == "admin") or (
            message_obj.sender_id == int(current_user_id)
            and message_obj.sender_role == current_user_role
        )

        if not can_delete:
            current_app.logger.warning(
                f"Forbidden: User {current_user_id} ({current_user_role}) attempted to delete message {message_id} sent by user {message_obj.sender_id} ({message_obj.sender_role})."
            )
            return err_resp(
                "Forbidden: You cannot delete this message.", "delete_forbidden", 403
            )

        try:
            current_app.logger.warning(
                f"User {current_user_id} (Role: {current_user_role}) attempting to delete message {message_id}."
            )

            db.session.delete(message_obj)
            db.session.commit()

            current_app.logger.info(
                f"Message {message_id} deleted successfully by User ID: {current_user_id}."
            )
            return None, 204

        except SQLAlchemyError as error:
            db.session.rollback()
            current_app.logger.error(
                f"Database error deleting message {message_id}: {error}", exc_info=True
            )
            return err_resp(
                "Could not delete message due to a database constraint or error.",
                "delete_error_db",
                500,
            )
        except Exception as error:
            db.session.rollback()
            current_app.logger.error(
                f"Unexpected error deleting message {message_id}: {error}",
                exc_info=True,
            )
            return internal_err_resp()
