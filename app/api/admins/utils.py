# Import AdminSchema and ValidationError
from app.models.Schemas import AdminSchema
from marshmallow import ValidationError


def dump_data(db_obj, many=False):
    """
    Serialize database object(s) using the AdminSchema. Excludes password.

    Parameters:
        db_obj: An Admin SQLAlchemy object or a list of them.
        many: Boolean indicating if db_obj is a list.
    Returns:
        A dictionary or list of dictionaries representing the admin(s).
    """
    # Ensure AdminSchema excludes 'password_hash' field during serialization (dump)
    # Configure in Schema definition: exclude=('password_hash',)
    admin_schema = AdminSchema(many=many)
    data = admin_schema.dump(db_obj)
    return data


# --- Added standard load_data function ---
def load_data(data: dict, many=False, partial=False, instance=None):
    """
    Load (validate and deserialize) data using the AdminSchema, optionally into an existing instance.

    Parameters:
        data: A dictionary or list of dictionaries representing admin data.
        many: Boolean indicating if data is a list.
        partial: Boolean indicating if partial loading (like for updates) is allowed.
                 Ensure the schema correctly handles partial loading, potentially
                 excluding fields not meant for update (like email, password_hash).
                 For self-update, 'is_super_admin' should also be excluded.
        instance: An existing SQLAlchemy object (or list) to load data into.
                  Required for updates to work correctly with SQLAlchemy session tracking.
    Returns:
        An Admin SQLAlchemy object or a list of them (either new or the updated instance).
        *Note*: Assumes schema's load returns a model instance. Adjust if needed for creation.
    Raises:
        ValidationError: If the input data is invalid according to the schema.
    """
    # Instantiate the schema, passing 'many' and 'partial' flags.
    # Schema definition should handle field exclusion (e.g., password load_only=True)
    # and potentially which fields are allowed during partial updates (e.g., excluding 'is_super_admin' for self-update).
    # This might require different Schema instances for different update types if not handled in Meta.
    admin_schema = AdminSchema(many=many, partial=partial)

    # Deserialize the dictionary data into SQLAlchemy object(s).
    # Pass the instance if provided. Raise ValidationError if data is invalid.
    loaded_data = admin_schema.load(data, instance=instance, partial=partial)
    return loaded_data
