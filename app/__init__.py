from flask import Flask
from dotenv import load_dotenv
import os
from flask_pymongo import PyMongo
from flask_mail import Mail,Message
import json
from flask_apscheduler import APScheduler
from app.static.scripts.web_scraper import price_tracker,create_headless_driver
from app.static.scripts.APIcaller import search_flight
from bson.json_util import dumps

mail = Mail()
mongo = PyMongo(maxPoolSize=50,   # Maximum number of connections
    minPoolSize=10,   # Minimum number of connections
    maxIdleTimeMS=120000  # Time before a connection is closed if idle
    )
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
            tracked = []
            for data in tracker_data:
                source = data["source"]
                destination = data["destination"]
                date = data["date"]
                adults = data["adults"]
                cabin_class = data["cabin_class"]
                flight_no = data["flight_no"]
                price = data["price"]
                takeoff_time = data["takeoff_time"]
                track_cheap = data["trackCheap"]
                target = [source,destination,date]
                if not any(item[:3] == target for item in tracked):
                    flight_result = search_flight(source,destination,date,adults,cabin_class)
                    
                    target.append(flight_result)
                    tracked.append(target)
                else:
                    flight_result = search_flight(source,destination,date,adults,cabin_class)

                for flight in flight_result:
                    # results format: [flight logo url, fligh name and flight no, price, duration, takeoff terminal, landing terminal, takeoff time, landing time, date, booking_url]
                    subject = None
                    price_change = "neutral"
                    if track_cheap:
                        subject = f"✨ Hot Deal Alert! ✈️ Cheapest Flight on {data['date']}: {data['flight_no']} from {data['source']} to {data['destination']}! 💸"

                        flight_data = flight
                        break

                    if flight_no == flight[1]:
                        float_price_new = float(flight[2].replace("$",""))
                        float_price_old = float(price.replace("$",""))

                        if float_price_new > float_price_old:
                            subject = f"Price Spike Alert! 🚀 Flight {data['flight_no']} from {data['source']} to {data['destination']} Just Got More Expensive! 💰"
                            price_change = "up"
                        elif float_price_new < float_price_old:
                            subject = f"Great News! ✈️ Flight {data['flight_no']} from {data['source']} to {data['destination']} is Now Cheaper! 🎉"
                            price_change = "down"
                        # checking for flight time change
                        if takeoff_time != flight[6]:
                            subject = f"Important Update! ✈️ Flight {data['flight_no']} from {data['source']} to {data['destination']} Has a New Departure Time 🕒"
                        
                        flight_data = flight
                        break
                    
                        

                message_body = f"""
                    Flight Details ✈️

                    Flight Number: {flight_data[1]}
                    Route: {source} ➡️ {destination}
                    Date: {flight_data[8]}
                    Take Off Time: {flight_data[6]}
                    Landing Time: {flight_data[7]} 
                    Take Off Terminal: {flight_data[4]}
                    Landing Terminal: {flight_data[5]}

                    Current Price: 💸{flight_data[2]}💸

                    Safe travels! ✈️
                """                            
                recipient_mail = [data["email"]]
                msg = Message(
                    subject=subject,
                    recipients = recipient_mail,
                    body=message_body
                )
                try:
                    if subject:
                        mongo.db.usersearch.update_one({
                            "flight_no":data["prev_flight_no"],
                            "email":data["email"],
                            "date":date,
                            "source":source,
                            "destination":destination
                            },
                            {"$set":{
                                "flight_no":flight[1],
                                "flight_url":flight[0],
                                "duration":flight[3],
                                "airport_takeoff":flight[4],
                                "airport_landing":flight[5],
                                "takeoff_time":flight[6],
                                "landing_time":flight[7],
                                "price":flight[2],
                                "url":flight[-1],
                                "price_change":price_change,
                                }
                            })
                        mail.send(msg)
                        print(f"Mail sent to {recipient_mail} :)")
                except Exception as e:
                    print("An error occured : ",e)


                # driver = create_headless_driver()
                # results.append(price_tracker(driver,data))
                # driver.quit()

            
        
            
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
                                                                "duration":data["duration"],
                                                                "take_off_date":data["take_off_date"],
                                                                "landing_date":data["landing_date"]
                                                                }
                                                            })
                            
                            if data["trackCheap"]:
                                subject = f"✨ Hot Deal Alert! ✈️ Cheapest Flight on {data['date']}: {data['flight_no']} from {data['source']} to {data['destination']}! 💸"
                            elif data["price_change"] == "up":
                                subject = f"Price Spike Alert! 🚀 Flight {data['flight_no']} from {data['source']} to {data['destination']} Just Got More Expensive! 💰"
                            elif data["price_change"] == "down":
                                subject = f"Great News! ✈️ Flight {data['flight_no']} from {data['source']} to {data['destination']} is Now Cheaper! 🎉"
                            else:
                                pass
                            cleaned_price = data['price'].replace('\\u20b9', '₹')
                            message_body = f"""
                            Flight Details ✈️

                            Flight Number: {data['flight_no']}
                            Route: {data['source']} ➡️ {data['destination']}
                            Date: {data['date']}
                            Take Off Time: {data['take_off']} {data['take_off_date']}
                            Landing Time: {data['landing_at']} {data['landing_date']}
                            Take Off Terminal: {data['terminal_takeoff']}
                            Landing Terminal: {data['terminal_landing']}

                            Current Price: 💸{cleaned_price}💸

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
           

        


    return app

