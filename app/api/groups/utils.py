from app.models.Schemas import GroupSchema  # Keep specific schema import


def dump_data(
    db_obj, many=False
):
    """
    Serialize database object(s) using the GroupSchema.

    Parameters:
        db_obj: A Group SQLAlchemy object or a list of them.
        many: Boolean indicating if db_obj is a list.
    Returns:
        A dictionary or list of dictionaries representing the group(s).
    """
    # Instantiate the schema, passing 'many=True' if handling a list
    group_schema = GroupSchema(many=many)
    # Serialize the database object(s) into dictionary format
    data = group_schema.dump(db_obj)
    return data


# --- Updated load_data function ---
def load_data(
    data: dict, many=False, partial=False, instance=None
):
    """
    Load (validate and deserialize) data using the GroupSchema, optionally into an existing instance.

    Parameters:
        data: A dictionary or list of dictionaries representing group data.
        many: Boolean indicating if data is a list.
        partial: Boolean indicating if partial loading (like for updates) is allowed.
        instance: An existing SQLAlchemy object (or list) to load data into.
                  Required for updates to work correctly with SQLAlchemy session tracking.
    Returns:
        A Group SQLAlchemy object or a list of them (either new or the updated instance).
    Raises:
        ValidationError: If the input data is invalid according to the schema.
    """
    # Instantiate the schema, passing 'many' and 'partial' flags
    group_schema = GroupSchema(many=many, partial=partial)

    # Deserialize the dictionary data into SQLAlchemy object(s)
    # Pass the instance if provided
    loaded_data = group_schema.load(
        data, instance=instance, partial=partial
    )  # Ensure partial is passed here too
    return loaded_data
