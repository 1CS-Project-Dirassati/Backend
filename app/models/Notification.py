from sqlalchemy.orm import relationship
from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    ForeignKey,
    Text,
)  # Added Text
from sqlalchemy.sql import func

from app import db  # Assuming db is your SQLAlchemy instance


class Notification(db.Model):
    """Stores individual notifications for users."""

    __tablename__ = "notification"

    id = Column(Integer, primary_key=True)

    # Polymorphic relationship for the recipient
    recipient_type = Column(
        String(50), nullable=False
    )  # e.g., 'parent', 'admin', 'teacher', 'student'
    recipient_id = Column(
        Integer, nullable=False
    )  # ID of the user in their respective table

    # Consider a generic way to link back if needed, or handle querying per type
    # recipient = relationship(...) # Complex polymorphic setup, might be overkill initially

    message = Column(Text, nullable=False)  # Use Text for potentially longer messages
    link = Column(
        String(255), nullable=True
    )  # Optional URL related to the notification
    is_read = Column(Boolean, default=False, nullable=False)
    type = Column(
        String(50), nullable=True, index=True
    )  # Optional category (e.g., 'grade', 'absence', 'application', 'message')

    # Optional: Track who/what triggered the notification
    # sender_type = Column(String(50), nullable=True)
    # sender_id = Column(Integer, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), onupdate=func.now()
    )  # Track when read status changes

    # Add index for faster querying by user and read status
    __table_args__ = (
        db.Index(
            "ix_notification_recipient_read_created",
            "recipient_type",
            "recipient_id",
            "is_read",
            "created_at",
        ),
    )

    def __repr__(self):
        read_status = "Read" if getattr(self, "is_read", False) else "Unread"
        return f"<Notification id={self.id} for {self.recipient_type} {self.recipient_id} - {read_status}>"
