from app import db

Column = db.Column
Model = db.Model
relationship = db.relationship


from .Admin import Admin
from .Absence import Absence
from .Chat import Chat
from .Fee import Fee
from .Group import Group
from .Level import Level
from .Parent import Parent
from .Session import Session
from .Student import Student
from .Teacher import Teacher
from .Lesson import Cours as Lesson
from .Message import Message
from .Module import Module
from .Note import Note
from .Notification import Notification
from .Salle import Salle
from .Semester import Semester
from .TeachingUnit import TeachingUnit
from .Teachings import Teachings


__all__ = [
    "Admin",
    "Absence",
    "Chat",
    "Fee",
    "Group",
    "Level",
    "Parent",
    "Session",
    "Student",
    "Teacher",
    "Lesson",
    "Message",
    "Module",
    "Note",
    "Notification",
    "Salle",
    "Semester",
    "TeachingUnit",
    "Teachings",
]
