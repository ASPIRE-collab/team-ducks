# coding: utf-8

from app import db
from flask_login import UserMixin

class User(db.Model, UserMixin):
    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True)
    first_name = db.Column(db.String(255))
    last_name = db.Column(db.String(255))
    user_hash = db.Column(db.String(255))
    user_salt = db.Column(db.String(255))
    active = db.Column(db.Integer)




#Class used to store Roles keys.
class Roles(db.Model, UserMixin):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    role_name = db.Column(db.String(255))
    

#Class used to join users and roles.
#This is done in cases where a user might need to have multiple roles.
class UserRoles(db.Model, UserMixin):
    __tablename__ = 'user_roles'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    role_id = db.Column(db.Integer)


#Class used to join users and roles.
#This is done in cases where a user might need to have multiple roles.
class PasswordResetTokens(db.Model, UserMixin):
    __tablename__ = 'password_reset_tokens'
    id = db.Column(db.Integer,primary_key=True)
    user_id=db.Column(db.Integer)
    token = db.Column(db.String(255))
    expire_date = db.Column(db.Date)


class Classifications(db.Model, UserMixin):
    __tablename__ = 'classifications'
    id = db.Column(db.Integer, primary_key=True)
    zooniverse_user_id = db.Column(db.Integer)
    user_ip=db.Column(db.String(40))
    workflow_id= db.Column(db.Integer)
    workflow_version= db.Column(db.Float)
    created_at = db.Column(db.DateTime)
    meta_data = db.Column(db.JSON)
    annotations = db.Column(db.JSON)
    subject_data = db.Column(db.JSON)
    subject_id = db.Column(db.Integer)
    ingest_type=db.Column(db.String(10))

class ZooniverseUsers(db.Model, UserMixin):
    __tablename__ = 'zooniverse_users'
    id = db.Column(db.Integer, primary_key=True)
    display_name = db.Column(db.String(100))
    credited_name = db.Column(db.String(100))
    avatar_src = db.Column(db.String(100))


class CountsAll(db.Model, UserMixin):
    __tablename__ = 'counts_all'
    zooniverse_user_id = db.Column(db.Integer, primary_key=True)
    count = db.Column(db.Integer)


class Teams(db.Model, UserMixin):
    __tablename__ = 'teams'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    owner_id = db.Column(db.Integer)
 
class TeamMembers(db.Model, UserMixin):
    __tablename__ = 'team_members'
    id = db.Column(db.Integer, primary_key=True)
    zooniverse_user_id = db.Column(db.Integer)
    team_id = db.Column(db.Integer)


class Invitations(db.Model, UserMixin):
    __tablename__ = 'invitations'
    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer)
    zooniverse_user_id = db.Column(db.Integer)
    accepted=db.Column(db.Boolean)
    rejected=db.Column(db.Boolean)
    token = db.Column(db.String(255))

class Challenges(db.Model, UserMixin):
    __tablename__ = 'challenges'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    team_id = db.Column(db.Integer)
    goal_number = db.Column(db.Integer)
    start_datetime= db.Column(db.DateTime)
    end_datetime= db.Column(db.DateTime)
    public=db.Column(db.Boolean)
    type = db.Column(db.String(50))

class ChallengeCounts(db.Model, UserMixin):
    __tablename__ = 'challenge_counts'
    id = db.Column(db.Integer, primary_key=True)
    challenge_id = db.Column(db.Integer)
    user_id = db.Column(db.Integer)
    count = db.Column(db.Integer)


# Create Database Models
db.create_all()
db.session.commit()

#Roles standardization
roles_list=[{'id':1,"role_name":'Admin'},{'id':2,"role_name":'Data Viewer'}]
#Add standard groups if missing or incorrect:
all_roles = db.session.query(Roles).all()
db_roles_list=[]
for row in all_roles:
    db_roles_list.append({'id':row.id,"role_name":row.role_name})

if roles_list!=db_roles_list:
    print("Creating Roles")
    Roles.query.filter(Roles.id>0).delete()
    db.session.commit()
    for role in roles_list:
        newRole = Roles(id = role['id'],role_name = role['role_name'])
        db.session.add(newRole)
    db.session.commit()  


