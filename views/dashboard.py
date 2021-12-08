import json
import logging
from flask import Blueprint, render_template, request, current_app, redirect
from flask.helpers import url_for
from flask_login.utils import login_required, current_user

from views.admin import is_admin

dashboard_bp = Blueprint('dashboard_bp',__name__)
logging.getLogger().setLevel(logging.INFO)

@dashboard_bp.route("/")
def dashboard():
    if current_user.is_authenticated:
        user_info = {
            "first_name":current_user.first_name,
            "last_name":current_user.last_name,
            "is_admin":is_admin(current_user)
        }
        return render_template('dashboard.html', user_info=user_info)
    else:
        return redirect(url_for('admin_bp.login'))

@dashboard_bp.route("/manage_users")
@login_required
def manage_users():
    if is_admin(current_user):
        return render_template('user_management.html')