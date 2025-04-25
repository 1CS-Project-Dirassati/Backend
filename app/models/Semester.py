from app import db
from datetime import datetime, timezone
from . import Column, Model, relationship


class Semester(Model):
    """Represents an academic semester, linked to a level."""

    __tablename__ = "semester"

    id = Column(db.Integer, primary_key=True)
    name = Column(db.String(50), nullable=False)
    level_id = Column(db.Integer, db.ForeignKey("level.id"), nullable=False, index=True)
    start_date = Column(db.Date, nullable=False)
    duration = Column(db.Integer, nullable=False)
    created_at = Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    level = relationship("Level", back_populates="semesters")
    sessions = relationship("Session", back_populates="semester")

    def __repr__(self):
        return f"<Semester id={self.id} name={self.name} level_id={self.level_id}>"
