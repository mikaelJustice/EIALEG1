"""
Authentication helpers - session management, login/logout, access control decorators
"""

from functools import wraps
from flask import session, redirect, url_for, flash


def login_required(f):
    """Decorator: requires any logged-in user"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    """Decorator: requires admin role"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in.', 'warning')
            return redirect(url_for('auth.login'))
        if session.get('role') != 'admin':
            flash('Admin access required.', 'danger')
            return redirect(url_for('public.home'))
        return f(*args, **kwargs)
    return decorated


def captain_required(f):
    """Decorator: requires captain role"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in.', 'warning')
            return redirect(url_for('auth.login'))
        if session.get('role') != 'captain':
            flash('Captain access required.', 'danger')
            return redirect(url_for('public.home'))
        return f(*args, **kwargs)
    return decorated
