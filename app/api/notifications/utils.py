# Import NotificationSchema and ValidationError
from app.models.Schemas import NotificationSchema
from marshmallow import ValidationError


def dump_data(db_obj, many=False):
    """
    Serialize database object(s) using the NotificationSchema.

    Parameters:
        db_obj: A Notification SQLAlchemy object or a list of them.
        many: Boolean indicating if db_obj is a list.
    Returns:
        A dictionary or list of dictionaries representing the notification(s).
    """
    # Ensure schema handles Enum serialization correctly (e.g., to string value)
    notification_schema = NotificationSchema(many=many)
    data = notification_schema.dump(db_obj)
    return data


def load_data(data, many=False, partial=False, instance=None):
    """
    Load (validate and deserialize) data using the NotificationSchema, optionally into an existing instance.
    Used for creation (Admin) and PATCH validation (Parent) in this context.

    Parameters:
        data: A dictionary or list of dictionaries representing notification data.
        many: Boolean indicating if data is a list.
        partial: Boolean indicating if partial loading (like for updates) is allowed.
                 Ensure schema handles partial fields (e.g., only 'is_read').
        instance: An existing SQLAlchemy object to load data into (for updates).
    Returns:
        A Notification SQLAlchemy object or a list of them.
    Raises:
        ValidationError: If the input data is invalid according to the schema.
    """
    # Schema definition should handle field exclusion/inclusion based on context
    notification_schema = NotificationSchema(many=many, partial=partial)
    loaded_data = notification_schema.load(data, instance=instance, partial=partial)
    return loaded_data
