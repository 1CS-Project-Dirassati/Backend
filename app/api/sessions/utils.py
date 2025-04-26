# Assuming SessionSchema exists and correctly maps the Session model
from app.models.Schemas import SessionSchema


def load_data(session_db_obj, many=False):
    """
    Load session data using the SessionSchema.

    Parameters:
        session_db_obj: A Session SQLAlchemy object or a list of them.
        many: Boolean indicating if session_db_obj is a list.
    Returns:
        A dictionary or list of dictionaries representing the session(s).
    """
    # Instantiate the schema, passing 'many=True' if handling a list
    session_schema = SessionSchema(many=many)
    # Serialize the database object(s) into dictionary format
    data = session_schema.dump(session_db_obj)
    return data
