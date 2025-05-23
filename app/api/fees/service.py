from flask import current_app
from sqlalchemy.exc import SQLAlchemyError
from marshmallow import ValidationError
from datetime import datetime, timezone

from app import db
from app.models import Fee, FeeStatus, Parent
from app.utils import err_resp, message, internal_err_resp, validation_error
from .utils import dump_data, load_data

class FeeService:
    @staticmethod
    def get_fee_data(fee_id: int, current_user_id: int, current_user_role: str):
        """Get fee data by ID, with record-level authorization check"""
        fee = Fee.query.get(fee_id)
        if not fee:
            current_app.logger.info(f"Fee with ID {fee_id} not found.")
            return err_resp("Fee not found!", "fee_404", 404)

        # Record-level authorization check
        if current_user_role == "parent" and fee.parent_id != int(current_user_id):
            current_app.logger.warning(
                f"Forbidden: Parent {current_user_id} attempted to access fee {fee_id} belonging to parent {fee.parent_id}."
            )
            return err_resp(
                "Forbidden: You do not have permission to access this fee.",
                "record_access_denied",
                403,
            )

        try:
            fee_data = dump_data(fee)
            # Add parent information
            parent = Parent.query.get(fee.parent_id)
            if parent:
                fee_data['parent_name'] = f"{parent.first_name} {parent.last_name}"
            
            resp = message(True, "Fee data sent successfully")
            resp["fee"] = fee_data
            current_app.logger.debug(f"Successfully retrieved fee ID {fee_id}")
            return resp, 200
        except Exception as error:
            current_app.logger.error(
                f"Error serializing fee data for ID {fee_id}: {error}",
                exc_info=True,
            )
            return internal_err_resp()

    @staticmethod
    def get_all_fees(
        parent_id=None,
        status=None,
        page=None,
        per_page=None,
        current_user_id=None,
        current_user_role=None,
    ):
        """Get a paginated list of fees, filtered by parent and status"""
        page = page or 1
        per_page = per_page or 10

        try:
            query = Fee.query

            # Role-based data scoping
            if current_user_role == "parent":
                current_app.logger.debug(f"Scoping fees list for parent ID: {current_user_id}")
                query = query.filter(Fee.parent_id == int(current_user_id))
            elif current_user_role != "admin":
                return err_resp(
                    "Forbidden: Only admins and parents can view fees.",
                    "list_role_forbidden",
                    403,
                )

            # Apply filters
            if parent_id is not None and current_user_role == "admin":
                query = query.filter(Fee.parent_id == parent_id)
            if status is not None:
                query = query.filter(Fee.status == status)

            # Add ordering
            query = query.order_by(Fee.due_date.desc())

            # Implement pagination
            current_app.logger.debug(f"Paginating fees: page={page}, per_page={per_page}")
            paginated_fees = query.paginate(page=page, per_page=per_page, error_out=False)
            current_app.logger.debug(f"Paginated fees items count: {len(paginated_fees.items)}")

            # Get all parent IDs for the fees
            parent_ids = {fee.parent_id for fee in paginated_fees.items}
            parents = {p.id: p for p in Parent.query.filter(Parent.id.in_(parent_ids)).all()}

            # Serialize results
            fees_data = []
            for fee in paginated_fees.items:
                fee_dict = dump_data(fee)
                parent = parents.get(fee.parent_id)
                if parent:
                    fee_dict['parent_name'] = f"{parent.first_name} {parent.last_name}"
                fees_data.append(fee_dict)

            current_app.logger.debug(f"Serialized {len(fees_data)} fees")
            resp = message(True, "Fees list retrieved successfully")
            resp["fees"] = fees_data
            resp["total"] = paginated_fees.total
            resp["pages"] = paginated_fees.pages
            resp["current_page"] = paginated_fees.page
            resp["per_page"] = paginated_fees.per_page
            resp["has_next"] = paginated_fees.has_next
            resp["has_prev"] = paginated_fees.has_prev

            current_app.logger.debug(f"Successfully retrieved fees page {page}. Total: {paginated_fees.total}")
            return resp, 200

        except Exception as error:
            log_msg = f"Error getting fees list (role: {current_user_role})"
            if parent_id:
                log_msg += f" for parent {parent_id}"
            if page:
                log_msg += f", page {page}"
            current_app.logger.error(f"{log_msg}: {error}", exc_info=True)
            return internal_err_resp()

    @staticmethod
    def update_fee_status(fee_id: int, data: dict, current_user_role: str):
        """Update a fee's status (Admin only)"""
        if current_user_role != "admin":
            return err_resp(
                "Forbidden: Only admins can update fee status.",
                "update_role_forbidden",
                403,
            )

        fee = Fee.query.get(fee_id)
        if not fee:
            current_app.logger.info(f"Attempted to update non-existent fee ID: {fee_id}")
            return err_resp("Fee not found!", "fee_404", 404)

        try:
            # Using temporary manual schema load
            from app.models.Schemas import FeeSchema
            fee_status_schema = FeeSchema(only=("status",), partial=True)
            validated_data = fee_status_schema.load(data)

            fee.status = validated_data.status
            if fee.status == FeeStatus.PAID:
                fee.payment_date = datetime.now(timezone.utc).date()

            db.session.commit()
            current_app.logger.info(f"Fee status updated successfully for ID: {fee_id}")

            fee_data = dump_data(fee)
            resp = message(True, f"Fee status updated to {fee.status.value}")
            resp["fee"] = fee_data
            return resp, 200

        except ValidationError as err:
            db.session.rollback()
            current_app.logger.warning(
                f"Validation error updating fee {fee_id}: {err.messages}. Data: {data}"
            )
            return validation_error(False, err.messages), 400
        except SQLAlchemyError as error:
            db.session.rollback()
            current_app.logger.error(
                f"Database error updating fee {fee_id}: {error}. Data: {data}",
                exc_info=True,
            )
            return internal_err_resp()
        except Exception as error:
            db.session.rollback()
            current_app.logger.error(
                f"Unexpected error updating fee {fee_id}: {error}. Data: {data}",
                exc_info=True,
            )
            return internal_err_resp() 