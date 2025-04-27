# Import NoteSchema and ValidationError
from app.models.Schemas import NoteSchema
from marshmallow import ValidationError


def dump_data(db_obj, many=False):
    """
    Serialize database object(s) using the NoteSchema.

    Parameters:
        db_obj: A Note SQLAlchemy object or a list of them.
        many: Boolean indicating if db_obj is a list.
    Returns:
        A dictionary or list of dictionaries representing the note(s).
    """
    # Consider adding context={'include_relations': True} if schema handles enrichment
    note_schema = NoteSchema(many=many)
    data = note_schema.dump(db_obj)
    return data


# --- Added standard load_data function ---
def load_data(data: dict, many=False, partial=False, instance=None):
    """
    Load (validate and deserialize) data using the NoteSchema, optionally into an existing instance.

    Parameters:
        data: A dictionary or list of dictionaries representing note data.
        many: Boolean indicating if data is a list.
        partial: Boolean indicating if partial loading (like for updates) is allowed.
                 Ensure the schema correctly handles partial loading, potentially
                 excluding fields not meant for update (like student_id, module_id, teacher_id).
        instance: An existing SQLAlchemy object (or list) to load data into.
                  Required for updates to work correctly with SQLAlchemy session tracking.
    Returns:
        A Note SQLAlchemy object or a list of them (either new or the updated instance).
        *Note*: Assumes schema's load returns a model instance. Adjust if needed for creation.
    Raises:
        ValidationError: If the input data is invalid according to the schema.
    """
    # Instantiate the schema, passing 'many' and 'partial' flags.
    # Schema definition should handle field exclusion (e.g., teacher_id load_only=True or exclude on create)
    # and potentially which fields are allowed during partial updates (e.g., using 'only' in constructor).
    note_schema = NoteSchema(many=many, partial=partial)

    # Deserialize the dictionary data into SQLAlchemy object(s).
    # Pass the instance if provided. Raise ValidationError if data is invalid.
    loaded_data = note_schema.load(data, instance=instance, partial=partial)
    return loaded_data
