# Import ModuleSchema and ValidationError
from app.models.Schemas import ModuleSchema
from marshmallow import ValidationError


def dump_data(db_obj, many=False):
    """
    Serialize database object(s) using the ModuleSchema.

    Parameters:
        db_obj: A Module SQLAlchemy object or a list of them.
        many: Boolean indicating if db_obj is a list.
    Returns:
        A dictionary or list of dictionaries representing the module(s).
    """
    module_schema = ModuleSchema(many=many)
    data = module_schema.dump(db_obj)
    return data


def load_data(data, many=False, partial=False, instance=None):
    """
    Load (validate and deserialize) data using the ModuleSchema, optionally into an existing instance.

    Parameters:
        data: A dictionary or list of dictionaries representing module data.
        many: Boolean indicating if data is a list.
        partial: Boolean indicating if partial loading (like for updates) is allowed.
        instance: An existing SQLAlchemy object to load data into (for updates).
    Returns:
        A Module SQLAlchemy object or a list of them.
    Raises:
        ValidationError: If the input data is invalid according to the schema.
    """
    module_schema = ModuleSchema(many=many, partial=partial)
    loaded_data = module_schema.load(data, instance=instance, partial=partial)
    return loaded_data
