from flask import request, current_app
from flask_restx import Resource
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt

# Import shared extensions/decorators
from app.extensions import limiter
from app.api.decorators import roles_required

# Import salle-specific modules
from .service import SalleService
from .dto import SalleDto

# Get the API namespace and DTOs
api = SalleDto.api
data_resp = SalleDto.data_resp
list_data_resp = SalleDto.list_data_resp
salle_create_input = SalleDto.salle_create_input
salle_update_input = SalleDto.salle_update_input
salle_filter_parser = SalleDto.salle_filter_parser


# --- Helper to get current user info ---
def get_current_user_info():
    user_id = get_jwt_identity()
    claims = get_jwt()
    role = claims.get("role")
    current_app.logger.debug(
        f"Current user info: ID={user_id}, Role={role}"
    )  # Log user info
    return user_id, role


# --- Route for listing/creating salles ---
@api.route("/")
class SalleList(Resource):

    @api.doc(
        "List salles",
        security="Bearer",
        parser=salle_filter_parser,
        description="Get a list of classrooms (salles). Filterable by name and capacity.",
        responses={
            200: ("Success", list_data_resp),
            401: "Unauthorized",
            403: "Forbidden",
            429: "Too Many Requests",
            500: "Internal Server Error",
        },
    )
    @jwt_required()
    @roles_required("admin", "teacher")  # Example roles allowed
    @limiter.limit("60/minute")
    def get(self):
        """Get a list of salles, filtered by query params"""
        user_id, role = get_current_user_info()
        args = salle_filter_parser.parse_args()
        current_app.logger.debug(
            f"Received GET request for salles list with args: {args}"
        )
        return SalleService.get_all_salles(
            name=args.get("name"),
            min_capacity=args.get("min_capacity"),
            max_capacity=args.get("max_capacity"),
            current_user_id=user_id,
            current_user_role=role,
        )

    @api.doc(
        "Create a new salle",
        security="Bearer",
        description="Create a new salle (classroom). Admin only.",
        responses={
            201: ("Created", data_resp),
            400: "Validation Error/Invalid Data",
            401: "Unauthorized",
            403: "Forbidden",
            429: "Too Many Requests",
            500: "Internal Server Error",
        },
    )
    @api.expect(salle_create_input, validate=True)
    @jwt_required()
    @roles_required("admin")  # Only admins can create
    @limiter.limit("30/minute")
    def post(self):
        """Create a new salle"""
        user_id, role = get_current_user_info()
        data = request.get_json()
        current_app.logger.debug(
            f"Received POST request to create salle with data: {data}"
        )
        return SalleService.create_salle(data, user_id, role)


# --- Route for specific salle operations ---
@api.route("/<int:salle_id>")
@api.param("salle_id", "The unique identifier of the salle")
class SalleResource(Resource):

    @api.doc(
        "Get a specific salle by ID",
        security="Bearer",
        description="Get data for a specific salle.",
        responses={
            200: ("Success", data_resp),
            401: "Unauthorized",
            403: "Forbidden",
            404: "Not Found",
            429: "Too Many Requests",
            500: "Internal Server Error",
        },
    )
    @jwt_required()
    @roles_required("admin", "teacher")  # Example roles allowed
    @limiter.limit("100/minute")
    def get(self, salle_id):
        """Get a specific salle's data by ID"""
        user_id, role = get_current_user_info()
        current_app.logger.debug(f"Received GET request for salle ID: {salle_id}")
        return SalleService.get_salle_data(salle_id, user_id, role)

    @api.doc(
        "Update a salle",
        security="Bearer",
        description="Update details of a salle (Admin only).",
        responses={
            200: ("Success", data_resp),
            400: "Validation Error/Invalid Data",
            401: "Unauthorized",
            403: "Forbidden",
            404: "Not Found",
            429: "Too Many Requests",
            500: "Internal Server Error",
        },
    )
    @api.expect(salle_update_input, validate=True)
    @jwt_required()
    @roles_required("admin")  # Only admins can update
    @limiter.limit("40/minute")
    def patch(self, salle_id):
        """Update details of a salle"""
        user_id, role = get_current_user_info()
        data = request.get_json()
        current_app.logger.debug(
            f"Received PATCH request for salle ID {salle_id} with data: {data}"
        )
        return SalleService.update_salle(salle_id, data, user_id, role)

    @api.doc(
        "Delete a salle",
        security="Bearer",
        description="Delete a salle (Admin only).",
        responses={
            204: "No Content - Success",
            401: "Unauthorized",
            403: "Forbidden",
            404: "Not Found",
            429: "Too Many Requests",
            500: "Internal Server Error",
        },
    )
    @jwt_required()
    @roles_required("admin")  # Only admins can delete
    @limiter.limit("20/minute")
    def delete(self, salle_id):
        """Delete a salle"""
        user_id, role = get_current_user_info()
        current_app.logger.debug(f"Received DELETE request for salle ID: {salle_id}")
        return SalleService.delete_salle(salle_id, user_id, role)
