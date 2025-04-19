from app import db
from datetime import datetime, timezone
from . import Column, Model, relationship


class Absence(Model):
    """Records an absence of a student from a specific session."""

    __tablename__ = "absence"

    id = Column(db.Integer, primary_key=True)
    student_id = Column(
        db.Integer, db.ForeignKey("student.id"), nullable=False, index=True
    )
    session_id = Column(
        db.Integer, db.ForeignKey("session.id"), nullable=False, index=True
    )
    justified = Column(db.Boolean, default=False, nullable=False)
    reason = Column(db.String(255), nullable=True)
    recorded_at = Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    student = relationship("Student", back_populates="absences")
    session = relationship("Session", back_populates="absences")

    __table_args__ = (
        db.UniqueConstraint("student_id", "session_id", name="_student_session_uc"),
    )

    def __repr__(self):
        return f"<Absence id={self.id} student_id={self.student_id} session_id={self.session_id}>"



