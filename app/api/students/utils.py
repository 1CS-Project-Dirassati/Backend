# Assuming StudentSchema exists and excludes password on dump
from app.models.Schemas import StudentSchema

def load_data(student_db_obj, many=False):
    """
    Load student data using the StudentSchema. Excludes password.

    Parameters:
        student_db_obj: A Student SQLAlchemy object or a list of them.
        many: Boolean indicating if student_db_obj is a list.
    Returns:
        A dictionary or list of dictionaries representing the student(s).
    """
    # Ensure your StudentSchema excludes 'password' field during serialization (dump)
    student_schema = StudentSchema(many=many)
    data = student_schema.dump(student_db_obj)
    return data
