from app import db
from . import Column, Model, relationship
from .TimeSlot import TimeSlot
from sqlalchemy import Enum as SQLAlchemyEnum


class Session(Model):
    """Represents a scheduled class session for a specific module and group."""
    __tablename__ = "session"

    id = Column(db.Integer, primary_key=True)
    teacher_id = Column(db.Integer, db.ForeignKey("teacher.id"), nullable=False, index=True)
    module_id = Column(db.Integer, db.ForeignKey("module.id"), nullable=False, index=True)
    group_id = Column(db.Integer, db.ForeignKey("group.id"), nullable=False, index=True)
    semester_id = Column(db.Integer, db.ForeignKey("semester.id"), nullable=False, index=True)
    salle_id = Column(db.Integer, db.ForeignKey("salle.id"), nullable=True)
    time_slot = Column(SQLAlchemyEnum(TimeSlot), nullable=False, index=True)
    weeks = Column(db.Integer, nullable=True)

    # Relationships
    teacher = relationship("Teacher", back_populates="sessions")
    module = relationship("Module", back_populates="sessions")
    group = relationship("Group", back_populates="sessions")
    semester = relationship("Semester", back_populates="sessions")
    salle = relationship("Salle", back_populates="sessions")
    absences = relationship("Absence", back_populates="session", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Session id={self.id} module_id={self.module_id} group_id={self.group_id} time_slot={self.time_slot.value}>"
