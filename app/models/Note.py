from app import db
from . import Column, Model, relationship
from datetime import datetime, timezone
from enum import Enum


class NoteType(Enum):
    CC = "cc"
    EXAM1 = "exam1"
    EXAM2 = "exam2"


class Note(Model):
    """Student grade for a module"""

    __tablename__ = "note"

    id = Column(db.Integer, primary_key=True)
    student_id = Column(db.Integer, db.ForeignKey("student.id"), nullable=False)
    module_id = Column(db.Integer, db.ForeignKey("module.id"), nullable=False)
    teacher_id = Column(db.Integer, db.ForeignKey("teacher.id"), nullable=False)
    value = Column(db.Float, nullable=False)
    type = Column(db.Enum(NoteType), nullable=False)
    comment = Column(db.Text, nullable=True)
    created_at = Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    student = relationship("Student", back_populates="notes")
    module = relationship("Module", back_populates="notes")
    teacher = relationship("Teacher", back_populates="notes")

    def __init__(
        self,
        student_id,
        module_id,
        teacher_id,
        value,
        type,
        comment=None,
    ):
        self.student_id = student_id
        self.module_id = module_id
        self.teacher_id = teacher_id
        self.value = value
        self.type = type
        self.comment = comment

    def __repr__(self):
        return f"<Note id={self.id} student_id={self.student_id} module_id={self.module_id} value={self.value} type={self.type.value}>"
