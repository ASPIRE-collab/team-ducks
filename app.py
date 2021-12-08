from flask import Flask,render_template
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user, login_user, logout_user, login_required
app = Flask(__name__)
app.config.from_object('config.DevConfig')

#app_config is accessed from this definition from other parts of the app.
#Do not remove
app_config=app.config

# Initialize Plugins
db = SQLAlchemy(app)
login_manager = LoginManager(app)
# db.init_app(app)
# login_manager.init_app(app)

# Import blueprints
from views.dashboard import dashboard_bp
from views.admin import admin_bp


# Register blueprints
app.register_blueprint(dashboard_bp,url_prefix='/dashboard')
app.register_blueprint(admin_bp,url_prefix='/admin')


@app.route("/" , methods=['GET', 'POST']) 
def root():
    return render_template('index.html' , is_authenticated=current_user.is_authenticated)

