from flask_restx import Namespace, fields
from flask_restx.reqparse import RequestParser


class ModuleDto:
    """Data Transfer Objects and Request Parsers for the Module API."""

    # Define the namespace
    api = Namespace("modules", description="Course module related operations.")

    # --- Parser for Query Parameters (Filters and Pagination) ---
    module_filter_parser = RequestParser(bundle_errors=True)
    module_filter_parser.add_argument(
        "name",
        type=str,
        location="args",
        required=False,
        help="Filter modules by name (partial match).",
    )
    module_filter_parser.add_argument(
        "description",
        type=str,
        location="args",
        required=False,
        help="Filter modules by description (partial match).",
    )
    module_filter_parser.add_argument(
        "teacher_id",
        type=int,
        location="args",
        required=False,
        help="Filter modules by the ID of the teacher.",
    )
    module_filter_parser.add_argument(
        "page",
        type=int,
        location="args",
        required=False,
        default=1,
        help="Page number for pagination (default: 1).",
    )
    module_filter_parser.add_argument(
        "per_page",
        type=int,
        location="args",
        required=False,
        default=10,
        help="Number of items per page (default: 10).",
    )

    # Define the core 'module' object model
    module = api.model(
        "Module Object",
        {
            "id": fields.Integer(readonly=True, description="Module unique identifier"),
            "name": fields.String(required=True, description="Name of the module"),
            "description": fields.String(
                required=False, description="Description of the module"
            ),
            "teacher_id": fields.Integer(
                required=True,
                description="ID of the teacher responsible for this module",
            ),
        },
    )

    # Standard response for a single module
    data_resp = api.model(
        "Module Data Response",
        {
            "status": fields.Boolean(description="Indicates success or failure"),
            "message": fields.String(description="Response message"),
            "module": fields.Nested(module, description="The module data"),
        },
    )

    # Standard response for a list of modules (includes pagination)
    list_data_resp = api.model(
        "Module List Response",
        {
            "status": fields.Boolean(description="Indicates success or failure"),
            "message": fields.String(description="Response message"),
            "modules": fields.List(
                fields.Nested(module), description="List of module data"
            ),
            "total": fields.Integer(
                description="Total number of modules matching the query"
            ),
            "pages": fields.Integer(description="Total number of pages"),
            "current_page": fields.Integer(description="The current page number"),
            "per_page": fields.Integer(description="Number of items per page"),
            "has_next": fields.Boolean(description="True if there is a next page"),
            "has_prev": fields.Boolean(description="True if there is a previous page"),
        },
    )

    # --- DTOs for POST/PATCH ---
    module_create_input = api.model(
        "Module Create Input",
        {
            "name": fields.String(required=True, description="Name of the module"),
            "description": fields.String(
                required=False, description="Description of the module"
            ),
            "teacher_id": fields.Integer(
                required=True,
                description="ID of the teacher responsible for this module",
            ),
        },
    )

    module_update_input = api.model(
        "Module Update Input",
        {
            "name": fields.String(
                required=False, description="Updated name of the module"
            ),
            "description": fields.String(
                required=False, description="Updated description of the module"
            ),
        },
    )
