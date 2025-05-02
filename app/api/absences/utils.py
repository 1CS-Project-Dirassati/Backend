# Import AbsenceSchema and ValidationError
from app.models.Schemas import AbsenceSchema
from marshmallow import ValidationError


def dump_data(db_obj, many=False):
    """
    Serialize database object(s) using the AbsenceSchema.

    Parameters:
        db_obj: An Absence SQLAlchemy object or a list of them.
        many: Boolean indicating if db_obj is a list.
    Returns:
        A dictionary or list of dictionaries representing the absence(s).
    """
    absence_schema = AbsenceSchema(many=many)
    data = absence_schema.dump(db_obj)
    return data


def load_data(data, many=False, partial=False, instance=None):
    """
    Load (validate and deserialize) data using the AbsenceSchema, optionally into an existing instance.

    Parameters:
        data: A dictionary or list of dictionaries representing absence data.
        many: Boolean indicating if data is a list.
        partial: Boolean indicating if partial loading (like for updates) is allowed.
                 Ensure the schema correctly handles partial loading (e.g., only justified/reason).
        instance: An existing SQLAlchemy object to load data into (for updates).
    Returns:
        An Absence SQLAlchemy object or a list of them.
    Raises:
        ValidationError: If the input data is invalid according to the schema.
    """
    # Schema definition should handle field exclusion/inclusion based on context (create vs update)
    absence_schema = AbsenceSchema(many=many, partial=partial)
    loaded_data = absence_schema.load(data, instance=instance, partial=partial)
    return loaded_data
