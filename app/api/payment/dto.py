from flask_restx import Namespace, fields

class PaymentDto:
    api = Namespace('payment', description='Payment related operations')
    
    checkout_session = api.model('CheckoutSession', {
        'fee_id': fields.Integer(required=True, description='ID of the fee to pay'),
    })
    
    checkout_response = api.model('CheckoutResponse', {
        'sessionId': fields.String(description='Stripe checkout session ID'),
    })
    
    error_response = api.model('ErrorResponse', {
        'message': fields.String(description='Error message'),
    }) 