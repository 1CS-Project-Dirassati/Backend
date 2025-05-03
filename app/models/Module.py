from app import db
from . import Column, Model, relationship


class Module(Model):
    """Represents a subject or course module taught."""

    __tablename__ = "module"

    id = Column(db.Integer, primary_key=True)
    name = Column(db.String(50), nullable=False)
    description = Column(db.String(255), nullable=True)
    level_id = Column(db.Integer, db.ForeignKey("level.id"), nullable=False, index=True)

    # Relationships
    teacher_associations = relationship(
        "TeacherModuleAssociation", back_populates="module", cascade="all, delete-orphan"
    )
    level = relationship("Level", back_populates="modules")
    sessions = relationship("Session", back_populates="module")
    cours = relationship("Cours", back_populates="module", cascade="all, delete-orphan")
    notes = relationship("Note", back_populates="module", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Module id={self.id} name={self.name}>"
