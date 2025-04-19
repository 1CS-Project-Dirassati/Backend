from app import db
from . import Column, Model, relationship


class Level(Model):
    """Represents an academic or study level."""

    __tablename__ = "level"

    id = Column(db.Integer, primary_key=True)
    name = Column(db.String(50), nullable=False, unique=True)
    description = Column(db.String(255), nullable=True)

    # Relationships
    groups = relationship("Group", back_populates="level")
    module_associations = relationship(
        "LevelModuleAssociation", back_populates="level", cascade="all, delete-orphan"
    )
    students = relationship("Student", back_populates="level")
    semesters = relationship("Semester", back_populates="level")

    def __repr__(self):
        return f"<Level id={self.id} name={self.name}>"
