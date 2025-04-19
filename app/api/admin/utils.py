def load_data(admin_db_obj):
    """
    load admin data from db object

    Parameters:
    - Admin db object
    """
    from app.models.Schemas import AdminSchema

    admin_schema = AdminSchema()
    data = admin_schema.dump(admin_db_obj)

    return data
