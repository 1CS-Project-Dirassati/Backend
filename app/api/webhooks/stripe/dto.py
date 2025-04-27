from flask_restx import Namespace, fields

class StripeWebhookDto:
    api = Namespace('stripe-webhook', description='Stripe webhook operations')
    
    webhook_response = api.model('WebhookResponse', {
        'message': fields.String(description='Response message'),
    }) 