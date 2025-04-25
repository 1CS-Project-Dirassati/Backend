# Assuming your GroupSchema correctly maps the Group model
from models import GroupSchema

def load_data(group_db_obj, many=False):
    """
    Load group data using the GroupSchema.

    Parameters:
        group_db_obj: A Group SQLAlchemy object or a list of them.
        many: Boolean indicating if group_db_obj is a list.
    Returns:
        A dictionary or list of dictionaries representing the group(s).
    """
    # Instantiate the schema, passing 'many=True' if handling a list
    group_schema = GroupSchema(many=many)
    # Serialize the database object(s) into dictionary format
    data = group_schema.dump(group_db_obj)
    return data

