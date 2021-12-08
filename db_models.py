# coding: utf-8

from app import db, app
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


