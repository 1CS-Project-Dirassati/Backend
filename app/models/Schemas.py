from app import ma


class AdminSchema(ma.Schema):
    class Meta:
        fields = (
            "id",
            "first_name",
            "last_name",
            "email",
            "phone_number",
            "is_super_admin",
            "created_at",
            "updated_at",
        )


class AbsenceSchema(ma.Schema):
    class Meta:
        fields = (
            "id",
            "student_id",
            "session_id",
            "justified",
            "reason",
            "recorded_at",
        )


class ChatSchema(ma.Schema):
    class Meta:
        fields = (
            "id",
            "parent_id",
            "teacher_id",
            "created_at",
        )


class FeeSchema(ma.Schema):
    class Meta:
        fields = (
            "id",
            "parent_id",
            "amount",
            "description",
            "due_date",
            "status",
            "payment_date",
            "created_at",
            "updated_at",
        )


class GroupSchema(ma.Schema):
    class Meta:
        fields = (
            "id",
            "name",
            "level_id",
        )


class CoursSchema(ma.Schema):
    class Meta:
        fields = (
            "id",
            "title",
            "content",
            "module_id",
            "teacher_id",
            "created_at",
        )


class LevelSchema(ma.Schema):
    class Meta:
        fields = (
            "id",
            "name",
            "description",
        )


class ModuleSchema(ma.Schema):
    class Meta:
        fields = (
            "id",
            "name",
            "description",
            "teacher_id",
        )


class NoteSchema(ma.Schema):
    class Meta:
        fields = (
            "id",
            "student_id",
            "module_id",
            "teacher_id",
            "value",
            "comment",
            "created_at",
        )


class NotificationSchema(ma.Schema):
    class Meta:
        fields = (
            "id",
            "parent_id",
            "message",
            "notification_type",
            "is_read",
            "created_at",
        )


class ParentSchema(ma.Schema):
    class Meta:
        fields = (
            "id",
            "first_name",
            "last_name",
            "email",
            "is_email_verified",
            "phone_number",
            "is_phone_verified",
            "address",
            "profile_picture",
            "created_at",
            "updated_at",
        )


class SalleSchema(ma.Schema):
    class Meta:
        fields = (
            "id",
            "name",
            "capacity",
            "location",
        )


class SemesterSchema(ma.Schema):
    class Meta:
        fields = (
            "id",
            "name",
            "level_id",
            "start_date",
            "duration",
            "created_at",
            "updated_at",
        )


class StudentSchema(ma.Schema):
    class Meta:
        fields = (
            "id",
            "first_name",
            "last_name",
            "email",
            "level_id",
            "group_id",
            "is_approved",
            "parent_id",
            "docs_url",
            "created_at",
            "updated_at",
        )


class TeacherSchema(ma.Schema):
    class Meta:
        fields = (
            "id",
            "first_name",
            "last_name",
            "email",
            "phone_number",
            "address",
            "profile_picture",
            "module_key",
            "created_at",
            "updated_at",
        )


class TeachingsSchema(ma.Schema):
    class Meta:
        fields = (
            "teacher_id",
            "group_id",
        )


class TeachingUnitSchema(ma.Schema):
    class Meta:
        fields = (
            "level_id",
            "module_id",
        )
