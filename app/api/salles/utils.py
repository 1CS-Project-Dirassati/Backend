# Import SalleSchema and ValidationError
from app.models.Schemas import SalleSchema
from marshmallow import ValidationError


def dump_data(db_obj, many=False):
    """
    Serialize database object(s) using the SalleSchema.

    Parameters:
        db_obj: A Salle SQLAlchemy object or a list of them.
        many: Boolean indicating if db_obj is a list.
    Returns:
        A dictionary or list of dictionaries representing the salle(s).
    """
    salle_schema = SalleSchema(many=many)
    data = salle_schema.dump(db_obj)
    return data


def load_data(data, many=False, partial=False, instance=None):
    """
    Load (validate and deserialize) data using the SalleSchema, optionally into an existing instance.

    Parameters:
        data: A dictionary or list of dictionaries representing salle data.
        many: Boolean indicating if data is a list.
        partial: Boolean indicating if partial loading (like for updates) is allowed.
        instance: An existing SQLAlchemy object to load data into (for updates).
    Returns:
        A Salle SQLAlchemy object or a list of them.
    Raises:
        ValidationError: If the input data is invalid according to the schema.
    """
    salle_schema = SalleSchema(many=many, partial=partial)
    loaded_data = salle_schema.load(data, instance=instance, partial=partial)
    return loaded_data
