# Import NotificationSchema and ValidationError
# Ensure NotificationSchema handles polymorphic fields and Enum correctly
from app.models.Schemas import NotificationSchema
from marshmallow import ValidationError


def dump_data(db_obj, many=False):
    """
    Serialize database object(s) using the NotificationSchema.
    """
    notification_schema = NotificationSchema(many=many)
    data = notification_schema.dump(db_obj)
    return data


def load_data(data, many=False, partial=False, instance=None):
    """
    Load (validate and deserialize) data using the NotificationSchema.
    """
    notification_schema = NotificationSchema(many=many, partial=partial)
    loaded_data = notification_schema.load(data, instance=instance, partial=partial)
    return loaded_data
