# Import MessageSchema and ValidationError
from app.models.Schemas import MessageSchema
from marshmallow import ValidationError


def dump_data(db_obj, many=False):
    """
    Serialize database object(s) using the MessageSchema.

    Parameters:
        db_obj: A Message SQLAlchemy object or a list of them.
        many: Boolean indicating if db_obj is a list.
    Returns:
        A dictionary or list of dictionaries representing the message(s).
    """
    message_schema = MessageSchema(many=many)
    data = message_schema.dump(db_obj)
    return data


def load_data(data, many=False, partial=False, instance=None):
    """
    Load (validate and deserialize) data using the MessageSchema, optionally into an existing instance.

    Parameters:
        data: A dictionary or list of dictionaries representing message data.
        many: Boolean indicating if data is a list.
        partial: Boolean indicating if partial loading (like for updates) is allowed.
                 Ensure schema handles partial fields (e.g., only 'content').
        instance: An existing SQLAlchemy object to load data into (for updates).
    Returns:
        A Message SQLAlchemy object or a list of them.
    Raises:
        ValidationError: If the input data is invalid according to the schema.
    """
    # Schema definition should handle field exclusion/inclusion based on context
    message_schema = MessageSchema(many=many, partial=partial)
    loaded_data = message_schema.load(data, instance=instance, partial=partial)
    return loaded_data
