# Assuming AdminSchema exists and excludes password on dump
from app.models.Schemas import AdminSchema


def load_data(admin_db_obj, many=False):
    """
    Load admin data using the AdminSchema. Excludes password.

    Parameters:
        admin_db_obj: An Admin SQLAlchemy object or a list of them.
        many: Boolean indicating if admin_db_obj is a list.
    Returns:
        A dictionary or list of dictionaries representing the admin(s).
    """
    # Ensure your AdminSchema excludes 'password' field during serialization (dump)
    admin_schema = AdminSchema(many=many)
    data = admin_schema.dump(admin_db_obj)
    return data
