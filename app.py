from flask import Flask,render_template
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user, login_user, logout_user, login_required
app = Flask(__name__)
app.config.from_object('config.DevConfig')

#These variables are accessed from this definition from other parts of the app.
#Do not remove
app_config=app.config
db = SQLAlchemy(app)
login_manager = LoginManager(app)
static_path=app.root_path+"/static/"


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
    rs=db.session.execute('select display_name,avatar_src, zooniverse_user_id, count(*) as count from (select distinct zooniverse_user_id, zooniverse_users.display_name, zooniverse_users.avatar_src,subject_id  from classifications,zooniverse_users where zooniverse_users.id=classifications.zooniverse_user_id) as lol group by zooniverse_user_id order by count DESC LIMIT 10;')

    top_contributors=[]

    for row in rs:
        top_contributors.append({'name':row[0],'avatar':'/static/avatars/'+row[1],'user_id':row[2],'count':row[3]})
    print(top_contributors)
    body=render_template('index_body.html',top_contributors=top_contributors)

    return render_template('index.html' , is_authenticated=current_user.is_authenticated, body=body)

