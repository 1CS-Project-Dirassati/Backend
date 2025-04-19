from app import db
from . import Column, Model, relationship


class TeachingUnit(Model):
    """Association table linking Levels to the Modules taught in them (Many-to-Many)."""

    __tablename__ = "level_module_association"

    level_id = Column(db.Integer, db.ForeignKey("level.id"), index=True)
    module_id = Column(db.Integer, db.ForeignKey("module.id"), index=True)
    __table_args__ = (db.PrimaryKeyConstraint("level_id", "module_id"),)

    level = relationship("Level", back_populates="module_associations")
    module = relationship("Module", back_populates="level_associations")

    def __repr__(self):
        return f"<TeachingUnit level_id={self.level_id} module_id={self.module_id}>"
