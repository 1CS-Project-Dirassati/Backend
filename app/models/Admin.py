from app import db
from datetime import datetime, timezone
from . import Column, Model
from werkzeug.security import generate_password_hash, check_password_hash


class Admin(Model):
    """Represents an administrator user with system privileges."""

    __tablename__ = "admin"

    id = Column(db.Integer, primary_key=True)
    first_name = Column(db.String(50), nullable=True)
    last_name = Column(db.String(50), nullable=True)
    email = Column(db.String(100), unique=True, nullable=False, index=True)
    password = Column(db.String(200), nullable=False)  # Store HASHED passwords
    phone_number = Column(db.String(20), nullable=False)
    is_super_admin = Column(db.Boolean, default=False, nullable=False)
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

    def __repr__(self):
        return f"<Admin id={self.id} email={self.email}>"

    @property
    def password(self):
        raise AttributeError("password is not a readable attribute")

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)
