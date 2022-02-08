from flask import Blueprint, render_template, request
from flask_login import current_user, login_required
from app import app_config 
from sqlalchemy import func
from db_models import Teams,db
from views.admin import render_index,add_zooniverse_user,get_current_user_ids
from uuid import uuid4


# Blueprint Configuration
challenges_bp = Blueprint(
    'challenges_bp',__name__,
    template_folder='templates',
    static_folder='static')



@challenges_bp.route("/" , methods=['GET','POST']) 
@login_required
def list_challenges():
    if request.method == 'GET':
        my_teams=db.session.query(Teams).filter(Teams.owner_id==current_user.id).first()
        if my_teams:
            body=render_template('create_a_challenge.html')
            return render_index(body)
        else:
            body=render_template('general_error.html',error_string='You cannot create a challenge unless you have a team.')
            return render_index(body)

@challenges_bp.route("/create_challenge/<challenge_type>" , methods=['GET','POST']) 
@login_required
def create_challenge(challenge_type):
    if request.method == 'GET':
        my_teams=db.session.query(Teams).filter(Teams.owner_id==current_user.id).all()
        if my_teams:
            teams=[]
            for team in my_teams:
                print(team.id)
                teams.append({'id':team.id,'name':team.name})
            body=render_template('create_challenge_type.html',challenge_type=challenge_type,teams=teams)
            return render_index(body)
        else:
            body=render_template('general_error.html',error_string='You cannot create a challenge unless you have a team.')
            return render_index(body)
    if request.method == 'POST':
        challenge_json = request.get_json()
        print(challenge_json)
        return {'status':'success'}
