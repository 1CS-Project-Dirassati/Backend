from app import db
from datetime import datetime, timezone
from . import Column, Model, relationship
from enum import Enum


class NotificationType(Enum):
    SYSTEM = "system"
    PAYMENT = "payment"
    ATTENDANCE = "attendance"
    MESSAGE = "message"


class Notification(Model):
    """System notification"""

    __tablename__ = "notification"

    id = Column(db.Integer, primary_key=True)
    parent_id = Column(db.Integer, db.ForeignKey("parent.id"), nullable=False)
    message = Column(db.Text, nullable=False)
    notification_type = Column(db.Enum(NotificationType), nullable=False)
    is_read = Column(db.Boolean, default=False)
    created_at = Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    parent = relationship("Parent", back_populates="notifications")

    def __repr__(self):
        return f"<Notification id={self.id} parent_id={self.parent_id} type={self.notification_type}>"
