from app import db
from . import Column, Model, relationship


class Group(Model):
    """Represents a group of students within a specific level."""

    __tablename__ = "group"

    id = Column(db.Integer, primary_key=True)
    name = Column(db.String(50), nullable=False)
    level_id = Column(db.Integer, db.ForeignKey("level.id"), nullable=False, index=True)

    # Relationships
    level = relationship("Level", back_populates="groups")
    students = relationship("Student", back_populates="group")
    teacher_associations = relationship(
        "TeacherGroupAssociation", back_populates="group", cascade="all, delete-orphan"
    )
    sessions = relationship("Session", back_populates="group")

    def __init__(self, name, level_id):
        self.name = name
        self.level_id = level_id

    def __repr__(self):
        return f"<Group id={self.id} name={self.name} level_id={self.level_id}>"
