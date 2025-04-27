from flask import current_app
import stripe
from datetime import datetime, timezone

from app.models import Fee, FeeStatus
from app import db
from app.utils import err_resp, message

# Initialize Stripe with your secret key
stripe.api_key = current_app.config['STRIPE_SECRET_KEY']

class StripeWebhookService:
    @staticmethod
    def handle_webhook(payload, sig_header):
        """Handle Stripe webhook events"""
        try:
            # Verify the webhook signature
            event = stripe.Webhook.construct_event(
                payload, sig_header, current_app.config['STRIPE_WEBHOOK_SECRET']
            )
        except ValueError as e:
            current_app.logger.error(f'Invalid payload: {str(e)}')
            return err_resp("Invalid payload", "invalid_payload", 400)
        except stripe.error.SignatureVerificationError as e:
            current_app.logger.error(f'Invalid signature: {str(e)}')
            return err_resp("Invalid signature", "invalid_signature", 400)
            
        # Handle the event
        if event.type == 'checkout.session.completed':
            session = event.data.object
            try:
                # Get the fee ID from the session metadata
                fee_id = int(session.metadata.get('fee_id'))
                fee = Fee.query.get(fee_id)
                
                if not fee:
                    current_app.logger.error(f'Fee not found: {fee_id}')
                    return err_resp("Fee not found", "fee_404", 404)
                    
                # Update the fee status
                fee.status = FeeStatus.PAID
                fee.payment_date = datetime.now(timezone.utc)
                db.session.commit()
                
                current_app.logger.info(f'Successfully processed payment for fee {fee_id}')
                return message(True, "Payment processed successfully"), 200
                
            except Exception as e:
                current_app.logger.error(f'Error processing payment: {str(e)}')
                db.session.rollback()
                return err_resp("Error processing payment", "payment_error", 500)
                
        return message(True, "Event received"), 200 