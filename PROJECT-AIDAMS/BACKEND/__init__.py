from flask import Flask

def create_app():
    app = Flask(__name__, static_folder='static')
    
    app.config['SECRET_KEY'] = 'Z9qHUK7SXPcb00MSDN9yiPhJEvJndjzH'
    from .views import views
    from.auth import auth
    
    app.register_blueprint(views, url_prefix='/')
    app.register_blueprint(auth, url_prefix='/')
    
    return app
    