"""
Authentication Routes - handles login and logout for admin and captains
"""

from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import check_password_hash
from database import get_db

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Login page for both admins and captains"""
    if 'user_id' in session:
        # Already logged in - redirect to appropriate dashboard
        if session['role'] == 'admin':
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('captain.dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        db = get_db()
        user = db.execute(
            'SELECT * FROM users WHERE username = ?', (username,)
        ).fetchone()

        if user and check_password_hash(user['password_hash'], password):
            # Store user info in session
            session.clear()
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            session['team_id'] = user['team_id']

            flash(f'Welcome back, {username}!', 'success')

            if user['role'] == 'admin':
                return redirect(url_for('admin.dashboard'))
            else:
                return redirect(url_for('captain.dashboard'))
        else:
            flash('Invalid username or password.', 'danger')

    return render_template('auth/login.html')


@auth_bp.route('/logout')
def logout():
    """Clear session and redirect to home"""
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('public.home'))
