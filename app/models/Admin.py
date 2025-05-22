from app import db
from . import Model, Column # Assuming these are from your models/__init__.py
from . import User  # Import the base User model

class Admin(User):
    """Represents an administrator user with system privileges."""

    __tablename__ = "admin"

    # user_id is this table's PK and FK to user.id
    id = Column(db.Integer, db.ForeignKey("user.id"), primary_key=True)

    # Admin-specific fields
    phone_number = Column(db.String(20), nullable=False)
    is_super_admin = Column(db.Boolean, default=False, nullable=False)

    # Common fields (email, password, names, timestamps) are inherited from User.

    __mapper_args__ = {
        'polymorphic_identity': 'admin',  # Value for User.user_type
    }


    def __repr__(self):
        # self.id and self.email are accessible from the joined User table
        return f"<Admin id={self.id} email={self.email} is_super_admin={self.is_super_admin}>"

    # verify_password method is inherited from User
