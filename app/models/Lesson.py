from app import db
from datetime import datetime, timezone
from . import Column, Model, relationship


class Cours(Model):
    """Course content/material"""

    __tablename__ = "cours"

    id = Column(db.Integer, primary_key=True)
    title = Column(db.String(100), nullable=False)
    content = Column(db.Text, nullable=True)
    module_id = Column(db.Integer, db.ForeignKey("module.id"), nullable=False)
    teacher_id = Column(db.Integer, db.ForeignKey("teacher.id"), nullable=False)
    created_at = Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    module = relationship("Module", back_populates="cours")
    teacher = relationship("Teacher", back_populates="cours")

    def __repr__(self):
        return f"<Cours id={self.id} title={self.title} module_id={self.module_id}>"
