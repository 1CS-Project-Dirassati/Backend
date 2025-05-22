from app import db
from . import Column, Model, relationship


class TeacherModuleAssociation(Model):
    """Association table linking Teachers to Modules (Many-to-Many)."""

    __tablename__ = "teacher_module_association"

    teacher_id = Column(db.Integer, db.ForeignKey("teacher.id"), index=True)
    module_id = Column(db.Integer, db.ForeignKey("module.id"), index=True)
    __table_args__ = (db.PrimaryKeyConstraint("teacher_id", "module_id"),)

    teacher = relationship("Teacher", back_populates="module_associations")
    module = relationship("Module", back_populates="teacher_associations")

    def __repr__(self):
        return f"<TeacherModuleAssociation teacher_id={self.teacher_id} module_id={self.module_id}>"


class TeacherGroupAssociation(Model):
    """Association table linking Teachers to Groups (Many-to-Many)."""

    __tablename__ = "teacher_group_association"

    teacher_id = Column(db.Integer, db.ForeignKey("teacher.id"), index=True)
    group_id = Column(db.Integer, db.ForeignKey("group.id"), index=True)
    __table_args__ = (db.PrimaryKeyConstraint("teacher_id", "group_id"),)

    teacher = relationship("Teacher", back_populates="group_associations")
    group = relationship("Group", back_populates="teacher_associations")

    def __repr__(self):
        return f"<TeacherGroupAssociation teacher_id={self.teacher_id} group_id={self.group_id}>"
