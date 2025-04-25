from app import db
from . import Column, Model, relationship


class Teachings(Model):
    """Association table linking Teachers to the Groups they teach (Many-to-Many)."""

    __tablename__ = "teacher_group_association"

    teacher_id = Column(db.Integer, db.ForeignKey("teacher.id"), index=True)
    group_id = Column(db.Integer, db.ForeignKey("group.id"), index=True)
    __table_args__ = (db.PrimaryKeyConstraint("teacher_id", "group_id"),)

    teacher = relationship("Teacher", back_populates="assigned_groups")
    group = relationship("Group", back_populates="teacher_associations")

    def __repr__(self):
        return f"<teachings teacher_id={self.teacher_id} group_id={self.group_id}>"
