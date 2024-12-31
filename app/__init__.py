from flask import Flask
from dotenv import load_dotenv
import os
from flask_pymongo import PyMongo,MongoClient
from flask_mail import Mail,Message
import json
from flask_apscheduler import APScheduler
from app.static.scripts.script import price_tracker,create_headless_driver
from bson.json_util import dumps

mail = Mail()
mongo = PyMongo()
scheduler = APScheduler()




def create_app():

    app = Flask(__name__)
    load_dotenv()

    # Allow HTTP for development
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

    # Replace with your actual credentials
    app.config["MONGO_URI"] = os.getenv("DATABASE_URI")
    app.config["SECRET_KEY"] = os.urandom(24)

    # Mailtrap configuration
    app.config['MAIL_SERVER']='smtp.gmail.com'
    app.config['MAIL_PORT'] = 587
    app.config['MAIL_USERNAME'] = os.getenv("GMAIL-ACCOUNT")
    app.config['MAIL_PASSWORD'] = os.getenv("PASS-KEY")
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USE_SSL'] = False
    app.config['MAIL_DEFAULT_SENDER'] = os.getenv("GMAIL-ACCOUNT")

    # Scheduler configuration
    app.config['SCHEDULER_API_ENABLED'] = True

    

    @app.template_filter('json_loads')
    def json_loads_filter(s):
        return json.loads(s)

    from .auth import auth,create_oauth
    create_oauth(app)

    app.register_blueprint(auth, url_prefix = "/")
    mongo.init_app(app)
    mail.init_app(app)
    scheduler.init_app(app)
    scheduler.start()

    @scheduler.task("cron",id="update_price",hour=20,minute=32)
    def update_price():
        with app.app_context():
            tracker_data = mongo.db.usersearch.find()
            results = []
            for data in tracker_data:
                print(data)
                driver = create_headless_driver()
                results.append(price_tracker(driver,data))
                driver.quit()
                print(results)

            
        
            
            try:
                for data in results:
                    if data != None:
                        if data["price_change"] == "up":
                            subject = dumps(f"Flight no:{data["flight_no"]} from {data["source"]} to {data["destination"]} price increased!")
                        elif data["price_change"] == "down":
                            subject = dumps(f"Flight no:{data["flight_no"]} from {data["source"]} to {data["destination"]} price decreased!")
                        else:
                            subject = dumps(f"Flight no:{data["flight_no"]} from {data["source"]} to {data["destination"]}")
                        message_body = dumps(f"Flight no:{data["flight_no"]} from {data["source"]} to {data["destination"]} taking off on {data["date"]} at {data["take_off"]} and landing at {data["landing_at"]} costs {data["price"]}.")
                        recipient_mail = dumps(data["email"])
                        msg = Message(
                            subject=subject,
                            recipients = [recipient_mail],
                            body=message_body
                        )
                        mail.send(msg)
                        print(f"Mail sent to {recipient_mail} :)")
            except Exception as e:
                print(f"An error occured:{e}")
           

        

    # try:
    #     db.session.query(User).all()
    # except OperationalError as err:
    #     print("Connection error at backend side!",err)
    return app

