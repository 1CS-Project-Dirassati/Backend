from flask import request
from flask_restx import Resource
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.extensions import limiter
from app.api.decorators import roles_required
from .service import PaymentService
from .dto import PaymentDto

# Get the API namespace and DTOs
api = PaymentDto.api
checkout_session = PaymentDto.checkout_session
checkout_response = PaymentDto.checkout_response
error_response = PaymentDto.error_response

@api.route('/create-checkout-session')
class CreateCheckoutSession(Resource):
    @api.doc(
        'Create a Stripe checkout session',
        security='Bearer',
        responses={
            200: ('Success', checkout_response),
            400: ('Validation Error', error_response),
            401: 'Unauthorized',
            404: ('Fee not found', error_response),
            500: ('Internal Server Error', error_response)
        }
    )
    @api.expect(checkout_session, validate=True)
    @jwt_required()
    @roles_required('parent')
    @limiter.limit('10/minute')
    def post(self):
        """Create a Stripe checkout session for a fee payment"""
        data = request.get_json()
        fee_id = data.get('fee_id')
        current_user_id = get_jwt_identity()
        
        return PaymentService.create_checkout_session(fee_id, current_user_id) 