from flask import Flask
from dotenv import load_dotenv
import os
from flask_pymongo import PyMongo
from flask_mail import Mail

mail = Mail()
mongo = PyMongo()
load_dotenv()



def create_app():

    app = Flask(__name__)

    # Allow HTTP for development
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

    # Replace with your actual credentials
    app.config["MONGO_URI"] = "mongodb+srv://zoomershredder:e6ndNLxgAWpNIKsb@cluster0.8blyf.mongodb.net/trackIt?retryWrites=true&w=majority&appName=Cluster0"
    app.config["SECRET_KEY"] = os.urandom(24)

    # Mailtrap configuration
    app.config['MAIL_SERVER']='smtp.gmail.com'
    app.config['MAIL_PORT'] = 587
    app.config['MAIL_USERNAME'] = os.getenv("GMAIL-ACCOUNT")
    app.config['MAIL_PASSWORD'] = os.getenv("PASS-KEY")
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USE_SSL'] = False
    app.config['MAIL_DEFAULT_SENDER'] = os.getenv("GMAIL-ACCOUNT")


    from .auth import auth

    app.register_blueprint(auth, url_prefix = "/")
    mongo.init_app(app)
    mail.init_app(app)


    

    # try:
    #     db.session.query(User).all()
    # except OperationalError as err:
    #     print("Connection error at backend side!",err)
    return app

