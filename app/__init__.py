from flask import Flask
from dotenv import load_dotenv
import os
from flask_pymongo import PyMongo
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

    @scheduler.task("cron",id="update_price",hour=17,minute=22)
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
                        if not data["stale"]:
                            print(data)
                            mongo.db.usersearch.update_one({"flight_no":data["prev_flight_no"]},
                                                           {"$set":{
                                                                "price":data["price"],
                                                                "flight_no":data["flight_no"],
                                                                "take_off":data["take_off"],
                                                                "landing_at":data["landing_at"],
                                                                "price_change":data["price_change"],
                                                                "terminal_takeoff":data["terminal_takeoff"],
                                                                "terminal_landing":data["terminal_landing"],
                                                                "duration":data["duration"]
                                                                }
                                                            })
                            
                            if data["trackCheap"]:
                                subject = f"✨ Hot Deal Alert! ✈️ Cheapest Flight on {data["date"]}: {data["flight_no"]} from {data["source"]} to {data["destination"]}! 💸"
                            elif data["price_change"] == "up":
                                subject = f"Price Spike Alert! 🚀 Flight {data["flight_no"]} from {data["source"]} to {data["destination"]} Just Got More Expensive! 💰"
                            elif data["price_change"] == "down":
                                subject = f"Great News! ✈️ Flight {data["flight_no"]} from {data["source"]} to {data["destination"]} is Now Cheaper! 🎉"
                            else:
                                pass
                            message_body = f"""
                            Flight Details ✈️

                            Flight Number: {data["flight_no"]}
                            Route: {data["source"]} ➡️ {data["destination"]}
                            Date: {data["date"]}
                            Take Off Time: {data["take_off"]}
                            Landing Time: {data["landing_at"]}
                            Take Off Terminal: {data["terminal_takeoff"]}
                            Landing Terminal: {data["terminal_landing"]}

                            Current Price: 💸{data["price"].replace("\\u20b9", "₹")}💸

                            Safe travels! ✈️
                            """                            
                            recipient_mail = [data["email"]]
                            msg = Message(
                                subject=subject,
                                recipients = recipient_mail,
                                body=message_body
                            )
                            mail.send(msg)
                            print(f"Mail sent to {recipient_mail} :)")
                        else:
                            mongo.db.usersearch.delete_one({
                                "date":data["date"],
                                "flight_no":data["flight_no"]
                            })
            except Exception as e:
                print(f"An error occured:{e}")
           

        

    # try:
    #     db.session.query(User).all()
    # except OperationalError as err:
    #     print("Connection error at backend side!",err)
    return app

