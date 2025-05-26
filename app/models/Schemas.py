from app import ma
from app.models import (
    NoteType,
    NotificationType,
    Admin,
    Absence,
    Chat,
    Fee,
    Group,
    Level,
    Lesson,
    Module,
    Message,
    Note,
    Notification,
    Parent,
    Salle,
    Semester,
    Student,
    Session,
    Teacher,
    TeacherModuleAssociation,
    TeacherGroupAssociation,
)
from .TimeSlot import TimeSlot
from marshmallow import fields
from .Fee import FeeStatus


class AdminSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Admin
        load_instance = True
        include_fk = True
        load_only = ["password"]
        dump_only = ["id", "created_at", "updated_at", "user_type"]


class AbsenceSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Absence
        load_instance = True
        include_fk = True


class ChatSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Chat
        load_instance = True
        include_fk = True


class FeeSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Fee
        load_instance = True
        include_fk = True

    status = fields.Enum(FeeStatus, by_value=True)


class GroupSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Group
        load_instance = True
        include_fk = True


class LessonSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Lesson
        load_instance = True
        include_fk = True


class LevelSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Level
        load_instance = True


class ModuleSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Module
        load_instance = True
        include_fk = True


class NoteSchema(ma.SQLAlchemyAutoSchema):
    type = fields.Enum(NoteType, by_value=False)

    class Meta:
        model = Note
        load_instance = True
        include_fk = True


class NotificationSchema(ma.SQLAlchemyAutoSchema):
    notification_type = fields.Enum(NotificationType, by_value=False)

    class Meta:
        model = Notification
        load_instance = True
        include_fk = True


class ParentSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Parent
        load_instance = True
        load_only = ["password"]
        dump_only = ["id", "created_at", "updated_at", "user_type"]


class SalleSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Salle
        load_instance = True


class SemesterSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Semester
        load_instance = True
        include_fk = True


class StudentSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Student
        load_instance = True
        include_fk = True
        load_only = ["password"]
        dump_only = ["id", "created_at", "updated_at", "user_type"]


class TeacherSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Teacher
        load_instance = True
        include_fk = True
        load_only = ["password"]
        dump_only = ["id", "created_at", "updated_at", "user_type"]


class TeacherModuleAssociationSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = TeacherModuleAssociation
        load_instance = True
        include_fk = True


class TeacherGroupAssociationSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = TeacherGroupAssociation
        load_instance = True
        include_fk = True


class SessionSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Session
        load_instance = True
        include_fk = True

    time_slot = fields.Enum(TimeSlot, by_value=True)


class MessageSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Message
        load_instance = True
        include_fk = True
        dump_only = ("id", "created_at")
        load_only = ("chat_id", "content")
