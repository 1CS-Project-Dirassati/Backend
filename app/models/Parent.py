from app import db
from . import Column, Model, relationship
from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash


class Parent(Model):
    """Represents a parent or guardian of one or more students."""

    __tablename__ = "parent"

    id = Column(db.Integer, primary_key=True)
    first_name = Column(db.String(50), nullable=True)
    last_name = Column(db.String(50), nullable=True)
    email = Column(db.String(100), unique=True, nullable=False, index=True)
    is_email_verified = Column(db.Boolean, default=False, nullable=False)
    password = Column(db.String(200), nullable=False)
    phone_number = Column(db.String(20), nullable=False)
    is_phone_verified = Column(db.Boolean, default=False, nullable=False)
    address = Column(db.String(255), nullable=True)
    profile_picture = Column(
        db.String(255), default="static/images/default_profile.png"
    )
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
    students = relationship(
        "Student", back_populates="parent", cascade="all, delete-orphan"
    )
    fees = relationship("Fee", back_populates="parent", cascade="all, delete-orphan")
    notifications = relationship(
        "Notification", back_populates="parent", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Parent id={self.id} email={self.email}>"

    def __init__(
        self,
        email,
        password,
        phone_number,
        first_name=None,
        last_name=None,
    ):
        self.email = email
        self.password = generate_password_hash(password)
        self.phone_number = phone_number
        self.first_name = first_name
        self.last_name = last_name

    def verify_password(self, password):
        return check_password_hash(self.password, password)
