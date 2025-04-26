# Assuming your LevelSchema correctly maps the Level model
from app.models.Schemas import LevelSchema


def load_data(level_db_obj, many=False):
    """
    Load level data using the LevelSchema.

    Parameters:
        level_db_obj: A Level SQLAlchemy object or a list of them.
        many: Boolean indicating if level_db_obj is a list.
    Returns:
        A dictionary or list of dictionaries representing the level(s).
    """
    # Instantiate the schema, passing 'many=True' if handling a list
    level_schema = LevelSchema(many=many)
    # Serialize the database object(s) into dictionary format
    data = level_schema.dump(level_db_obj)
    return data
