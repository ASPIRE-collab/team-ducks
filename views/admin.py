""" Routes for user Authentication """
import hashlib
import json
import logging
import smtplib
import random
import string
import os
import csv
import requests

from flask import Blueprint, flash, redirect, render_template, request, url_for,current_app,url_for, make_response,jsonify
from werkzeug.utils import secure_filename
from flask.scaffold import F
from flask_login import current_user, login_user, logout_user, login_required
from flask_login.utils import wraps
from uuid import uuid4
from app import login_manager,app_config,static_path 
from db_models import User, Roles,UserRoles,PasswordResetTokens,Classifications,db,ZooniverseUsers
from datetime import datetime,timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from panoptes_client import Panoptes
from panoptes_client import User as ZooniverseUser

# Blueprint Configuration
admin_bp = Blueprint(
    'admin_bp',__name__,
    template_folder='templates',
    static_folder='static')

logging.getLogger().setLevel(logging.INFO)

#+-+-+-+-+-+-+-+ +-+-+-+-+-+-+-+-+-+
#|U|t|i|l|i|t|y| |F|u|n|c|t|i|o|n|s|
#+-+-+-+-+-+-+-+ +-+-+-+-+-+-+-+-+-+
def get_current_user_ids():
    return_list=[]
    all_users=db.session.query(ZooniverseUsers.id).all()
    for user in all_users:
        return_list.append(user[0])
    return return_list


def add_zooniverse_user(user_id,current_users):
    """Adds new users to the DB with avatars.
    
    Args:
        user_id (integer): Zooniverse user id.
        current_users list(integer): list of zooniverse users currently in system.
    Returns:
        array: list of current users or ERR. 
    """
    #connect using Panoptes and get user object.
    Panoptes.connect()
    users = ZooniverseUser.where(id=user_id)
    insert_dict={}
    #This returns a generator, but only one time will be generated.
    for item in users:
        #If the user has a custom avatar we download it locally, otherwise we set it to the default.
        #We are storing locally to avoid a ton of requests for images when we want to render a team or whatnot.
        if item.avatar_src:
            avatar_src=str(item.id)+".jpeg"
            avatar_path=os.path.join(static_path,"avatars",avatar_src)
            r = requests.get(item.avatar_src, allow_redirects=True)
            open(avatar_path, 'wb').write(r.content)
        else:
            avatar_src="default.png"
        #We store the userdata  in a temporary dictionary.
        insert_dict['avatar_src']=avatar_src
        insert_dict['id']=int(item.id)
        insert_dict['display_name']=item.display_name
        insert_dict['credited_name']=item.credited_name
    #We add it to the current_users, so if we come across this user again, we can skip it.
    if item.id not in current_users:
        current_users.append(item.id)
    #Add new user to our table.
    try:
        newZUser = ZooniverseUsers(id=insert_dict['id'],display_name=insert_dict['display_name'],credited_name=insert_dict['credited_name'],avatar_src=insert_dict['avatar_src'])
        db.session.add(newZUser)
        db.session.commit()
    except Exception as err:
        db.session.rollback()
        db.session.flush()
        return err
    #We return the updated list even though this is not necessary as the list is passed by reference.
    return current_users


def get_random_string(length):
    """Generates random strings.
    Args:
        length (integer): length of random string to be generated.

    Returns:
        string: Random ascii string. 
    """
    letters = string.ascii_lowercase
    result_str = ''.join(random.choice(letters) for i in range(length))
    return result_str


def send_email(recipients, subject, body,htmlbody):
    """Creates HTML e-mail and sends to recipients.
       Primarily used for password reset, but could be used for other purposes.

    Args:
        recipients ([list]): String list of email addresses.
        subject (string): String used in for subject of e-mail.
        body (string): String for body in case the recipient does not have HTML enabled in their e-mail client.
        htmlbody (string): Body of the HTML sent.

    Returns:
        redirect: Returns redirect to the login page.
    """
    sender = app_config['MAIL_ADDRESS']
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = recipients
    part1 = MIMEText(body, 'plain')
    part2 = MIMEText(htmlbody, 'html')
    try:
        msg.attach(part1)
        msg.attach(part2)
        smtp = smtplib.SMTP(app_config['MAIL_SERVER'], app_config['MAIL_PORT'])
        smtp.starttls()
        smtp.login(app_config['MAIL_USERNAME'], app_config['MAIL_PASSWORD'])
        smtp.sendmail(sender, recipients, msg.as_string()) 
        smtp.quit()
    except Exception as e:
        print(e)
    return redirect(url_for('admin_bp.login'))


def send_password_reset_email(user,headertitle,blurb):
    """Generates a tokens and sends token to user via send_mail function.

    Args:
        user (object): User tuple from DB.
        headertitle (string): String for the header in the email.
        blurb (string): String describing the purpose of the e-mail.

    Returns:
        Exception: Returns Exception if there is one, otherwise returns 0
    """
    expire_date=datetime.now()
    expire_date += timedelta(days=1)

    token = str(uuid4())
    try:
        newToken = PasswordResetTokens(user_id=user.id, token=token,expire_date=str(expire_date))
        db.session.add(newToken)
        db.session.commit()
    except Exception as err:
        db.session.rollback()
        db.session.flush()
        return err
    try:
        link = url_for('admin_bp.token_password_reset', token=token, _external=True)
        body = 'Please use this link to reset your password {}'.format(link)
        htmlbody = render_template('password_reset_email.html', link=link,firstname=user.first_name,headertitle=headertitle,blurb=blurb)
        send_email(user.email,"Password Reset", body,htmlbody)
    except Exception as e:
        return e


def is_admin(user_obj):
    """Simple function to check if user is an admin

    Args:
        user_obj (tuple): User object from DB.

    Returns:
        Bool: True if user is admin else False
    """
    admin_role_row=db.session.query(UserRoles).filter(UserRoles.user_id==user_obj.id).filter(UserRoles.role_id==Roles.id).filter(Roles.id==1).first()
    if admin_role_row:
        return True
    else:
        return False




def get_all_user_roles():
    """Generate object with each key being the user id and the value being a list of role ids;
    Returns:
        object: user_roles_obj
    """
    user_roles_obj={}
    user_roles_rows=db.session.query(UserRoles).all()
    for user_role in user_roles_rows:
        if user_role.user_id not in user_roles_obj:
            user_roles_obj[user_role.user_id]=[]
        user_roles_obj[user_role.user_id].append(user_role.role_id)
    return user_roles_obj

def reset_user_roles(user_id,new_roles_list):
    """Adds and removes roles based on the new_roles_list list.
    Args:
        user_id (integer): The user ID to modify.
        new_roles_list ([string]): List of string integers that represent new role IDs to assign to the user.
    """
    user_roles_obj=get_all_user_roles()

    existing_roles_list=user_roles_obj[user_id]
    new_roles_list = list(map(int, new_roles_list))
    
    try:
        
        for new_role_id in new_roles_list:
            if new_role_id not in existing_roles_list:
                print("need to add "+str(new_role_id))
                newRole=UserRoles(user_id=user_id,role_id=new_role_id)
                db.session.add(newRole)
                db.session.commit()
        for existing_role_id in existing_roles_list:
            if existing_role_id not in new_roles_list:
                print("need to remove "+str(existing_role_id))
                delete_row=db.session.query(UserRoles).filter(UserRoles.user_id==user_id).filter(UserRoles.role_id==existing_role_id).delete()
                db.session.commit()
    except Exception as e:
        raise








#  +-+-+-+-+-+-+
#  |R|o|u|t|e|s|
#  +-+-+-+-+-+-+



@admin_bp.route("/test2")
def admin_test():
    return(str(get_current_user_ids()))


@admin_bp.route("/")
@login_required
def admin_root():
    if is_admin(current_user):
        return render_template('admin.html')
    else:
        return render_template('general_error.html',error_string='Admins Only.')




#  +-+-+-+-+-+-+-+-+-+-+-+-+-+-+ +-+-+-+-+-+-+
#  |A|u|t|h|e|n|t|i|c|a|t|i|o|n| |R|o|u|t|e|s|
#  +-+-+-+-+-+-+-+-+-+-+-+-+-+-+ +-+-+-+-+-+-+
@admin_bp.route('/set_password', methods=['POST'])
def set_password():
    """User password set. the token must match the user id.

    Returns:
        HTML: Error message to the user.
        Redirect: Redirect to login if no error.
    """
    password1 = request.form['password1']
    password2 = request.form['password2']
    token_string = request.form['token']
    user_id = request.form['user_id']
    token=db.session.query(PasswordResetTokens).filter(PasswordResetTokens.token==token_string).first()
    if token:
        user_row=db.session.query(User).filter(User.id==token.user_id).first()
        if user_row.active==False:
            return render_template('general_error.html',error_string='This account has been disabled. Please contact an admin.')
        if token.user_id==int(user_id) and password1==password2:
            salt = get_random_string(64)
            pass_string=password1+salt
            salted_hash = hashlib.sha256(pass_string.encode()).hexdigest()
            try:
                updated_user_row = db.session.query(User).filter(User.id==int(user_id)).update(dict(user_hash=salted_hash,user_salt=salt,active=True))
                delete_row=db.session.query(PasswordResetTokens).filter(PasswordResetTokens.token==token_string).delete()
                db.session.commit()
                return redirect(url_for('admin_bp.login'))
            except Exception as e:
                db.session.rollback()
                db.session.flush()
                return render_template('general_error.html',error_string=str(e))
        else:
            error_string='Token or user mismatch. Please request a new password reset link.'
            return render_template('general_error.html',error_string=error_string)            
    error_string='Invalid Token.'
    return render_template('general_error.html',error_string=error_string)

@admin_bp.route('/token_password_reset/<token>', methods=['GET','POST'])
def token_password_reset(token):
    """Renders a password reset form

    Args:
        token (string): token found in password_reset_tokens table.

    Returns:
        [type]: [description]
    """
    token=db.session.query(PasswordResetTokens).filter(PasswordResetTokens.token==token).first()
    if token:
        if token.expire_date>=datetime.now().date():
            user_info= db.session.query(User).filter(User.id==token.user_id).first()
            return render_template('password_reset_form.html',username=user_info.email,token=token.token,user_id=user_info.id)
        else:
            error_string="This token has expired. Please request a new password reset link."
            return render_template('general_error.html',error_string=error_string)
    else:
        error_string='Invalid Token. Please request a new password reset link.'
        return render_template('general_error.html',error_string=error_string)


@admin_bp.route("/create_user", methods=['GET', 'POST'])
@login_required
def create_user():
    """Renders create user form if GET, otherwise creates user from from post data.

    Returns:
        HTML: Error or success message.
    """

    if is_admin(current_user):
        if request.method == 'GET':
            template_object={"roles":[]}
            all_roles=db.session.query(Roles).all()
            for row in all_roles:
                template_object['roles'].append({'id':row.id,"role_name":row.role_name})
            return render_template('create_user.html',roles_object=template_object)
        if request.method == 'POST':
            email = request.form['email']
            first_name = request.form['first_name']
            last_name = request.form['last_name']
            role = request.form['role']
            user = db.session.query(User).filter(User.email == email).first()
        
            headertitle='Set your Drones for Ducks password.'
            blurb='An API account has been created for you. Before you log in you must change your password.'
            if user:
                error_string="User with email:"+email+" exists."
                return render_template('general_error.html',error_string=error_string)
            else:
                try:
                    newUser=User(email=email,first_name=first_name,last_name=last_name,user_hash='----',user_salt='-')
                    db.session.add(newUser)
                    db.session.flush()
                    db.session.refresh(newUser)
                    newRole=UserRoles(user_id=newUser.id,role_id=role)
                    db.session.add(newRole)
                    db.session.commit()
                    send_password_reset_email(newUser,headertitle,blurb)
                    return render_template('general_message.html',error_string='An e-mail has been set to '+email)
                except Exception as e:
                    error_string="Insert into db failed. Error:"+str(e)
                    return render_template('general_error.html',error_string=error_string)
    else:
        error_string='Only Admins can create new users.'
        return render_template('general_error.html',error_string=error_string)


    

@admin_bp.route("/edit_users", methods=['GET', 'POST'])
@login_required
def edit_users():
    """Genrates a edit users form if a GET or updates user data based on JSON POST.

    Returns:
        HTML: Error or success message.
    """
    if is_admin(current_user):
        if request.method == 'GET':
            user_obj={'users':[]}
            role_obj={'roles':[]}
            user_roles_obj=get_all_user_roles()
            all_users=db.session.query(User).all()
            for user in all_users:
                user_obj['users'].append({'id':user.id,'email':user.email,'first_name':user.first_name,'last_name':user.last_name,'active':user.active,'role_ids':user_roles_obj[user.id]})
            all_roles=db.session.query(Roles).all()
            for role in all_roles:    
                role_obj['roles'].append({'id':role.id,'role_name':role.role_name})
            return render_template('edit_users.html',user_obj=user_obj,role_obj=role_obj)
        elif request.method == 'POST':
            user_json = request.get_json()
            print(user_json)
            new_roles=user_json['roles']
            user_json.pop("roles", None)
            try:
                reset_user_roles(user_json['id'],new_roles)
            except Exception as e:
                return render_template('general_error.html',error_string='test')
            try:
                updated_user_row = db.session.query(User).filter(User.id==int(user_json['id'])).update(user_json)
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                db.session.flush()
                return render_template('general_error.html',error_string=str(e))
            return {'status':'success','message':'user updated.'}
    else:
        return render_template('general_error.html',error_string='Only admins can edit users.')

@admin_bp.route("/login", methods=['GET', 'POST'])
def login():
    """
    Log-in page for registered users.

    GET requests serve Log-in page.
    POST requests validate and redirect user to dashboard.
    """
    if request.method == 'GET':
        # Bypass if user is logged in
        if current_user.is_authenticated:
            return redirect(url_for('dashboard_bp.dashboard'))
        return render_template('login.html')
    # Validate login attempt
    if request.method == 'POST':
        email = request.form['email']
        user = db.session.query(User).filter(User.email == email).first()
        if user:
            if user.active == True:
                string = request.form['password']+user.user_salt
                salted_hash = hashlib.sha256(string.encode()).hexdigest()
                if salted_hash == user.user_hash:
                    login_user(user)
                    return redirect(url_for('root'))
                else:
                    return render_template('general_error.html',error_string='Login Failed.')
            else:
                return render_template('general_error.html',error_string='This account has been disabled.')
        else:
            return render_template('general_error.html',error_string='Account for '+email+' not found.')

    return redirect(url_for('admin_bp.login'))

@admin_bp.route("/password_reset_request", methods=['POST'])
def password_reset_request():
    """Sends and email with instructions on resetting a password.

    Returns:
        HTML: Success message or Error.
    """
    if request.form['email']:
        email = request.form['email']
        user_row=db.session.query(User).filter(User.email==email).first()
        if user_row.active==False:
            return render_template('general_error.html',error_string='This account has been disabled. Please contact an admin.')
        if user_row:
            #This if is used to prevent any sql shenanigans
            if user_row.email==email:
                headertitle='Change your Drones for Ducks password.'
                blurb='A request was made for a password reset link. If you did not request this, please disregard.'
                send_password_reset_email(user_row,headertitle,blurb)
                return render_template('general_message.html',error_string='An e-mail has been set to '+email)
            else:
                return render_template('general_error.html',error_string='Unknown e-mail address.')
        else:
            return render_template('general_error.html',error_string='Unknown e-mail address.')
    else:
        return render_template('general_error.html',error_string='Unknown e-mail address.')



@admin_bp.route('/logout')
def logout():
    """Logs the current user out.

    Returns:
        Redirect: redirect to login page.
    """
    current_app.logger.info("User ID:"+str(current_user.id)+" Email:"+current_user.email+" has logged out.")
    logout_user()
    return redirect(url_for('root'))


@login_manager.user_loader
def user_loader(id):
    print(id)
    """Loads the user into the login_manager

    Args:
        id (int): User id.

    Returns:
        tuple: User object from DB.
    """
    print(1)
    user = db.session.query(User).filter(User.id == id).first()
    print(2)
    return user  

def get_all_classification_ids():
    all_classifications=db.session.query(Classifications.id).all()

    all_classifications_ids=[]
    for id_tupe in all_classifications:
        print(id_tupe)
        all_classifications_ids.append(id_tupe[0])
    return all_classifications_ids



@admin_bp.route('/extracts', methods=['POST'])
def extracts():
    
    try:
        current_users=get_current_user_ids()
        extract_json = request.get_json()
        print(extract_json)
        cdate, frag = extract_json['created_at'].split('.')
        classifications_id=extract_json['id']
        subject_id=extract_json['subject_id']
        zooniverse_user_id=extract_json['user_id']
        if int(zooniverse_user_id) not in current_users:
            current_users=add_zooniverse_user(zooniverse_user_id,current_users)
        newClassification = Classifications(id=int(classifications_id), zooniverse_user_id=int(zooniverse_user_id),created_at=datetime.strptime(cdate, "%Y-%m-%dT%H:%M:%S"),subject_id=int(subject_id))
        db.session.add(newClassification)
        db.session.commit()

        data = {'status': 'RECIEVED', 'message': 'SUCCESS'}
        print('good')
        return make_response(jsonify(data), 201)
    except:
        db.session.rollback()
        db.session.flush()
        data = {'status': 'ERROR', 'message': 'FAIL'}
        return make_response(jsonify(data), 500)


#select zooniverse_user_id, count(*) as count from (select distinct zooniverse_user_id, subject_id  from classifications) as lol group by zooniverse_user_id order by count DESC;



@admin_bp.route('/update_extracts', methods=['GET','POST'])
@login_required
def update_extracts():
    #TODO add function to get all zooniverse ids
    zooniverse_user_ids=[]
    if request.method == 'POST':
        all_classifications_ids=get_all_classification_ids()
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and file.filename.rsplit('.', 1)[1].lower()=='csv':
            filename = secure_filename(file.filename)
            csv_file=os.path.join(app_config['UPLOAD_FOLDER'], filename)
            file.save(csv_file)

            with open(csv_file, newline='') as csvfile:
                csv_reader = csv.reader(csvfile, delimiter=',', quotechar='"')
                next(csv_reader)
                for row in csv_reader:
                    print(int(row[0]))
                    if int(row[0]) not in all_classifications_ids:
                        
                        try:
                            if row[2] not in zooniverse_user_ids:
                                zooniverse_user_ids=add_zooniverse_user(row[2],zooniverse_user_ids)
                            print(row[0],row[2],row[7],row[13])
                            
                            newClassification = Classifications(id=int(row[0]), zooniverse_user_id=int(row[2]),created_at=datetime.strptime(row[7], '%Y-%m-%d %H:%M:%S %Z'),subject_id=int(row[13]))
                            print(row[0],row[2],row[7],row[13])
                            db.session.add(newClassification)
                            db.session.commit()
                        except Exception as err:
                            db.session.rollback()
                            db.session.flush()
                            return str(err)
                    # print(row[0],row[2],row[7],row[13])
            return ":)"
    if request.method == 'GET':
        return '''
        <!doctype html>
        <title>Upload new File</title>
        <h1>Upload new File</h1>
        <form method=post enctype=multipart/form-data>
        <input type=file name=file>
        <input type=submit value=Upload>
        </form>
        '''








