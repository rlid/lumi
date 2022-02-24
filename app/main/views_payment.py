# app.py
#
# Use this sample code to handle webhook events in your integration.
#
# 1) Paste this code into a new file (app.py)
#
# 2) Install dependencies
#   pip3 install flask
#   pip3 install stripe
#
# 3) Run the server on http://localhost:4242
#   python3 -m flask run --port=4242
import stripe
from flask import jsonify, render_template, url_for
from flask import redirect, request
from flask_login import login_required, current_user

from app import db
from app.main import main
# This is your Stripe CLI webhook secret for testing your endpoint locally.
from app.models.payment import PaymentIntent

endpoint_secret = 'whsec_4ce91ea8b54f73539e987f5c30d57da15d250f59fcaf34ca7a1ed10b6b2181e9'

# This is your test secret API key.
stripe.api_key = 'sk_test_51D4bSfGoAMQGbjHHTVWyBn16wzOxG3bWCzgZSVXflGj7E1vkNeC2coBNf6MrqtRxkjKQhzI8OWTbjAk2HBdOZNDS00O8IJiiED'


@main.route('/checkout')
def payment_checkout():
    return render_template('payment_checkout.html')


@main.route('/create-checkout-session', methods=['POST'])
@login_required
def create_checkout_session():
    try:
        checkout_session = stripe.checkout.Session.create(
            line_items=[
                {
                    # Provide the exact Price ID (for example, pr_1234) of the product you want to sell
                    'price': 'price_1KWgD0GoAMQGbjHHUBRINR2I',
                    'quantity': 1,
                },
            ],
            mode='payment',
            customer_email=current_user.email,
            success_url=url_for('main.user', user_id=current_user.id, _external=True),
            cancel_url=url_for('main.payment_cancel', _external=True),
        )
        print(checkout_session.payment_intent)
        current_user.create_payment_intent(checkout_session.payment_intent)
    except Exception as e:
        return str(e)
    return redirect(checkout_session.url, code=303)


@main.route('/success')
def payment_success():
    return render_template('payment_success.html')


@main.route('/cancel')
def payment_cancel():
    return render_template('payment_cancel.html')


@main.route('/webhook', methods=['POST'])
def webhook():
    event = None
    payload = request.data
    sig_header = request.headers['STRIPE_SIGNATURE']
    print(payload)
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
    except ValueError as e:
        return 'Invalid payload', 400
    except stripe.error.SignatureVerificationError as e:
        return 'Invalid signature', 400

    # Handle the event
    print(f'Webhook received event of type {event.type}')
    if event['type'] == 'payment_intent.succeeded':
        stripe_payment_intent = event.data.object  # contains a stripe.PaymentIntent
        payment_intent = PaymentIntent.query.filter_by(stripe_id=stripe_payment_intent.id).first()
        if payment_intent is not None and payment_intent.succeeded == False:
            payment_intent.succeeded = True
            payment_intent.creator.total_balance_cent += stripe_payment_intent.amount
            db.session.add(payment_intent)
            db.session.commit()
            print('PaymentIntent was successful')
    else:
        print(f'Unhandled event type {event.type}')

    return jsonify(success=True)
