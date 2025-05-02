from app import db
from datetime import datetime, timezone
from . import Column, Model, relationship
from werkzeug.security import generate_password_hash, check_password_hash


class Teacher(Model):
    """Represents a teacher responsible for modules and groups."""

    __tablename__ = "teacher"

    id = Column(db.Integer, primary_key=True)
    first_name = Column(db.String(50), nullable=True)
    last_name = Column(db.String(50), nullable=True)
    email = Column(db.String(100), unique=True, nullable=False, index=True)
    password = Column(db.String(200), nullable=False)
    phone_number = Column(db.String(20), nullable=False)
    address = Column(db.String(255), nullable=True)
    profile_picture = Column(
        db.String(255), default="static/images/default_profile.png"
    )
    module_key = Column(db.String(100), nullable=True)
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
    modules = relationship("Module", back_populates="teacher")
    assigned_groups = relationship(
        "Teachings",
        back_populates="teacher",
        cascade="all, delete-orphan",
    )
    sessions = relationship("Session", back_populates="teacher")
    cours = relationship(
        "Cours", back_populates="teacher", cascade="all, delete-orphan"
    )
    notes = relationship("Note", back_populates="teacher", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Teacher id={self.id} email={self.email}>"

   

    def verify_password(self, password):
        return check_password_hash(self.password, password)
