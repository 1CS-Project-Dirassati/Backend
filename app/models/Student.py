from app import db
from datetime import datetime, timezone
from . import Column, Model, relationship
from werkzeug.security import check_password_hash


class Student(Model):
    """Represents a student enrolled in the system."""

    __tablename__ = "student"

    id = Column(db.Integer, primary_key=True)
    first_name = Column(db.String(50), nullable=True)
    last_name = Column(db.String(50), nullable=True)
    email = Column(db.String(100), unique=True, nullable=False, index=True)
    password = Column(db.String(200), nullable=False)
    level_id = Column(db.Integer, db.ForeignKey("level.id"), nullable=False, index=True)
    group_id = Column(db.Integer, db.ForeignKey("group.id"), nullable=True, index=True)
    is_approved = Column(db.Boolean, default=False, nullable=False)
    parent_id = Column(
        db.Integer, db.ForeignKey("parent.id"), nullable=False, index=True
    )
    docs_url = Column(db.String(255), nullable=True)
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

    # Relationships
    parent = relationship("Parent", back_populates="students")
    level = relationship("Level", back_populates="students")
    group = relationship("Group", back_populates="students")
    absences = relationship(
        "Absence", back_populates="student", cascade="all, delete-orphan"
    )
    notes = relationship("Note", back_populates="student", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Student id={self.id} email={self.email} level_id={self.level_id} group_id={self.group_id}>"


    def verify_password(self, password):
        return check_password_hash(self.password, password)
