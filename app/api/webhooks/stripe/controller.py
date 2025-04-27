import datetime
from flask import request, current_app
from flask_restx import Namespace, Resource
import stripe
import json

from app.models import Fee, FeeStatus
from app import db

from .service import StripeWebhookService
from .dto import StripeWebhookDto

# Initialize Stripe with your secret key
stripe.api_key = current_app.config['STRIPE_SECRET_KEY']

# Get the API namespace and DTOs
api = StripeWebhookDto.api
webhook_response = StripeWebhookDto.webhook_response

@api.route('/')
class StripeWebhook(Resource):
    @api.doc(
        'Handle Stripe webhook events',
        responses={
            200: ('Success', webhook_response),
            400: ('Invalid payload/signature', webhook_response),
            404: ('Fee not found', webhook_response),
            500: ('Internal Server Error', webhook_response)
        }
    )
    def post(self):
        """Handle Stripe webhook events"""
        payload = request.get_data()
        sig_header = request.headers.get('Stripe-Signature')
        
        return StripeWebhookService.handle_webhook(payload, sig_header) 