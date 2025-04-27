from app.models.Schemas import TeacherSchema
from marshmallow import ValidationError


def dump_data(db_obj, many=False):
    """
    Serialize database object(s) using the TeacherSchema. Excludes password.

    Parameters:
        db_obj: A Teacher SQLAlchemy object or a list of them.
        many: Boolean indicating if db_obj is a list.
    Returns:
        A dictionary or list of dictionaries representing the teacher(s).
    """
    # Ensure TeacherSchema excludes 'password_hash' field during serialization (dump)
    # Configure in Schema definition: exclude=('password_hash',)
    teacher_schema = TeacherSchema(many=many)
    data = teacher_schema.dump(db_obj)
    return data


# --- Added standard load_data function ---
def load_data(data: dict, many=False, partial=False, instance=None):
    """
    Load (validate and deserialize) data using the TeacherSchema, optionally into an existing instance.

    Parameters:
        data: A dictionary or list of dictionaries representing teacher data.
        many: Boolean indicating if data is a list.
        partial: Boolean indicating if partial loading (like for updates) is allowed.
                 Ensure the schema correctly handles partial loading, potentially
                 excluding fields not meant for update (like email, password_hash).
        instance: An existing SQLAlchemy object (or list) to load data into.
                  Required for updates to work correctly with SQLAlchemy session tracking.
    Returns:
        A Teacher SQLAlchemy object or a list of them (either new or the updated instance).
        *Note*: Assumes schema's load returns a model instance. Adjust if needed for creation.
    Raises:
        ValidationError: If the input data is invalid according to the schema.
    """
    # Instantiate the schema, passing 'many' and 'partial' flags.
    # Schema definition should handle field exclusion (e.g., password load_only=True)
    # and potentially which fields are allowed during partial updates.
    teacher_schema = TeacherSchema(many=many, partial=partial)

    # Deserialize the dictionary data into SQLAlchemy object(s).
    # Pass the instance if provided. Raise ValidationError if data is invalid.
    loaded_data = teacher_schema.load(data, instance=instance, partial=partial)
    return loaded_data
