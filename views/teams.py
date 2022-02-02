from flask import Blueprint, render_template, request
from flask_login import current_user, login_required
from app import app_config 
from sqlalchemy import func
from db_models import User,Classifications,CountsAll, ZooniverseUsers,Teams,TeamMembers,Invitations,db
from panoptes_client import Panoptes, User
from views.admin import render_index,add_zooniverse_user,get_current_user_ids
from uuid import uuid4


import requests
import json
from requests.structures import CaseInsensitiveDict

# Blueprint Configuration
teams_bp = Blueprint(
    'teams_bp',__name__,
    template_folder='templates',
    static_folder='static')

@teams_bp.route("/" , methods=['GET', 'POST']) 
def root():
    teams_list=[]
    all_teams=db.session.query(Teams).all()
    for team in all_teams:
        teams_list.append({'name':team.name,'id':team.id})
    body=render_template('teams_body.html',teams=teams_list)
    return render_index(body)
    #return render_template('index.html' , is_authenticated=current_user.is_authenticated, body=body)


@teams_bp.route("/invite/<token>" , methods=['GET', 'POST']) 
def invite(token):
    if request.method == 'GET':
        invite=db.session.query(Invitations,ZooniverseUsers,Teams).filter(Teams.id==Invitations.team_id).filter(Invitations.zooniverse_user_id==ZooniverseUsers.id).filter(Invitations.token==token).first()
        if invite:
            print(invite)
            #If this is a clean invite...
            if invite[0].accepted==False and invite[0].rejected==False:
                body=render_template('invite.html',name=invite[2].name,display_name=invite[1].display_name,token=token)
                return render_index(body)
            if invite[0].accepted==True:
                body=render_template('invite_status.html',this_invite="has been ACCEPTED. ")
                return render_index(body)
            if invite[0].rejected==True:
                body=render_template('invite_status.html',this_invite="has been REJECTED. ")
                return render_index(body)
        else:
            body=render_template('invite_status.html',this_invite="was not found in our system.")
            return render_index(body)


    if request.method == 'POST':
        response = request.get_json()
        invite=db.session.query(Invitations).filter(Invitations.token==token).first()
        if invite:
            if response['choice']=='join': #Add user to team, and accept the invite.
                try:
                    new_member=TeamMembers(zooniverse_user_id=invite.zooniverse_user_id,team_id=invite.team_id)
                    db.session.add(new_member)
                    db.session.query(Invitations).filter(Invitations.token==token).update({'accepted':True})
                    db.session.commit()
                    return {'status':'success','message':'Thanks for joining!'}
                except Exception as err:
                    db.session.rollback()
                    db.session.flush()
                    return {'status':'error','message':str(err)}
            else: #decline the invite.
                try:
                    db.session.query(Invitations).filter(Invitations.token==token).update({'rejected':True})
                    db.session.commit()
                    return {'status':'success','message':'Invitation rejected.'}
                except Exception as err:
                    db.session.rollback()
                    db.session.flush()
                    return {'status':'error','message':str(err)}
        else:
            return {'status':'error','message':'Invitation not found.'} 
 

# @teams_bp.route("/remove_team_member/<team_id>" , methods=['POST']) 
# @login_required
# def remove_team_member(team_id):
#     team=db.session.query(Teams).filter(Teams.id==int(team_id)).first()
#     if team:
#         if team.owner_id!=current_user.id:
#             return {'status':'error','message':'You do not own this team.'}
    

@teams_bp.route("/invite_user/<team_id>" , methods=['POST']) 
@login_required
def invite_user(team_id):
    team=db.session.query(Teams).filter(Teams.id==int(team_id)).first()
    
    if team:
        if team.owner_id!=current_user.id:
            return {'status':'error','message':'You do not own this team.'}
    team_name=team.name
    user_json = request.get_json()
    current_users=get_current_user_ids()
    if int(user_json['id']) not in current_users:
        current_users=add_zooniverse_user(user_json['id'],current_users)
    existing_users=db.session.query(TeamMembers).filter(TeamMembers.team_id==int(team_id)).filter(TeamMembers.zooniverse_user_id==int(user_json['id'])).first()
    if existing_users:
        return {'status':'error','message':'User is already in team.'}
    existing_invite=db.session.query(Invitations).filter(Invitations.zooniverse_user_id==user_json['id']).filter(Invitations.team_id==team_id).first()
    p=Panoptes.connect(username=app_config['ZOONIVERSE_USER'], password=app_config['ZOONIVERSE_PASS'])
    encoded_jwt=p.get_bearer_token()
    headers = CaseInsensitiveDict()
    headers["Accept"] = "application/vnd.api+json; version=1"
    headers["Content-Type"]="application/json"
    headers["Authorization"] = "Bearer "+encoded_jwt
    headers["authority"] = "talk.zooniverse.org"
    headers['origin'] = 'https://www.zooniverse.org'
    headers['sec-fetch-site'] = 'same-site'
    headers['sec-fetch-mode'] = 'cors'
    headers['sec-fetch-dest'] = 'empty'
    headers['referer'] = 'https://www.zooniverse.org/'
    if existing_invite==None:

        try:
            token=str(uuid4())
            new_invite=Invitations(team_id=team_id,zooniverse_user_id=user_json['id'],accepted=False,rejected=False,token=token)
            db.session.add(new_invite)
            db.session.commit()
            json_data={"http_cache":True,"conversations":{"user_id":2417880,"title":"Drones For Ducks Team Invite","body":"You have been invited to join a Drones for Ducks team!\nIf you wish to be a part of the '"+team_name+"' team,\nClick the URL below:\n[View "+team_name+" Invitation]("+request.host_url+"teams/invite/"+token+")","recipient_ids":[int(user_json['id'])]}}
            print(json_data)
            r=requests.post('https://talk.zooniverse.org/conversations',headers=headers,data=json.dumps(json_data))
            if r.status_code!=200:
                return {'status':'error','message':'failed to send invite.'}
            else:
                return {'status':'success','message':'Invitation sent.'}
        except Exception as err:
            db.session.rollback()
            db.session.flush()
            return {'status':'error','message':str(err)}
    else:
        try:
            token=existing_invite.token
            updated_user_row = db.session.query(Invitations).filter(Invitations.zooniverse_user_id==user_json['id']).filter(Invitations.team_id==team_id).update({'accepted':0,'rejected':0})
            db.session.commit()
            json_data={"http_cache":True,"conversations":{"user_id":2417880,"title":"Drones For Ducks Team Invite","body":"You have been invited to join a Drones for Ducks team!\nIf you wish to be a part of the '"+team_name+"' team,\nClick the URL below:\n[View "+team_name+" Invitation]("+request.host_url+"teams/invite/"+token+")","recipient_ids":[int(user_json['id'])]}}
            r=requests.post('https://talk.zooniverse.org/conversations',headers=headers,data=json.dumps(json_data))
            print(r.text)
            if r.status_code!=200:
                return {'status':'error','message':'failed to send invite.'}
            else:
                return {'status':'success','message':'Invitation sent.'}
        except Exception as err:
            db.session.rollback()
            db.session.flush()
            return {'status':'error','message':str(err)}



@teams_bp.route("/create_a_team" , methods=['GET', 'POST']) 
@login_required
def create_a_team():
    if request.method == 'GET':
        body=render_template('create_a_team.html')
        return render_index(body)
        #return render_template('index.html' , is_authenticated=current_user.is_authenticated, body=body)
    if request.method == 'POST':
        print(request.base_url)
        print(request.host)
        print(request.host_url)
        user_json = request.get_json()
        try:
            existing_team=db.session.query(Teams).filter(Teams.name==user_json['name']).first()
            if existing_team:
                return {'status':'error','message':'Team '+user_json['name']+' already exists.'}
            else:
                new_team=Teams(name=user_json['name'],owner_id=current_user.get_id())
                
                db.session.add(new_team)
                db.session.commit()
                # db.session.flush(new_team)
                db.session.refresh(new_team)
                print(new_team)
                if new_team.id:
                    print(user_json['members'])
                    for team_member in user_json['members']:
                        try:
                            token=str(uuid4())
                            new_invite=Invitations(team_id=new_team.id,zooniverse_user_id=team_member['id'],accepted=False,rejected=False,token=token)
                            db.session.add(new_invite)
                            db.session.commit()
                            p=Panoptes.connect(username=app_config['ZOONIVERSE_USER'], password=app_config['ZOONIVERSE_PASS'])
                            encoded_jwt=p.get_bearer_token()
                            headers = CaseInsensitiveDict()
                            headers["Accept"] = "application/vnd.api+json; version=1"
                            headers["Content-Type"]="application/json"
                            headers["Authorization"] = "Bearer "+encoded_jwt
                            headers["authority"] = "talk.zooniverse.org"
                            headers['origin'] = 'https://www.zooniverse.org'
                            headers['sec-fetch-site'] = 'same-site'
                            headers['sec-fetch-mode'] = 'cors'
                            headers['sec-fetch-dest'] = 'empty'
                            headers['referer'] = 'https://www.zooniverse.org/'
                            json_data={"http_cache":True,"conversations":{"user_id":2417880,"title":"Drones For Ducks Team Invite","body":"You have been invited to join a Drones for Ducks team!\nIf you wish to be a part of the '"+user_json['name']+"' team,\nClick the URL below:\n[View "+user_json['name']+" Invitation]("+request.host_url+"teams/invite/"+token+")","recipient_ids":[int(team_member['id'])]}}
                            print(json_data)
                            r=requests.post('https://talk.zooniverse.org/conversations',headers=headers,data=json.dumps(json_data))
                            if r.status_code!=200:
                                return {'status':'error','message':'failed to send invite.'}

                        except Exception as err:
                            db.session.rollback()
                            db.session.flush()
                            return {'status':'error','message':str(err)}
                    return {'status':'success','message':'Team '+user_json['name']+' created.','team_id':new_team.id}
        except Exception as err:
            return {'status':'error','message':str(err)}
        return {'status':'success','message':'Team '+user_json['name']+' created.'}



@teams_bp.route("/remove_team_member/<team_id>" , methods=['POST']) 
@login_required
def remove_team_member(team_id):
    team=db.session.query(Teams).filter(Teams.id==team_id).first()
    if team:
        if team.owner_id==current_user.id:
            user_json = request.get_json()
            remove_user_id=user_json['id']
            try:
                db.session.query(TeamMembers).filter(TeamMembers.zooniverse_user_id==remove_user_id).filter(TeamMembers.team_id==team_id).delete()
                db.session.commit()
                return {'status':'success','message':'User Successfully Removed from Team.'}

            except Exception as e:
                return {'status':'error','message':str(e)}


        else:
            return {'status':'error','message':'Team does not exist.'}
    else:
        return {'status':'error','message':'Team does not exist.'}

@teams_bp.route("/team_data/<team_id>" , methods=['GET']) 
@login_required
def team_data(team_id):

    return_obj={'team_members':[],'accepted_invites':[],'rejected_invites':[],'pending_invites':[]}
    
    team=db.session.query(Teams).filter(Teams.id==team_id).first()
    if team:
        if team.owner_id==current_user.id:

            team_members=db.session.query(ZooniverseUsers).filter(TeamMembers.team_id==team.id).filter(ZooniverseUsers.id==TeamMembers.zooniverse_user_id).all()
            for tm in team_members:
                return_obj['team_members'].append({'id':tm.id,'display_name':tm.display_name,'avatar_src':tm.avatar_src})
                
            invites=db.session.query(Invitations,ZooniverseUsers).filter(Invitations.zooniverse_user_id==ZooniverseUsers.id).filter(Invitations.team_id==team.id).all()
            for invite in invites:
                if invite[0].accepted==True and invite[0].rejected==False:
                    
                    return_obj['accepted_invites'].append({'id':invite[1].id,'display_name':invite[1].display_name,'avatar_src':invite[1].avatar_src})
                if invite[0].accepted==False and invite[0].rejected==True:
                    
                    return_obj['rejected_invites'].append({'id':invite[1].id,'display_name':invite[1].display_name,'avatar_src':invite[1].avatar_src})
                if invite[0].accepted==False and invite[0].rejected==False:
                    
                    return_obj['pending_invites'].append({'id':invite[1].id,'display_name':invite[1].display_name,'avatar_src':invite[1].avatar_src})
            return return_obj
        else:
            return {'status':'error','message':'You do not own this team.'}
    else:
        return {'status':'error','message':'Team not found.'}



@teams_bp.route("/manage_team/<team_id>" , methods=['GET', 'POST']) 
@login_required
def manage_team(team_id):
    if request.method == 'GET':
        team=db.session.query(Teams).filter(Teams.id==team_id).first()
        if team:
            if team.owner_id==current_user.id:
                body=render_template('manage_team.html',team_id=team.id,team_name=team.name)
                return render_index(body)
            else:
                body=render_template('general_error.html',error_string='You cannot manage teams created by others.')
                return render_index(body)
        else:
            body=render_template('general_error.html',error_string='Team not found.')
            return render_index(body)
 


@teams_bp.route("/user_lookup/" , methods=['POST']) 
def user_lookup():
    Panoptes.connect()
    user_json = request.get_json()
    print(user_json)
    users = User.where(login=user_json['username'])
    print(users)
    for item in users:
        print(item)
        return_dict={'status':'found'}
        return_dict['id']=item.id
        return_dict['login']=item.login
        return_dict['credited_name']=item.credited_name
        return return_dict
    return {'status':'not found'}


def update_single_user_rankings(user_id):
    count=db.session.query(func.count(Classifications.id)).filter(Classifications.zooniverse_user_id==int(user_id)).filter(Classifications.workflow_id==17287).first()
    print(count)
    try:
        updated_user_row = db.session.query(CountsAll).filter(CountsAll.zooniverse_user_id==int(user_id)).update({'count':count[0]})
        db.session.commit()
    except Exception as e:
        print(e)
        db.session.rollback()
        db.session.flush()
        return e

def update_all_rankings():
    db.session.execute('''TRUNCATE TABLE counts_all''')
    db.session.commit()
    
    rs=db.session.execute('select zooniverse_user_id, count(*) as count from (select distinct zooniverse_user_id, zooniverse_users.display_name, zooniverse_users.avatar_src,subject_id  from classifications,zooniverse_users where zooniverse_users.id=classifications.zooniverse_user_id AND classifications.workflow_id =17287) as lol group by zooniverse_user_id order by count DESC;')
    all_contributors=[]
    for row in rs:
        new_count=CountsAll(zooniverse_user_id=row[0],count=row[1])
        all_contributors.append(new_count)

    db.session.bulk_save_objects(all_contributors)
    db.session.commit()

   
@teams_bp.route("/recent/<team>" , methods=['GET']) 
def recent(team):
    if team=="all":
       # select zooniverse_users.display_name,zooniverse_users.avatar_src, zooniverse_users.id, created_at from zooniverse_users,classifications where classifications.zooniverse_user_id=zooniverse_users.id order by created_at DESC limit 100;
        rs=db.session.query(ZooniverseUsers.display_name,ZooniverseUsers.avatar_src,ZooniverseUsers.id,Classifications.created_at).filter(Classifications.zooniverse_user_id==ZooniverseUsers.id).order_by(Classifications.created_at.desc()).limit(100)
        all_contributors=[]
        for row in rs:
            all_contributors.append({'name':row[0],'avatar':'/static/avatars/'+row[1],'user_id':row[2],'count':row[3]})
        body=render_template('recent.html',all_contributors=all_contributors)
        return render_index(body)
    else:
        return "Team ranking not yet implemented."

@teams_bp.route("/rankings/<team>" , methods=['GET']) 
def rankings(team):
    if team=="all":
        rs=db.session.query(ZooniverseUsers.display_name,ZooniverseUsers.avatar_src,ZooniverseUsers.id,CountsAll.count).filter(CountsAll.zooniverse_user_id==ZooniverseUsers.id).filter(ZooniverseUsers.id>0).order_by(CountsAll.count.desc())
        all_contributors=[]
        for row in rs:
            all_contributors.append({'name':row[0],'avatar':'/static/avatars/'+row[1],'user_id':row[2],'count':row[3]})
        body=render_template('rankings.html',all_contributors=all_contributors,team_name='ALL')
        return render_index(body)
    else:
        team_rs=db.session.query(Teams).filter(Teams.id==int(team)).first()
        if team_rs:
            rs=db.session.query(ZooniverseUsers.display_name,ZooniverseUsers.avatar_src,ZooniverseUsers.id,CountsAll.count).filter(TeamMembers.team_id==int(team)).filter(TeamMembers.zooniverse_user_id==CountsAll.zooniverse_user_id).filter(CountsAll.zooniverse_user_id==ZooniverseUsers.id).filter(ZooniverseUsers.id>0).order_by(CountsAll.count.desc())
            all_contributors=[]
            for row in rs:
                all_contributors.append({'name':row[0],'avatar':'/static/avatars/'+row[1],'user_id':row[2],'count':row[3]})
            body=render_template('rankings.html',all_contributors=all_contributors,team_name=team_rs.name)
            return render_index(body)
        else:
            body=render_template('rankings.html',all_contributors=[],team_name="Team not found.")
            return render_index(body)
@teams_bp.route("/my_teams/" , methods=['GET']) 
@login_required
def my_teams():
    my_teams_list=[]
    my_teams_tuple=db.session.query(Teams).filter(Teams.owner_id==current_user.get_id()).all()
    for my_team in my_teams_tuple:
        my_teams_list.append({'name':my_team.name,'id':my_team.id})

    body=render_template('my_teams.html',my_teams=my_teams_list)
    return render_index(body)
