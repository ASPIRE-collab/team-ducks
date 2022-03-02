from flask import Blueprint, render_template, request
from flask_login import current_user, login_required
from app import app_config 
from sqlalchemy import func, desc, asc, distinct
from db_models import Classifications, Teams,Challenges,ChallengeCounts,ZooniverseUsers,TeamMembers,TeamChallenges,db
from views.admin import render_index,add_zooniverse_user,get_current_user_ids
from uuid import uuid4
import datetime
import json



ordinal = lambda n: "%d%s" % (n,"tsnrhtdd"[(n//10%10!=1)*(n%10<4)*n%10::4])

# Blueprint Configuration
challenges_bp = Blueprint(
    'challenges_bp',__name__,
    template_folder='templates',
    static_folder='static')



@challenges_bp.route("/my_challenges/" , methods=['GET']) 
@login_required
def my_challenges():
    if request.method == 'GET':
        challenges_obj={'challenges':[]}
        my_challenges=db.session.query(Teams.name,Challenges.name,Challenges.id).filter(Teams.id==Challenges.team_id).filter(Teams.owner_id==current_user.id).all()
        print(db.session.query(Teams.name,Challenges.name,Challenges.id).filter(Teams.id==Challenges.team_id).filter(Teams.owner_id==current_user.id))
        for my_challenge in my_challenges:
            print(my_challenge)
            challenges_obj['challenges'].append({'team_name':my_challenge[0],'challenge_name':my_challenge[1],'challenge_id':my_challenge[2]})
#        select distinct(challenges.id),challenges.name,teams.name from challenges,team_challenges,teams where teams.owner_id =1 and 
    #  teams.id=team_challenges.team_id and challenges.type='team';
        team_challenges=db.session.query(distinct(Challenges.id),Challenges.name).filter(Teams.owner_id==current_user.id).filter(
            Teams.id==TeamChallenges.team_id
        ).filter(
            Challenges.type=='team'
        ).all()
        for my_challenge in team_challenges:
            
            challenges_obj['challenges'].append({'team_name':'','challenge_name':my_challenge[1],'challenge_id':my_challenge[0]})

        body=render_template('my_challenges.html',challenges=challenges_obj)
        return render_index(body)


@challenges_bp.route("/" , methods=['GET','POST']) 
@login_required
def root():
    if request.method == 'GET':
        my_teams=db.session.query(Teams).filter(Teams.owner_id==current_user.id).first()
        if my_teams:
            body=render_template('create_a_challenge.html')
            # normalize_challenge_counts(1)
            return render_index(body)

        else:
            body=render_template('general_error.html',error_string='You cannot create a challenge unless you have a team.<a style="color:#ba0c2f;" href="/teams/create_a_team">Click here to create one!</a>')
            return render_index(body)


@challenges_bp.route("/list/<type>" , methods=['GET']) 
def list_challenges(type):
    if type=='current':
        #select * from challenges where public=True and end_datetime>'2022-03-02 1:50:00';
        now = datetime.datetime.now() # current date and time
        now_timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
        current_public=db.session.query(Challenges).filter(Challenges.public==True).filter(Challenges.end_datetime>now_timestamp).all()
        current_public_list=[]
        for row in current_public:
            current_public_list.append({'id':row.id,'name':row.name,'end_string':"Ends On "+str(row.end_datetime)})
        body=render_template('list_challenges.html',challenges=current_public_list)
        return render_index(body)
    if type=='past':
        #select * from challenges where public=True and end_datetime>'2022-03-02 1:50:00';
        now = datetime.datetime.now() # current date and time
        now_timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
        current_public=db.session.query(Challenges).filter(Challenges.public==True).filter(Challenges.end_datetime<now_timestamp).all()
        current_public_list=[]
        for row in current_public:
            current_public_list.append({'id':row.id,'name':row.name,'end_string':"Ends On "+str(row.end_datetime)})
        body=render_template('list_challenges.html',challenges=current_public_list)
        return render_index(body)
          #current past

def update_challenge_counts(challenge_id,user_id,new_count):
    print('update_challenge_counts')
    existing=db.session.query(ChallengeCounts).filter(ChallengeCounts.challenge_id==challenge_id).filter(ChallengeCounts.user_id==user_id).first()
    print(existing)
    if existing:
        try:
            db.session.query(ChallengeCounts).filter(ChallengeCounts.id==existing.id).update({'count':new_count})
            db.session.commit()
        except Exception as err:
            db.session.rollback()
            db.session.flush()
            return err
    else:
        try:
            print(challenge_id,user_id,new_count)
            newcount=ChallengeCounts(challenge_id=challenge_id,user_id=user_id,count=new_count)
            db.session.add(newcount)
            db.session.commit()
            print("done")
        except Exception as err:
            print(err)
            db.session.rollback()
            db.session.flush()
            return err


def remove_user_challenge_counts(team_id,remove_user_id):
    #Next we get all current challenges for this team;
    now = datetime.datetime.now() # current date and time
    now_timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
    
    current_challenges=db.session.query(Challenges).filter(Challenges.team_id==team_id).filter(Challenges.start_datetime<=now_timestamp).filter(Challenges.end_datetime>=now_timestamp).all()
    for current_challenge in current_challenges: #for each challange delete from challange_counts
        print('current_challenge')
        print(current_challenge)
        try:
            db.session.query(ChallengeCounts).filter(ChallengeCounts.challenge_id==current_challenge.id).filter(ChallengeCounts.user_id==remove_user_id).delete()

            db.session.commit()
        except Exception as e:
            print('error')
            print(e)
            db.session.rollback()
            db.session.flush()


def normalize_challenge_counts(team_id):
    print('normalize_challenge_counts')
    #First we get all team members.
    team_members=db.session.query(ZooniverseUsers).filter(TeamMembers.team_id==team_id).filter(ZooniverseUsers.id==TeamMembers.zooniverse_user_id).all()
    team_member_ids=[]
    updated_team_member_ids=[]
    for team_member in team_members:
        team_member_ids.append(team_member.id)

    #Next we get all current challenges for this team;
    now = datetime.datetime.now() # current date and time
    now_timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
    print(team_member_ids)
    current_challenges=db.session.query(Challenges).filter(Challenges.team_id==team_id).filter(Challenges.start_datetime<=now_timestamp).filter(Challenges.end_datetime>=now_timestamp).all()
    for current_challenge in current_challenges:
        print(team_member_ids)
        #current_classifications= db.session.query(Classifications.zooniverse_user_id,func.count(Classifications.id)).filter(Classifications.zooniverse_user_id.contains(team_member_ids)).filter(Classifications.created_at>=current_challenge.start_datetime).filter(Classifications.created_at<=current_challenge.end_datetime).group_by(Classifications.zooniverse_user_id).all()
        current_classifications= db.session.query(Classifications.zooniverse_user_id,func.count(Classifications.id)).filter(Classifications.zooniverse_user_id.in_(team_member_ids)).filter(Classifications.created_at>=current_challenge.start_datetime).filter(Classifications.created_at<=current_challenge.end_datetime).group_by(Classifications.zooniverse_user_id).all()
        
        for current_classification in current_classifications:
            print(current_classification)
            print("Update this user:")
            print(current_classification[0],current_classification[1])
            update_challenge_counts(current_challenge.id,current_classification[0],current_classification[1])
            updated_team_member_ids.append(current_classification[0])
        print(team_member_ids,updated_team_member_ids)
        for team_member in team_member_ids:
            print(current_challenge.id,team_member,0)
            if team_member not in updated_team_member_ids:
                print("zero")
                update_challenge_counts(current_challenge.id,team_member,0)








            # filter(TestUser.numbers.contains([some_int]))
# session.query(Table.column, func.count(Table.column)).group_by(Table.column).all(
# select zooniverse_user_id,count(*) from classifications where created_at <'2022-02-21 00:33:00' and created_at
# >'2021-02-01 08:33:00' and zooniverse_user_id in (2426149,-1) group by zooniverse_user_id;




    
    
    # challenge_counts=db.session.query(ChallengeCounts).filter(ChallengeCounts.id==challenge_id).all()
    # current_challenge_users=[]
    # for challenge_count in challenge_counts:
    #     current_challenge_users.append(challenge_count.user_id)
    # for team_member in team_members:
    #     if team_member.id not in current_challenge_users:
    #         new_challenge_member=ChallengeCounts(challenge_id=challenge_id,user_id=team_member.id,count =0)
    # select zooniverse_user_id,count(*) from classifications where created_at <'2022-02-21 00:33:00' and created_at >'2021-02-01 08:33:00' and zooniverse_user_id in (2426149,-1) group by zooniverse_user_id;
    # db.session.add(new_challenge_member)

    # for challenge_count in challenge_counts:
    #     if challenge_count.user_id not in team_member_ids:
    #             delete_row=db.session.query(ChallengeCounts).filter(ChallengeCounts.challenge_id==challenge_id).filter(ChallengeCounts.user_id==challenge_count.user_id).delete()
    #             db.session.commit()

@challenges_bp.route("/create_challenge/<challenge_type>" , methods=['GET','POST']) 
@login_required
def create_challenge(challenge_type):
    if request.method == 'GET':
        if challenge_type=='cooperative':
            my_teams=db.session.query(Teams).filter(Teams.owner_id==current_user.id).all()
            if my_teams:
                teams=[]
                for team in my_teams:
                    print(team.id)
                    teams.append({'id':team.id,'name':team.name})
                body=render_template('create_cooperative_type.html',challenge_type=challenge_type,teams=teams)
                return render_index(body)
            else:
                body=render_template('general_error.html',error_string='You cannot create a challenge unless you have a team.<a style="color:#ba0c2f;" href="/teams/create_a_team">Click here to create one!</a>')
                return render_index(body)
        elif challenge_type=='competitive':
            my_teams=db.session.query(Teams).filter(Teams.owner_id==current_user.id).all()
            if my_teams:
                teams=[]
                for team in my_teams:
                    print(team.id)
                    teams.append({'id':team.id,'name':team.name})
                body=render_template('create_competitive_type.html',challenge_type=challenge_type,teams=teams)
                return render_index(body)
            else:
                body=render_template('general_error.html',error_string='You cannot create a challenge unless you have a team.<a style="color:#ba0c2f;" href="/teams/create_a_team">Click here to create one!</a>')
                return render_index(body)

        elif challenge_type=='team':
            my_teams=db.session.query(Teams).filter(Teams.owner_id==current_user.id).all()


            if my_teams:
                all_teams=db.session.query(Teams).all()
                all_teams_list=[]
                for team in all_teams:
                    is_owner=False
                    if team.owner_id==current_user.id:
                        is_owner=True
                        #TODO unindent when we add teams the creator does not own:
                        all_teams_list.append({'name':team.name,'id':team.id,'is_owner':is_owner})
                teams=[]
                for team in my_teams:
                    print(team.id)
                    teams.append({'id':team.id,'name':team.name})
                body=render_template('create_team_type.html',challenge_type=challenge_type,teams=teams,all_teams=all_teams_list)
                return render_index(body)
            else:
                body=render_template('general_error.html',error_string='You cannot create a challenge unless you have a team.<a style="color:#ba0c2f;" href="/teams/create_a_team">Click here to create one!</a>')
                return render_index(body)
        else:
            body=render_template('general_error.html',error_string='Comming Soon!')
            return render_index(body)            
    if request.method == 'POST':
        challenge_json = request.get_json()
        if challenge_type=='cooperative':
            team_members=db.session.query(ZooniverseUsers).filter(TeamMembers.team_id==int(challenge_json['team'])).filter(ZooniverseUsers.id==TeamMembers.zooniverse_user_id).all()

            new_challenge=Challenges()
            try:
                new_challenge=Challenges(name = challenge_json['challenge_name'],team_id =int(challenge_json['team']) ,goal_number = challenge_json['goal_number'],start_datetime=datetime.datetime.fromtimestamp(challenge_json['start_datetime']/1000),end_datetime= datetime.datetime.fromtimestamp(challenge_json['end_datetime']/1000),public=challenge_json['public'],type='cooperative')
                db.session.add(new_challenge)
                db.session.flush()
                db.session.refresh(new_challenge)
                for team_member in team_members:
                    exists=db.session.query(ChallengeCounts).filter(challenge_id=new_challenge.id,user_id=team_member.id).first()
                    if not exists:
                        new_challenge_member=ChallengeCounts(challenge_id=new_challenge.id,user_id=team_member.id,count =0)
                        db.session.add(new_challenge_member)
                db.session.commit()
                return {'status':'success','message':'Challenge Created!','challenge_id':new_challenge.id}
            except Exception as err:
                db.session.rollback()
                db.session.flush()
                return {'status':'error','message':str(err)}
        

        if challenge_type=='competitive':
            team_members=db.session.query(ZooniverseUsers).filter(TeamMembers.team_id==int(challenge_json['team'])).filter(ZooniverseUsers.id==TeamMembers.zooniverse_user_id).all()

            new_challenge=Challenges()
            try:
                new_challenge=Challenges(name = challenge_json['challenge_name'],team_id =int(challenge_json['team']) ,start_datetime=datetime.datetime.fromtimestamp(challenge_json['start_datetime']/1000),end_datetime= datetime.datetime.fromtimestamp(challenge_json['end_datetime']/1000),public=challenge_json['public'],type='competitive')
                db.session.add(new_challenge)
                db.session.flush()
                db.session.refresh(new_challenge)
                for team_member in team_members:
                    new_challenge_member=ChallengeCounts(challenge_id=new_challenge.id,user_id=team_member.id,count =0)
                    db.session.add(new_challenge_member)
                db.session.commit()
                return {'status':'success','message':'Challenge Created!','challenge_id':new_challenge.id}
            except Exception as err:
                db.session.rollback()
                db.session.flush()
                return {'status':'error','message':str(err)}

        if challenge_type=='team':
            if challenge_json['team']:
                list_of_team_ids=challenge_json['team']

                # new_challenge=Challenges()
                try:
                    new_challenge=Challenges(name = challenge_json['challenge_name'],team_id =None ,start_datetime=datetime.datetime.fromtimestamp(challenge_json['start_datetime']/1000),end_datetime= datetime.datetime.fromtimestamp(challenge_json['end_datetime']/1000),public=challenge_json['public'],type='team')
                    db.session.add(new_challenge)
                    db.session.flush()
                    db.session.refresh(new_challenge)
                    #TODO This will be changed when teams that do not belong to creator are added.
                    for team_id in list_of_team_ids:
                        new_team_challenge=TeamChallenges(team_id=int(team_id),challenge_id=new_challenge.id)
                        db.session.add(new_team_challenge)

                        team_members=db.session.query(ZooniverseUsers).filter(TeamMembers.team_id==int(team_id)).filter(ZooniverseUsers.id==TeamMembers.zooniverse_user_id).all()

                        for team_member in team_members:
                            new_challenge_member=ChallengeCounts(challenge_id=new_challenge.id,user_id=team_member.id,count =0)
                            db.session.add(new_challenge_member)
                    db.session.commit()
                    return {'status':'success','message':'Challenge Created!','challenge_id':new_challenge.id}
                except Exception as err:
                    db.session.rollback()
                    db.session.flush()
                    return {'status':'error','message':str(err)}
            else:
                return {'status':'error','message':'error'}

            
        return {'status':'error','message':'unknown challenge type'}


@challenges_bp.route("/view_challenge/<challenge_id>" , methods=['GET','POST']) 
def view_challenge(challenge_id):

    is_team_challenge=db.session.query(Challenges).filter(Challenges.id==int(challenge_id)).filter(Challenges.type=='team').first()
    if is_team_challenge:
        if request.method == 'GET':

            counts=db.session.query(Teams.name,func.sum(ChallengeCounts.count)
            ).filter(ChallengeCounts.challenge_id==int(challenge_id)
            ).filter(ChallengeCounts.challenge_id==TeamChallenges.challenge_id
            ).filter(TeamChallenges.team_id==Teams.id
            ).filter(TeamMembers.team_id==Teams.id
            ).filter(TeamMembers.zooniverse_user_id==ChallengeCounts.user_id
            ).group_by(Teams.id
            ).order_by(func.sum(ChallengeCounts.count).desc()
            ).all()



            counts_list=[]
            order=1
            for count in counts:
                counts_list.append({'order':ordinal(order),'name':count[0],'count':int(count[1])})
                order+=1
            
            
            body=render_template('view_team_challenge.html',counts=counts_list,challenge_id=challenge_id,end=is_team_challenge.end_datetime)
            return render_index(body)
            #return ":)"

        
    else:
        this_challenge=db.session.query(Challenges,Teams).filter(Challenges.id==int(challenge_id)).filter(Teams.id==Challenges.team_id).first()
        if this_challenge:

            if this_challenge[0].type=="cooperative": 
                challenge_counts=db.session.query(ChallengeCounts,ZooniverseUsers).filter(ChallengeCounts.challenge_id==challenge_id).filter(ZooniverseUsers.id==ChallengeCounts.user_id).order_by(asc(ZooniverseUsers.display_name)).all()

            elif this_challenge[0].type=="competitive": 
                challenge_counts=db.session.query(ChallengeCounts,ZooniverseUsers).filter(ChallengeCounts.challenge_id==challenge_id).filter(ZooniverseUsers.id==ChallengeCounts.user_id).order_by(desc(ChallengeCounts.count)).all()
            else:
                challenge_counts=db.session.query(ChallengeCounts,ZooniverseUsers).filter(ChallengeCounts.challenge_id==challenge_id).filter(ZooniverseUsers.id==ChallengeCounts.user_id).all()
            counts=[]
            order=1
            for count in challenge_counts:
                if this_challenge[0].type=="competitive":
                    counts.append({'order':ordinal(order),'display_name':count[1].display_name,'avatar_src':count[1].avatar_src,'count':count[0].count})
                    order+=1
                else:
                    counts.append({'display_name':count[1].display_name,'avatar_src':count[1].avatar_src,'count':count[0].count})
            print(counts)
        else:
            body=render_template('general_message.html',error_string="Challenge ID not found.")
            return render_index(body)  
        if request.method == 'GET':
            if this_challenge[0].type=="cooperative": 
                if this_challenge:
                    is_public=this_challenge[0].public
                    if current_user.is_authenticated:
                        is_owner=current_user.id==this_challenge[1].owner_id
                    else:
                        is_owner=False
                    goal_number=this_challenge[0].goal_number
        
                    if is_public or is_owner:

                        
                        body=render_template('view_cooperative_challenge.html',counts=counts,goal_number=goal_number,challenge_id=challenge_id,end=this_challenge[0].end_datetime)
                        return render_index(body)
                else:
                    body=render_template('general_message.html',error_string="Challenge ID not found.")
                    return render_index(body)
            if this_challenge[0].type=="competitive": 
                if this_challenge:
                    is_public=this_challenge[0].public
                    is_owner=current_user.id==this_challenge[1].owner_id
                    goal_number=this_challenge[0].goal_number
                    if is_public or is_owner:

                        
                        body=render_template('view_competitive_challenge.html',counts=counts,challenge_id=challenge_id,end=this_challenge[0].end_datetime)
                        return render_index(body)
                else:
                    body=render_template('general_message.html',error_string="Challenge ID not found.")
                    return render_index(body)        
            return ":)"
        if request.method == 'POST':
            counts_obj={}
            counts_obj['counts']=counts
            counts_obj['goal']=this_challenge[0].goal_number
            return counts_obj
