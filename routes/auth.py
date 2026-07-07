from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from models import User
from extensions import db
from email_utils import send_password_reset_email
import secrets, string

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    error = None
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        user = User.query.filter_by(username=username, status='active').first()

        if user and user.check_password(password):
            login_user(user, remember=True)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('main.dashboard'))
        else:
            error = 'Invalid username or password.'

    return render_template('auth/login.html', error=error)


@auth_bp.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    message = None
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        user = User.query.filter_by(username=username, status='active').first()

        if not user:
            message = 'No active user found with that username.'
        elif not user.email:
            message = 'This account has no email address on file.'
        else:
            temp_password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(10))
            user.set_password(temp_password)
            db.session.commit()
            ok, err = send_password_reset_email(
                to_email=user.email,
                to_name=user.name,
                username=user.username,
                password=temp_password
            )
            if ok:
                flash('Password reset instructions have been sent to your email.', 'success')
                return redirect(url_for('auth.login'))
            message = f'Unable to send reset email: {err}'

    return render_template('auth/reset_password.html', error=message)


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))
