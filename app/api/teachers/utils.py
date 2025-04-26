# Assuming TeacherSchema exists and excludes password on dump
from app.models.Schemas import TeacherSchema


def load_data(teacher_db_obj, many=False):
    """
    Load teacher data using the TeacherSchema. Excludes password.

    Parameters:
        teacher_db_obj: A Teacher SQLAlchemy object or a list of them.
        many: Boolean indicating if teacher_db_obj is a list.
    Returns:
        A dictionary or list of dictionaries representing the teacher(s).
    """
    # Ensure your TeacherSchema excludes 'password' field during serialization (dump)
    teacher_schema = TeacherSchema(many=many)
    data = teacher_schema.dump(teacher_db_obj)
    return data
