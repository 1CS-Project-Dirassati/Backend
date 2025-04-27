from flask import current_app
import stripe
from datetime import datetime, timezone

from app.models import Fee, Parent, FeeStatus
from app import db
from app.utils import err_resp, message

def init_stripe():
    """Initialize Stripe with the secret key from app config"""
    stripe.api_key = current_app.config['STRIPE_SECRET_KEY']

class PaymentService:
    @staticmethod
    def create_checkout_session(fee_id, parent_id):
        print("Creating checkout session chmisouuuuuuuuuuuuuuuuuuuuuuuu")
        """Create a Stripe checkout session for a fee payment"""
        # Initialize Stripe with current app context
        init_stripe()
        # Get the fee and verify it belongs to the current parent
        fee = Fee.query.filter(
            Fee.id == fee_id,
            Fee.parent_id == parent_id
        ).first()
        
        if not fee:
            return err_resp("Fee not found or unauthorized", "fee_404", 404)
            
        if fee.status == FeeStatus.PAID:
            return err_resp("Fee is already paid", "fee_already_paid", 400)
            
        try:
            # Create a Stripe checkout session
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': 'usd',
                        'product_data': {
                            'name': f'Fee Payment - {fee.description or "School Fee"}',
                        },
                        'unit_amount': int(fee.amount * 100),  # Convert to cents
                    },
                    'quantity': 1,
                }],
                mode='payment',
                success_url=current_app.config['STRIPE_SUCCESS_URL'],
                cancel_url=current_app.config['STRIPE_CANCEL_URL'],
                metadata={
                    'fee_id': str(fee.id),
                    'parent_id': str(fee.parent_id)
                }
            )
            
            resp = message(True, "Checkout session created successfully")
            resp["sessionId"] = checkout_session.id
            return resp, 200
            
        except Exception as e:
            current_app.logger.error(f'Error creating checkout session: {str(e)}')
            return err_resp("Error creating checkout session", "stripe_error", 500) 