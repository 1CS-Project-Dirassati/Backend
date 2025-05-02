from app import db
from datetime import datetime, timezone
from . import Column, Model, relationship


class Message(Model):
    """Chat message"""

    __tablename__ = "message"

    id = Column(db.Integer, primary_key=True)
    chat_id = Column(db.Integer, db.ForeignKey("chat.id"), nullable=False)
    sender_id = Column(db.Integer, nullable=False)  # ID of parent or teacher
    sender_role = Column(db.String(10), nullable=False)  # "parent" or "teacher"
    content = Column(db.Text, nullable=False)
    created_at = Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    chat = relationship("Chat", back_populates="messages")

    def __repr__(self):
        return (
            f"<Message id={self.id} chat_id={self.chat_id} sender_id={self.sender_id}>"
        )
