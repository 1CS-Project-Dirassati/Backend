from flask import request, current_app
from flask_restx import Resource
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt

from app.extensions import limiter
from app.api.decorators import roles_required
from .service import FeeService
from .dto import FeeDto

# Get the API namespace and DTOs
api = FeeDto.api
data_resp = FeeDto.data_resp
list_data_resp = FeeDto.list_data_resp
fee_status_update = FeeDto.fee_status_update
fee_filter_parser = FeeDto.fee_filter_parser

@api.route("/")
class FeeList(Resource):
    @api.doc(
        "List fees",
        security="Bearer",
        parser=fee_filter_parser,
        description="Get a paginated list of fees. Filterable. Access restricted by role (Admins see all, Parents see own fees).",
        responses={
            200: ("Success", list_data_resp),
            401: "Unauthorized",
            403: "Forbidden",
            429: "Too Many Requests",
            500: "Internal Server Error"
        },
    )
    @jwt_required()
    @roles_required('admin', 'parent')
    @limiter.limit(lambda: current_app.config.get("RATE_LIMIT_FEE_LIST", "50/minute"))
    def get(self):
        """Get a list of fees, filtered by query params, user role, and paginated"""
        user_id = get_jwt_identity()
        role = get_jwt()['role']
        args = fee_filter_parser.parse_args()
        current_app.logger.debug(
            f"Received GET request for fees list with args: {args}"
        )

        return FeeService.get_all_fees(
            parent_id=args.get('parent_id'),
            status=args.get('status'),
            page=args.get('page'),
            per_page=args.get('per_page'),
            current_user_id=user_id,
            current_user_role=role
        )

@api.route("/<int:fee_id>")
@api.param('fee_id', 'The unique identifier of the fee')
class FeeResource(Resource):
    @api.doc(
        "Get a fee",
        security="Bearer",
        description="Get a specific fee by ID. Access restricted by role (Admins see all, Parents see own fees).",
        responses={
            200: ("Success", data_resp),
            401: "Unauthorized",
            403: "Forbidden",
            404: "Not Found",
            429: "Too Many Requests",
            500: "Internal Server Error"
        },
    )
    @jwt_required()
    @roles_required('admin', 'parent')
    @limiter.limit(lambda: current_app.config.get("RATE_LIMIT_FEE_GET", "100/minute"))
    def get(self, fee_id: int):
        """Get a specific fee by ID"""
        user_id = get_jwt_identity()
        role = get_jwt()['role']
        current_app.logger.debug(
            f"Received GET request for fee ID {fee_id}"
        )
        return FeeService.get_fee_data(fee_id, user_id, role)

@api.route("/<int:fee_id>/status")
@api.param('fee_id', 'The unique identifier of the fee')
class FeeStatus(Resource):
    @api.doc(
        "Update fee status",
        security="Bearer",
        description="Update the status of a fee (Admin only).",
        responses={
            200: ("Success", data_resp),
            400: "Validation Error",
            401: "Unauthorized",
            403: "Forbidden",
            404: "Not Found",
            429: "Too Many Requests",
            500: "Internal Server Error"
        },
    )
    @api.expect(fee_status_update, validate=True)
    @jwt_required()
    @roles_required('admin')
    @limiter.limit(lambda: current_app.config.get("RATE_LIMIT_FEE_UPDATE", "30/minute"))
    def patch(self, fee_id: int):
        """Update a fee's status (Admin only)"""
        data = request.get_json()
        role = get_jwt()['role']
        current_app.logger.debug(
            f"Received PATCH request for fee ID {fee_id} status with data: {data}"
        )
        return FeeService.update_fee_status(fee_id, data, role) 