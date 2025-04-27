# Assuming your LevelSchema correctly maps the Level model
from app.models.Schemas import LevelSchema
from marshmallow import ValidationError  # Import ValidationError


def dump_data(db_obj, many=False):
    """
    Serialize database object(s) using the LevelSchema.

    Parameters:
        db_obj: A Level SQLAlchemy object or a list of them.
        many: Boolean indicating if db_obj is a list.
    Returns:
        A dictionary or list of dictionaries representing the level(s).
    """
    # Instantiate the schema, passing 'many=True' if handling a list
    level_schema = LevelSchema(many=many)
    # Serialize the database object(s) into dictionary format
    data = level_schema.dump(db_obj)
    return data


# --- Added load_data function (similar to group/utils.py) ---
def load_data(data: dict, many=False, partial=False, instance=None):
    """
    Load (validate and deserialize) data using the LevelSchema, optionally into an existing instance.

    Parameters:
        data: A dictionary or list of dictionaries representing level data.
        many: Boolean indicating if data is a list.
        partial: Boolean indicating if partial loading (like for updates) is allowed.
        instance: An existing SQLAlchemy object (or list) to load data into.
                  Required for updates to work correctly with SQLAlchemy session tracking.
    Returns:
        A Level SQLAlchemy object or a list of them (either new or the updated instance).
    Raises:
        ValidationError: If the input data is invalid according to the schema.
    """
    # Instantiate the schema, passing 'many' and 'partial' flags
    level_schema = LevelSchema(many=many, partial=partial)

    # Deserialize the dictionary data into SQLAlchemy object(s)
    # Pass the instance if provided. Raise ValidationError if data is invalid.
    loaded_data = level_schema.load(
        data, instance=instance, partial=partial  # Ensure partial is passed here too
    )
    return loaded_data
