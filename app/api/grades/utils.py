# Assuming NoteSchema exists
from app.models.Schemas import NoteSchema


def load_data(note_db_obj, many=False):
    """
    Load note (grade) data using the NoteSchema.

    Parameters:
        note_db_obj: A Note SQLAlchemy object or a list of them.
        many: Boolean indicating if note_db_obj is a list.
    Returns:
        A dictionary or list of dictionaries representing the note(s).
    """
    # Consider adding context={'include_relations': True} if schema handles enrichment
    note_schema = NoteSchema(many=many)
    data = note_schema.dump(note_db_obj)
    return data
