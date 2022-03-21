import json

from flask import render_template, redirect, flash, Markup, url_for, session, request, current_app
from flask_login import login_required, current_user

from app import db
from app.auth.forms import LogInForm
from app.main import main
from app.main.forms import FeedbackForm
from app.models import Feedback, Notification, Node


@main.before_request
def before_request():
    if current_user.is_authenticated:
        current_user.ping()
        if request.blueprint == 'auth':
            return
        if request.endpoint == 'static':
            return
        if not current_user.email_verified and (
                request.endpoint == 'main.post_options' or
                request.endpoint == 'main.new_post' or
                request.endpoint == 'main.request_engagement' or
                request.endpoint == 'main.accept_engagement' or
                request.endpoint == 'main.rate_engagement'
        ):
            flash('Your access is restricted because your email address is not verified. ' +
                  Markup(f'<a href={url_for("auth.resend_confirmation")}>Click here</a> ') +
                  'to request another confirmation email.', category='warning')
            redirect_url = request.referrer
            if redirect_url is None or not redirect_url.startswith(request.root_url):
                redirect(url_for('main.index'))
            return redirect(redirect_url)


@main.route('/')
def index():
    return render_template('landing.html', login_form=LogInForm(prefix='login'))


@main.route('/email')
def email():
    return render_template('email/notification.html', notification=Notification(message="Hello", node=Node(id='1')))


@main.route('/csp-report', methods=['POST'])
def csp_report():
    current_app.logger.warning(json.loads(request.data))
    return '', 200


@main.route('/allow_cookie/<int:choice>')
def allow_cookie(choice):
    session['allow_cookie'] = choice == 1
    redirect_url = request.referrer
    if redirect_url is None or not redirect_url.startswith(request.root_url):
        redirect(url_for('main.index'))
    return redirect(redirect_url)


@main.route('/reset_cookie')
def reset_cookie():
    session.pop('allow_cookie', None)
    return redirect(url_for('main.index'))


@main.route('/whatsapp')
def whatsapp():
    return redirect('https://api.whatsapp.com/send?phone=+447774523701', code=302)


@main.route('/faq')
@login_required
def faq():
    return render_template('docs/faq.html', title='FAQs')


@main.route('/faq/<anchor_id>')
@login_required
def faq_anchor(anchor_id):
    return render_template('docs/faq.html', title='FAQs', anchor_id=anchor_id)


@main.route('/privacy')
def privacy():
    return render_template('docs/privacy.html', title='Privacy Policy')


@main.route('/cookie')
def cookie():
    return render_template('docs/cookie.html', title='Cookie Policy')


@main.route('/terms')
@login_required
def terms():
    return render_template('docs/terms.html', title='Terms & Conditions')


@main.route('/feedback')
def feedback():
    form = FeedbackForm(prefix='feedback')
    return render_template('contact.html', title="Questions & Feedback", form=form)


@main.route('/contact', methods=['GET', 'POST'])
def contact():
    form = FeedbackForm(prefix='feedback')
    if form.validate_on_submit():
        fb = Feedback(
            type='feedback',
            text=form.text.data,
            email=form.email.data or (current_user.email if current_user.is_authenticated else None),
            request_invite=form.request_invite.data)
        db.session.add(fb)
        db.session.commit()  # OK
        send_email = current_app.config['EMAIL_SENDER']
        send_email(
            sender='feedback@lumiask.com',
            recipient='support@lumiask.com',
            subject='Feedback received',
            body_text=f'{fb.email}\n{fb.text}'
        )
        flash('Thank you so much for your feedback!', category='success')
        redirect_url = request.referrer
        if redirect_url and redirect_url.startswith(request.root_url):
            return redirect(redirect_url)
        else:
            return redirect('main.contact')

    return render_template('contact.html', title="Contact Us", form=form)


@main.route('/engagements')
@login_required
def engagements():
    return render_template('landing.html', title='Active Engagements')


@main.route('/saved')
@login_required
def saved():
    return render_template('landing.html', title='Saved')


@main.route('/guidelines')
def guidelines():
    return render_template('landing.html', title='Community Guidelines')


@main.route('/about')
def about():
    return render_template('docs/about.html')
