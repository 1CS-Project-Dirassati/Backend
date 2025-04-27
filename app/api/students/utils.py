# Import StudentSchema and ValidationError
from app.models.Schemas import StudentSchema
from marshmallow import ValidationError


def dump_data(db_obj, many=False):
    """
    Serialize database object(s) using the StudentSchema. Excludes password.

    Parameters:
        db_obj: A Student SQLAlchemy object or a list of them.
        many: Boolean indicating if db_obj is a list.
    Returns:
        A dictionary or list of dictionaries representing the student(s).
    """
    # Ensure your StudentSchema excludes 'password' field during serialization (dump)
    # This should be configured in the Schema definition itself (e.g., exclude=('password_hash',))
    student_schema = StudentSchema(many=many)
    data = student_schema.dump(db_obj)
    return data


# --- Added standard load_data function ---
def load_data(data: dict, many=False, partial=False, instance=None):
    """
    Load (validate and deserialize) data using the StudentSchema, optionally into an existing instance.

    Parameters:
        data: A dictionary or list of dictionaries representing student data.
        many: Boolean indicating if data is a list.
        partial: Boolean indicating if partial loading (like for updates) is allowed.
                 Ensure the schema correctly handles partial loading, potentially
                 excluding fields not meant for update (like email, password_hash, parent_id).
        instance: An existing SQLAlchemy object (or list) to load data into.
                  Required for updates to work correctly with SQLAlchemy session tracking.
    Returns:
        A Student SQLAlchemy object or a list of them (either new or the updated instance).
        *Note*: For creation (instance=None), you might adjust this or the schema
        if you only need a validated dict back instead of a new, detached instance.
        Current implementation assumes schema's load returns a model instance.
    Raises:
        ValidationError: If the input data is invalid according to the schema.
    """
    # Instantiate the schema, passing 'many' and 'partial' flags
    # The schema definition should handle field exclusion (e.g., password on load/dump)
    # and potentially which fields are allowed during partial updates.
    student_schema = StudentSchema(many=many, partial=partial)

    # Deserialize the dictionary data into SQLAlchemy object(s)
    # Pass the instance if provided. Raise ValidationError if data is invalid.
    # Ensure schema handles 'password' field correctly (e.g., load_only=True)
    # Ensure schema excludes fields like 'email', 'parent_id' if partial=True and instance is provided
    loaded_data = student_schema.load(data, instance=instance, partial=partial)
    return loaded_data
