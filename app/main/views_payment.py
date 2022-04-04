import stripe
from flask import jsonify, url_for, flash
from flask import redirect, request, current_app
from flask_login import login_required, current_user

from app import db
from app.main import main
from app.models import Notification, Transaction
from app.models.payment import PaymentIntent


@main.route('/top-up/<price_id>')
@login_required
def top_up(price_id):
    try:
        checkout_session = stripe.checkout.Session.create(
            line_items=[
                {
                    # Provide the exact Price ID (for example, pr_1234) of the product you want to sell
                    'price': price_id,
                    'quantity': 1,
                },
            ],
            mode='payment',
            customer_email=current_user.email,
            success_url=url_for('main.top_up_success', _external=True) + '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=url_for('main.top_up_cancel', _external=True) + '?session_id={CHECKOUT_SESSION_ID}',
        )
        current_user.create_payment_intent(
            stripe_session_id=checkout_session.id,
            stripe_payment_intent_id=checkout_session.payment_intent)
        return redirect(checkout_session.url, code=303)
    except Exception as e:
        current_app.logger.exception(e)
        flash('Internal error - please contact support.', category='danger')
    return redirect(url_for('main.account'))


@main.route('/top-up/success')
@login_required
def top_up_success():
    stripe_session_id = request.args.get('session_id')
    if stripe_session_id is not None:
        payment_intent = PaymentIntent.query.filter_by(stripe_session_id=stripe_session_id).first()
        if payment_intent.succeeded:
            flash(f"Your top-up is successful. An email receipt has been sent to you.", "success")
            return redirect(url_for('main.account'))
        flash('You have authorised the payment but it is being processed. '
              'Please refresh this page in a few seconds to check your balance. '
              'You will also receive an email receipt once the payment has cleared.', category='info')
    return redirect(url_for('main.account'))


@main.route('/top-up/cancel')
@login_required
def top_up_cancel():
    flash('Top-up cancelled', category='warning')
    return redirect(url_for('main.account'))


@main.route('/top-up/webhook', methods=['POST'])
def webhook():
    payload = request.data
    sig_header = request.headers['STRIPE_SIGNATURE']
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, current_app.config['STRIPE_WEBHOOK_SECRET'])
    except ValueError as e:
        current_app.logger.exception(e)
        return 'Invalid payload', 400
    except stripe.error.SignatureVerificationError as e:
        current_app.logger.exception(e)
        return 'Invalid signature', 400

    # Handle the event
    if event['type'] == 'payment_intent.succeeded':
        stripe_payment_intent = event.data.object  # contains a stripe.PaymentIntent
        payment_intent = PaymentIntent.query.filter_by(stripe_payment_intent_id=stripe_payment_intent.id).first()
        if payment_intent is not None and not payment_intent.succeeded:
            payment_intent.succeeded = True
            db.session.add(payment_intent)
            Transaction.add(
                transaction_type=Transaction.TYPE_TOP_UP,
                amount_cent=stripe_payment_intent.amount,
                user=payment_intent.creator,
                payment_intent=payment_intent)

            Notification.push(
                target_user=payment_intent.creator,
                message=f'You topped up your account by ${0.01 * stripe_payment_intent.amount:.2f}.',
                email=True
            )
            db.session.commit()  # OK
            current_app.logger.info(f'Processed {event.type} - top-up successful')
    else:
        current_app.logger.info(f'Unhandled event type {event.type}')

    return jsonify(success=True)
