from app import db
from datetime import datetime, timezone
from . import Column, Model, relationship
import enum


# fee enum
class FeeStatus(enum.Enum):
    UNPAID = "unpaid"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"


# fee model
class Fee(Model):
    """Represents a fee owed by a parent."""

    __tablename__ = "fee"

    id = Column(db.Integer, primary_key=True)
    parent_id = Column(
        db.Integer, db.ForeignKey("parent.id"), nullable=False, index=True
    )
    amount = Column(db.Float, nullable=False)
    description = Column(db.String(255), nullable=True)
    due_date = Column(db.Date, nullable=False)
    status = Column(
        db.Enum(FeeStatus, name="fee_status_enum"),
        nullable=False,
        default=FeeStatus.UNPAID,
        index=True,
    )
    payment_date = Column(db.Date, nullable=True)
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

    parent = relationship("Parent", back_populates="fees")

    def __repr__(self):
        return f"<Fee id={self.id} amount={self.amount} status={self.status.value} parent_id={self.parent_id}>"
