from app import db
from . import (
    Model,
    Column,
    relationship,
)  # Assuming these are from your models/__init__.py
from . import User  # Import the base User model


class Parent(User):
    """Represents a parent or guardian of one or more students."""

    __tablename__ = "parent"

    id = Column(db.Integer, db.ForeignKey("user.id"), primary_key=True)

    # Parent-specific fields
    phone_number = Column(db.String(20), nullable=False)
    is_email_verified = Column(db.Boolean, default=False, nullable=False)
    is_phone_verified = Column(db.Boolean, default=False, nullable=False)
    address = Column(db.String(255), nullable=True)
    profile_picture = Column(
        db.String(255), default="static/images/default_profile.png"
    )

    __mapper_args__ = {
        "polymorphic_identity": "parent",
    }

    # Relationships: Foreign keys in related tables (Student, Fee, Notification)
    # will need to point to parent.user_id if they previously pointed to parent.id.
    students = relationship(
        "Student",
        foreign_keys="[Student.parent_id]",  # Explicitly state FK if not standard
        back_populates="parent",
        cascade="all, delete-orphan",
    )
    fees = relationship("Fee", back_populates="parent", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Parent id={self.id} email={self.email}>"

    # verify_password method is inherited from User
