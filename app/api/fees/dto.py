from flask_restx import Namespace, fields
from flask_restx.reqparse import RequestParser

class FeeDto:
    """Data Transfer Objects and Request Parsers for the Fee API."""

    api = Namespace("fees", description="Fee related operations.")

    # --- Parser for Query Parameters (Filters and Pagination) ---
    fee_filter_parser = RequestParser(bundle_errors=True)
    fee_filter_parser.add_argument(
        "parent_id",
        type=int,
        location="args",
        required=False,
        help="Filter fees by parent ID (Admin only).",
    )
    fee_filter_parser.add_argument(
        "status",
        type=str,
        location="args",
        required=False,
        help="Filter fees by status (unpaid, paid, overdue, cancelled).",
    )
    fee_filter_parser.add_argument(
        "page",
        type=int,
        location="args",
        required=False,
        default=1,
        help="Page number for pagination (default: 1).",
    )
    fee_filter_parser.add_argument(
        "per_page",
        type=int,
        location="args",
        required=False,
        default=10,
        help="Number of items per page (default: 10).",
    )

    # Define the core 'fee' object model
    fee = api.model(
        "Fee Object",
        {
            "id": fields.Integer(readonly=True, description="Fee unique identifier"),
            "parent_id": fields.Integer(required=True, description="ID of the parent who owes the fee"),
            "parent_name": fields.String(description="Full name of the parent"),
            "amount": fields.Float(required=True, description="Amount of the fee"),
            "description": fields.String(description="Description of the fee"),
            "due_date": fields.Date(required=True, description="Due date for the fee"),
            "status": fields.String(required=True, description="Current status of the fee"),
            "payment_date": fields.Date(description="Date when the fee was paid (if applicable)"),
            "created_at": fields.DateTime(readonly=True, description="Timestamp of fee creation (UTC)"),
            "updated_at": fields.DateTime(readonly=True, description="Timestamp of last fee update (UTC)"),
        },
    )

    # DTO for updating fee status (Admin only)
    fee_status_update = api.model(
        "Fee Status Update",
        {
            "status": fields.String(
                required=True,
                description="New status for the fee (unpaid, paid, overdue, cancelled)",
                enum=["unpaid", "paid", "overdue", "cancelled"],
            )
        },
    )

    # Response models
    data_resp = api.model(
        "Fee Data Response",
        {
            "status": fields.Boolean(description="Success status"),
            "message": fields.String(description="Response message"),
            "fee": fields.Nested(fee, description="Fee data"),
        },
    )

    list_data_resp = api.model(
        "Fee List Response",
        {
            "status": fields.Boolean(description="Success status"),
            "message": fields.String(description="Response message"),
            "fees": fields.List(fields.Nested(fee), description="List of fees"),
            "total": fields.Integer(description="Total number of fees"),
            "pages": fields.Integer(description="Total number of pages"),
            "current_page": fields.Integer(description="Current page number"),
            "per_page": fields.Integer(description="Number of items per page"),
            "has_next": fields.Boolean(description="Whether there is a next page"),
            "has_prev": fields.Boolean(description="Whether there is a previous page"),
        },
    ) 