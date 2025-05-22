from app import db
from datetime import datetime, timezone
from . import (
    Column,
    Model,
)  # Assuming 'relationship' is not directly used by User model itself
from werkzeug.security import check_password_hash
from sqlalchemy.orm import relationship


class User(Model):
    """
    Base model for all user types in the system.
    This class is intended to be abstract and should not be instantiated directly.
    """

    __tablename__ = "user"

    id = Column(db.Integer, primary_key=True)  # This is the central ID
    first_name = Column(db.String(50), nullable=True)
    last_name = Column(db.String(50), nullable=True)
    email = Column(db.String(100), unique=True, nullable=False, index=True)
    password = Column(db.String(200), nullable=False)  # Stores pre-hashed password
    user_type = Column(db.String(50), nullable=False)  # Discriminator column

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

    notifications = relationship(
        "Notification", back_populates="recipient", cascade="all, delete-orphan"
    )
    __mapper_args__ = {
        # No 'polymorphic_identity' for User, making it abstract in the hierarchy.
        # SQLAlchemy will not allow creating or loading instances of 'User' directly.
        # It will only permit instances of its subclasses (Admin, Parent, etc.).
        "polymorphic_on": user_type
    }


    def verify_password(self, password_to_check):
        return check_password_hash(self.password, password_to_check)

    def __repr__(self):
        # This repr might not be hit if User cannot be instantiated,
        # but subclasses will have their own.
        return (
            f"<User (Abstract) id={self.id} email={self.email} type='{self.user_type}'>"
        )
