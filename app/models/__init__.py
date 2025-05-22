from app import db

Column = db.Column
Model = db.Model
relationship = db.relationship

# Importing all models for easier access
from .User import User
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
from .Notification import NotificationType
from .Salle import Salle
from .Semester import Semester
from .associations import (
    TeacherModuleAssociation,
    TeacherGroupAssociation,
)

# importing all schemas for easier access
from .Fee import FeeStatus

# importing all schemas for easier access
from .Schemas import (
    AdminSchema,
    AbsenceSchema,
    ChatSchema,
    FeeSchema,
    GroupSchema,
    LessonSchema,
    ModuleSchema,
    MessageSchema,
    NoteSchema,
    NotificationSchema,
    ParentSchema,
    SalleSchema,
    SemesterSchema,
    StudentSchema,
    SessionSchema,
    TeacherSchema,
    TeacherModuleAssociationSchema,
    TeacherGroupAssociationSchema,
)

__all__ = [
    "User",
    "NotificationType",
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
    "TeacherModuleAssociation",
    "TeacherGroupAssociation",
    "AdminSchema",
    "AbsenceSchema",
    "ChatSchema",
    "FeeSchema",
    "GroupSchema",
    "LessonSchema",
    "ModuleSchema",
    "MessageSchema",
    "NoteSchema",
    "NotificationSchema",
    "ParentSchema",
    "SalleSchema",
    "SemesterSchema",
    "StudentSchema",
    "SessionSchema",
    "TeacherSchema",
    "TeacherModuleAssociationSchema",
    "TeacherGroupAssociationSchema",
    "FeeStatus",
]
