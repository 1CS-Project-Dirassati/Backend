from app import db
from . import (
    Model,
    Column,
    relationship,
)  # Assuming these are from your models/__init__.py
from . import User  # Import the base User model


class Student(User):
    """Represents a student enrolled in the system."""

    __tablename__ = "student"

    id = Column(db.Integer, db.ForeignKey("user.id"), primary_key=True)

    # Student-specific fields
    level_id = Column(db.Integer, db.ForeignKey("level.id"), nullable=True, index=True)
    group_id = Column(db.Integer, db.ForeignKey("group.id"), nullable=True, index=True)
    is_approved = Column(db.Boolean, default=False, nullable=False)
    # parent_id now refers to parent.user_id (the PK of the parent table)
    parent_id = Column(
        db.Integer, db.ForeignKey("parent.id"), nullable=False, index=True
    )
    docs_url = Column(db.String(255), nullable=True)

    __mapper_args__ = {
        "polymorphic_identity": "student",
    }

    # Relationships
    parent = relationship("Parent", foreign_keys=[parent_id], back_populates="students")
    level = relationship("Level", back_populates="students")
    group = relationship("Group", back_populates="students")
    absences = relationship(
        "Absence", back_populates="student", cascade="all, delete-orphan"
    )
    notes = relationship("Note", back_populates="student", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Student id={self.id} email={self.email} level_id={self.level_id} group_id={self.group_id}>"

    # verify_password method is inherited from User
