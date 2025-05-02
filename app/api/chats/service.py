# Added current_app
from flask import current_app
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from marshmallow import ValidationError
from sqlalchemy.orm import joinedload

# Import DB instance and models
from app import db

# Import related models needed for checks and context
from app.models import Chat, Parent, Teacher

# Import shared utilities
from app.utils import ( err_resp,
    message,
    internal_err_resp,
    validation_error,
)

# Import serialization/deserialization utilities from local utils.py
from .utils import dump_data, load_data


class ChatService:

    # --- GET Single ---
    @staticmethod
    # Add type hints
    def get_chat_data(chat_id: int, current_user_id: int, current_user_role: str):
        """Get chat data by ID, with record-level authorization check"""
        # Eager load participants for auth check
        chat = Chat.query.options(
            joinedload(Chat.parent), joinedload(Chat.teacher)
        ).get(chat_id)

        if not chat:
            current_app.logger.info(f"Chat with ID {chat_id} not found.")
            return err_resp("Chat not found!", "chat_404", 404)

        # --- Record-Level Authorization Check ---
        can_access = False
        log_reason = ""
        if current_user_role == "admin":
            can_access = True
            log_reason = "User is admin."
        elif current_user_role == "parent" and chat.parent_id == current_user_id:
            can_access = True
            log_reason = "User is the parent participant."
        elif current_user_role == "teacher" and chat.teacher_id == current_user_id:
            can_access = True
            log_reason = "User is the teacher participant."

        if not can_access:
            current_app.logger.warning(
                f"Forbidden: User {current_user_id} (Role: {current_user_role}) attempted to access chat {chat_id}."
            )
            return err_resp(
                "Forbidden: You do not have permission to access this chat.",
                "record_access_denied",
                403,
            )
        current_app.logger.debug(
            f"Record access granted for user {current_user_id} to chat {chat_id}. Reason: {log_reason}"
        )

        try:
            chat_data = dump_data(chat)
            resp = message(True, "Chat data sent successfully")
            resp["chat"] = chat_data
            current_app.logger.debug(f"Successfully retrieved chat ID {chat_id}")
            return resp, 200
        except Exception as error:
            current_app.logger.error(
                f"Error serializing chat data for ID {chat_id}: {error}",
                exc_info=True,
            )
            return internal_err_resp()

    # --- GET List with Filters, Pagination & Authorization ---
    @staticmethod
    # Add type hints
    def get_all_chats(
        other_participant_id=None,
        page=None,
        per_page=None,
        current_user_id=None,
        current_user_role=None,
    ):
        """Get a paginated list of chats for the current user, filtered"""
        page = page or 1
        per_page = per_page or 10

        try:
            query = Chat.query

            # --- Role-Based Data Scoping ---
            if current_user_role == "parent":
                current_app.logger.debug(
                    f"Scoping chats list for parent ID: {current_user_id}"
                )
                query = query.filter(Chat.parent_id == current_user_id)
                # Filter by teacher if provided
                if other_participant_id is not None:
                    query = query.filter(Chat.teacher_id == other_participant_id)
            elif current_user_role == "teacher":
                current_app.logger.debug(
                    f"Scoping chats list for teacher ID: {current_user_id}"
                )
                query = query.filter(Chat.teacher_id == current_user_id)
                # Filter by parent if provided
                if other_participant_id is not None:
                    query = query.filter(Chat.parent_id == other_participant_id)
            else:
                # Should not happen due to @roles_required, but handle defensively
                current_app.logger.error(
                    f"Invalid role '{current_user_role}' attempted to list chats."
                )
                return err_resp(
                    "Forbidden: Invalid role for listing chats.",
                    "list_role_forbidden",
                    403,
                )

            # Add ordering (e.g., by creation date descending)
            query = query.order_by(Chat.created_at.desc())

            # Implement pagination
            current_app.logger.debug(
                f"Paginating chats: page={page}, per_page={per_page}"
            )
            paginated_chats = query.paginate(
                page=page, per_page=per_page, error_out=False
            )
            current_app.logger.debug(
                f"Paginated chats items count: {len(paginated_chats.items)}"
            )

            # Serialize results using dump_data
            chats_data = dump_data(paginated_chats.items, many=True)

            current_app.logger.debug(f"Serialized {len(chats_data)} chats")
            resp = message(True, "Chats list retrieved successfully")
            # Add pagination metadata
            resp["chats"] = chats_data
            resp["total"] = paginated_chats.total
            resp["pages"] = paginated_chats.pages
            resp["current_page"] = paginated_chats.page
            resp["per_page"] = paginated_chats.per_page
            resp["has_next"] = paginated_chats.has_next
            resp["has_prev"] = paginated_chats.has_prev

            current_app.logger.debug(
                f"Successfully retrieved chats page {page}. Total: {paginated_chats.total}"
            )
            return resp, 200

        except Exception as error:
            log_msg = f"Error getting chats list (role: {current_user_role})"
            if other_participant_id:
                log_msg += f" with other_participant_id {other_participant_id}"
            if page:
                log_msg += f", page {page}"
            current_app.logger.error(f"{log_msg}: {error}", exc_info=True)
            return internal_err_resp()

    # --- CREATE or FIND ---
    @staticmethod
    # Add type hints
    def find_or_create_chat(data: dict, current_user_id: int, current_user_role: str):
        """Find an existing chat or create a new one between participants."""
        parent_id = None
        teacher_id = None
        other_participant_id = None

        # Determine parent and teacher IDs based on current user's role
        if current_user_role == "parent":
            parent_id = current_user_id
            teacher_id = data.get("teacher_id")
            other_participant_id = teacher_id
            if not teacher_id:
                return err_resp(
                    "Teacher ID is required when creating chat as a parent.",
                    "teacher_id_missing",
                    400,
                )
            if parent_id == teacher_id:  # Should not happen if IDs are distinct
                return err_resp(
                    "Cannot create a chat with yourself.", "chat_with_self", 400
                )
            # Validate teacher exists
            if not Teacher.query.get(teacher_id):
                return err_resp(
                    f"Teacher with ID {teacher_id} not found.", "teacher_not_found", 404
                )

        elif current_user_role == "teacher":
            teacher_id = current_user_id
            parent_id = data.get("parent_id")
            other_participant_id = parent_id
            if not parent_id:
                return err_resp(
                    "Parent ID is required when creating chat as a teacher.",
                    "parent_id_missing",
                    400,
                )
            if teacher_id == parent_id:  # Should not happen
                return err_resp(
                    "Cannot create a chat with yourself.", "chat_with_self", 400
                )
            # Validate parent exists
            if not Parent.query.get(parent_id):
                return err_resp(
                    f"Parent with ID {parent_id} not found.", "parent_not_found", 404
                )
        else:
            # Should not happen due to @roles_required
            return err_resp(
                "Invalid role for creating chat.", "create_role_forbidden", 403
            )

        try:
            # Check if chat already exists between these two participants
            existing_chat = Chat.query.filter(
                ((Chat.parent_id == parent_id) & (Chat.teacher_id == teacher_id))
                | (
                    (Chat.parent_id == parent_id) & (Chat.teacher_id == teacher_id)
                )  # Redundant check, simplified below
            ).first()

            # Simpler check assuming parent_id and teacher_id are correctly assigned
            existing_chat = Chat.query.filter_by(
                parent_id=parent_id, teacher_id=teacher_id
            ).first()

            if existing_chat:
                current_app.logger.info(
                    f"Found existing chat ID {existing_chat.id} for parent {parent_id} and teacher {teacher_id}."
                )
                chat_data = dump_data(existing_chat)
                resp = message(True, "Existing chat found.")
                resp["chat"] = chat_data
                return resp, 200  # OK, not Created

            # If not existing, create a new one
            current_app.logger.info(
                f"Creating new chat for parent {parent_id} and teacher {teacher_id}."
            )
            new_chat = load_data(data)
            db.session.add(new_chat)
            db.session.commit()
            current_app.logger.info(f"Chat created successfully with ID: {new_chat.id}")

            chat_data = dump_data(new_chat)
            resp = message(True, "Chat created successfully.")
            resp["chat"] = chat_data
            return resp, 201  # Created

        except SQLAlchemyError as error:
            db.session.rollback()
            current_app.logger.error(
                f"Database error finding or creating chat: {error}. Data: {data}",
                exc_info=True,
            )
            return internal_err_resp()
        except Exception as error:
            db.session.rollback()
            current_app.logger.error(
                f"Unexpected error finding or creating chat: {error}. Data: {data}",
                exc_info=True,
            )
            return internal_err_resp()

    # --- DELETE (Admin only) ---
    @staticmethod
    # Add type hint
    def delete_chat(chat_id: int, current_user_id: int, current_user_role: str):
        """Delete a chat and its messages. Assumes @roles_required('admin') handled authorization."""
        # No role check needed here due to decorator

        chat = Chat.query.get(chat_id)
        if not chat:
            current_app.logger.info(
                f"Attempted delete for non-existent chat ID: {chat_id}"
            )
            return err_resp("Chat not found!", "chat_404", 404)

        try:
            current_app.logger.warning(
                f"Admin {current_user_id} attempting to delete chat {chat_id} (Parent: {chat.parent_id}, Teacher: {chat.teacher_id}). This will cascade delete messages."
            )

            db.session.delete(chat)  # Cascade delete handles messages
            db.session.commit()

            current_app.logger.info(
                f"Chat {chat_id} and associated messages deleted successfully by Admin {current_user_id}."
            )
            return None, 204

        except SQLAlchemyError as error:
            db.session.rollback()
            current_app.logger.error(
                f"Database error deleting chat {chat_id}: {error}", exc_info=True
            )
            return err_resp(
                "Could not delete chat due to a database constraint or error.",
                "delete_error_db",
                500,
            )
        except Exception as error:
            db.session.rollback()
            current_app.logger.error(
                f"Unexpected error deleting chat {chat_id}: {error}", exc_info=True
            )
            return internal_err_resp()
