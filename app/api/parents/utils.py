# Assuming ParentSchema exists and excludes password on dump
from app.models.Schemas import ParentSchema


def load_data(parent_db_obj, many=False):
    """
    Load parent data using the ParentSchema. Excludes password.

    Parameters:
        parent_db_obj: A Parent SQLAlchemy object or a list of them.
        many: Boolean indicating if parent_db_obj is a list.
    Returns:
        A dictionary or list of dictionaries representing the parent(s).
    """
    # Ensure your ParentSchema excludes 'password' field during serialization (dump)
    parent_schema = ParentSchema(many=many)
    data = parent_schema.dump(parent_db_obj)
    return data
