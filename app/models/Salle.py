from app import db
from . import Column, Model, relationship


class Salle(Model):
    """Classroom/room for sessions"""

    __tablename__ = "salle"

    id = Column(db.Integer, primary_key=True)
    name = Column(db.String(50), nullable=False, unique=True)
    capacity = Column(db.Integer, nullable=False)
    location = Column(db.String(100), nullable=True)

    sessions = relationship("Session", back_populates="salle")

    def __repr__(self):
        return f"<Salle id={self.id} name={self.name}>"
