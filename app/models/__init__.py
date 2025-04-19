from app import db

from . import (
    Admin,
    Absence,
    Chat,
    Fee,
    Group,
    Level,
    Parent,
    Session,
    Student,
    Subject,
    Teacher,
    Lesson,
    Message,
    Module,
    Note,
    Notification,
    Salle,
    Semester,
    TeachingUnit,
    Teachings,
)


Column = db.Column
Model = db.Model
relationship = db.relationship

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
    "Subject",
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
