# Assuming SessionSchema exists and correctly maps the Session model
from app.models.Schemas import SessionSchema
from marshmallow import ValidationError  # Import ValidationError


def dump_data(db_obj, many=False):
    """
    Serialize database object(s) using the SessionSchema.

    Parameters:
        db_obj: A Session SQLAlchemy object or a list of them.
        many: Boolean indicating if db_obj is a list.
    Returns:
        A dictionary or list of dictionaries representing the session(s).
    """
    # Instantiate the schema, passing 'many=True' if handling a list
    session_schema = SessionSchema(many=many)
    # Serialize the database object(s) into dictionary format
    data = session_schema.dump(db_obj)
    return data


# --- Added load_data function (similar to group/utils.py) ---
def load_data(data: dict, many=False, partial=False, instance=None):
    """
    Load (validate and deserialize) data using the SessionSchema, optionally into an existing instance.

    Parameters:
        data: A dictionary or list of dictionaries representing session data.
        many: Boolean indicating if data is a list.
        partial: Boolean indicating if partial loading (like for updates) is allowed.
        instance: An existing SQLAlchemy object (or list) to load data into.
                  Required for updates to work correctly with SQLAlchemy session tracking.
    Returns:
        A Session SQLAlchemy object or a list of them (either new or the updated instance).
    Raises:
        ValidationError: If the input data is invalid according to the schema.
    """
    # Instantiate the schema, passing 'many' and 'partial' flags
    # Add 'unknown=EXCLUDE' if you want to ignore unexpected fields in input data
    session_schema = SessionSchema(many=many, partial=partial)  # unknown=EXCLUDE

    # Deserialize the dictionary data into SQLAlchemy object(s)
    # Pass the instance if provided. Raise ValidationError if data is invalid.
    loaded_data = session_schema.load(
        data, instance=instance, partial=partial  # Ensure partial is passed here too
    )
    return loaded_data
