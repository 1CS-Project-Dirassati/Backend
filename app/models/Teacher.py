from app import db
from . import (
    Model,
    Column,
    relationship,
)  # Assuming these are from your models/__init__.py
from . import User  # Import the base User model


class Teacher(User):
    """Represents a teacher responsible for modules and groups."""

    __tablename__ = "teacher"

    id = Column(db.Integer, db.ForeignKey("user.id"), primary_key=True)

    # Teacher-specific fields
    phone_number = Column(db.String(20), nullable=False)
    address = Column(db.String(255), nullable=True)
    profile_picture = Column(
        db.String(255), default="static/images/default_profile.png"
    )

    __mapper_args__ = {
        "polymorphic_identity": "teacher",
    }

    # Relationships: Foreign keys in related tables will need to point to teacher.user_id
    module_associations = relationship(
        "TeacherModuleAssociation",
        back_populates="teacher",
        cascade="all, delete-orphan",
    )
    group_associations = relationship(
        "TeacherGroupAssociation",
        back_populates="teacher",
        cascade="all, delete-orphan",
    )
    sessions = relationship("Session", back_populates="teacher")
    cours = relationship(  # Typo 'Cours' kept as per original
        "Cours", back_populates="teacher", cascade="all, delete-orphan"
    )
    notes = relationship("Note", back_populates="teacher", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Teacher id={self.id} email={self.email}>"

    # verify_password method is inherited from User
