from app import ma
from app.models import (
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


class AdminSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Admin
        load_instance = True


class AbsenceSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Absence
        load_instance = True
        include_fk=True


class ChatSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Chat
        load_instance = True


class FeeSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Fee
        load_instance = True


class GroupSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Group
        load_instance = True
        include_fk = True


class LessonSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Lesson
        load_instance = True


class LevelSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Level
        load_instance = True


class ModuleSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Module
        load_instance = True
        include_fk=True


class NoteSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Note
        load_instance = True
        include_fk=True



class NotificationSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Notification
        load_instance = True


class ParentSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Parent
        load_instance = True
        load_only = ["password"]


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
        include_fk=True
        load_only = ["password"]
        dump_only = ["id", ]

class TeacherSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Teacher
        load_instance = True
        include_fk = True
        load_only = ["password"]


class TeacherModuleAssociationSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = TeacherModuleAssociation
        load_instance = True


class TeacherGroupAssociationSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = TeacherGroupAssociation
        load_instance = True




class SessionSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Session
        load_instance = True
        include_fk = True
class MessageSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Message
        load_instance = True
