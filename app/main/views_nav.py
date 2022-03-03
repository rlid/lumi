from flask import render_template, redirect, flash, Markup, url_for, session, request
from flask_login import login_required, current_user

from app.main import main


@main.before_request
def before_request():
    if current_user.is_authenticated:
        current_user.ping()
        if not current_user.email_verified \
                and request.blueprint != 'auth' \
                and request.endpoint != 'static' \
                and request.endpoint != 'main.index' \
                and request.endpoint != 'main.browse':
            flash('Your access is restricted because your email address is not verified. ' +
                  Markup(f'<a href={url_for("auth.resend_confirmation")}>Click here</a> ') +
                  'to request another confirmation email.', category='warning')
            return redirect(url_for('main.browse'))

    # if session.get('allow_cookie') is None:
    #     flash(Markup(
    #         '<div class="toast-header bg-light"><strong class="me-auto">Cookie Notice</strong><button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Close"></button></div>') + \
    #           Markup(
    #               '<div class="toast-body pt-2"><p class="mb-1">This site only uses essential cookies by default. ' +
    #               'We’d also like to use analytics cookies so we can measure and improve the performance of our site. Do you want to allow analytics cookies?</p><div style="font-size:1.1rem">' +
    #               f'<a class="badge btn-primary text-decoration-none" href={url_for("main.allow_cookie", choice=1)}>' +
    #               'Accept</a> ' +
    #               f'<a class="badge btn-primary text-decoration-none" href={url_for("main.allow_cookie", choice=0)}>' +
    #               'Reject</a> ' +
    #               f'<a class="badge btn-primary text-decoration-none" href={url_for("main.cookie")}>' +
    #               'Learn More</a></div></div>')
    #           , category='privacy')


@main.route('/')
def index():
    return render_template('landing.html')


@main.route('/allow_cookie/<int:choice>')
def allow_cookie(choice):
    session['allow_cookie'] = choice == 1
    return redirect(url_for('main.index'))


@main.route('/reset_cookie')
def reset_cookie():
    session.pop('allow_cookie', None)
    return redirect(url_for('main.index'))


@main.route('/whatsapp')
def whatsapp():
    return redirect('https://api.whatsapp.com/send?phone=+447774523701', code=302)


@main.route('/how-it-works')
def how_it_works():
    return render_template('landing.html', title='How It Works')


@main.route('/privacy')
def privacy():
    return render_template('privacy.html', title='Privacy Policy')


@main.route('/cookie')
def cookie():
    return render_template('cookie.html', title='Cookie Policy')


@main.route('/alerts')
@login_required
def alerts():
    return render_template('landing.html', title='Alerts')


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
    return render_template('about.html')
