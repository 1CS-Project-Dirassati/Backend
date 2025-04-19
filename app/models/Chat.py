from app import db
from datetime import datetime, timezone
from . import Column, Model, relationship


class Chat(Model):
    """Chat conversation between parent and teacher"""

    __tablename__ = "chat"

    id = Column(db.Integer, primary_key=True)
    parent_id = Column(db.Integer, db.ForeignKey("parent.id"), nullable=False)
    teacher_id = Column(db.Integer, db.ForeignKey("teacher.id"), nullable=False)
    created_at = Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    parent = relationship("Parent", foreign_keys=[parent_id])
    teacher = relationship("Teacher", foreign_keys=[teacher_id])
    messages = relationship(
        "Message", back_populates="chat", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Chat id={self.id} parent_id={self.parent_id} teacher_id={self.teacher_id}>"
