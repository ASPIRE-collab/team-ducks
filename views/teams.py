import json
import logging
import string
import os
import csv
from flask import Blueprint, flash, redirect, render_template, request, url_for,current_app,url_for, make_response,jsonify
from werkzeug.utils import secure_filename
from flask.scaffold import F
from flask_login import current_user, login_user, logout_user, login_required
from flask_login.utils import wraps

from db_models import User, Roles,UserRoles,PasswordResetTokens,Classifications,db
from panoptes_client import Panoptes, User


# Blueprint Configuration
teams_bp = Blueprint(
    'teams_bp',__name__,
    template_folder='templates',
    static_folder='static')

@teams_bp.route("/" , methods=['GET', 'POST']) 
def root():
    body=render_template('teams_body.html')
    return render_template('index.html' , is_authenticated=current_user.is_authenticated, body=body)

@teams_bp.route("/create_a_team" , methods=['GET', 'POST']) 
def create_a_team():
    if request.method == 'GET':
        body=render_template('create_a_team.html')
        return render_template('index.html' , is_authenticated=current_user.is_authenticated, body=body)
    # if request.method == 'POST':

@teams_bp.route("/user_lookup/<login>" , methods=['GET', 'POST']) 
def user_lookup(login):
    Panoptes.connect()
    users = User.where(login=login)

    for item in users:

        return_dict={'status':'found'}
        return_dict['id']=item.id
        return_dict['login']=item.login
        return_dict['credited_name']=item.credited_name
        return return_dict
        
    return {'status':'not found'}
