from app.models.Schemas import FeeSchema

def dump_data(data, many=False):
    """Serialize data using the appropriate schema"""
    schema = FeeSchema(many=many)
    return schema.dump(data)

def load_data(data, partial=False, instance=None):
    """Deserialize data using the appropriate schema"""
    schema = FeeSchema(partial=partial)
    return schema.load(data, instance=instance) 