from flask import Flask,render_template,request
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user, login_user, logout_user, login_required

#Creating flask app
app = Flask(__name__)
app.config.from_object('config.DevConfig')

#These variables are accessed from this definition from other parts of the app.
#Do not remove
app_config=app.config
db = SQLAlchemy(app)
login_manager = LoginManager(app)
static_path=app.root_path+"/static/"

#POST APP Imports
#These imports rely on app so they have to be loaded after flask app is created.
from views.admin import render_index

# Import blueprints
from views.dashboard import dashboard_bp
from views.admin import admin_bp
from views.teams import teams_bp

# Register blueprints
app.register_blueprint(dashboard_bp,url_prefix='/dashboard')
app.register_blueprint(admin_bp,url_prefix='/admin')
app.register_blueprint(teams_bp,url_prefix='/teams')



@app.route("/" , methods=['GET', 'POST']) 
def root():

    rs=db.session.execute('select display_name,avatar_src, zooniverse_users.id,count from counts_all,zooniverse_users where counts_all.zooniverse_user_id=zooniverse_users.id and zooniverse_users.id>=0 order by count DESC limit 10;')

    top_contributors=[]

    for row in rs:
        top_contributors.append({'name':row[0],'avatar':'/static/avatars/'+row[1],'user_id':row[2],'count':row[3]})

    body=render_template('index_body.html',top_contributors=top_contributors)
    return render_index(body)
    #return render_template('index.html' , is_authenticated=current_user.is_authenticated, body=body)

@app.login_manager.unauthorized_handler
def unauth_handler():
        body=render_template('401.html')
        
        return render_index(body), 401

        