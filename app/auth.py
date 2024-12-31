from flask import Blueprint, request, jsonify, flash, session, redirect, url_for, render_template
from flask_mail import Message
from . import mail, mongo, scheduler
from .model import User
from authlib.integrations.flask_client import OAuth
from dotenv import load_dotenv
import os
import secrets
from app.static.scripts.script import cheapest_flight,price_tracker,date_optimiser,create_headless_driver
import json
from bson.json_util import dumps
import asyncio







# Load environment variables
load_dotenv()

# Initialize Blueprint
auth = Blueprint("auth", __name__)


# Initialize OAuth
oauth = OAuth()

# Initialize OAuth with your Flask app
def create_oauth(app):
    oauth.init_app(app)



google = oauth.register(
    name="google",
    client_id=os.getenv("CLIENT_ID"),
    client_secret=os.getenv("CLIENT_SECRET"),
    authorize_url=os.getenv("AUTH_URI"),
    access_token_url=os.getenv("TOKEN_URI"),
    jwks_uri="https://www.googleapis.com/oauth2/v3/certs",
    client_kwargs={
        "scope": "openid email profile"
    },
    redirect_uri="http://localhost:5000/callback"  # Adjust this to match your setup
)

# User Schema (replace with your model logic)
user_schema = User()

def test_connection():
    try:
        # Test connection
        print(mongo.db.list_collection_names())  # This will raise an exception if the connection fails
        print("MongoDB connection is successful")
    except Exception as e:
        print(f"MongoDB connection failed: {e}")
    return None




async def run_with_timeout(func, timeout, driver, source, destination, departure_date, option, direct=False):
    try:
        # Run the function with timeout
        return await asyncio.wait_for(
            func(driver, source, destination, departure_date, option, direct),
            timeout=timeout
        )
    except asyncio.TimeoutError:
        print("took too long!")
        try:
            if driver.session_id is not None:
                driver.quit()
        except Exception as e:
            print(f"Error while closing driver: {e}")
        return "timeout"

@auth.route("/",methods=["GET"])
def main_page():
    test_connection()
    return render_template("index.html")

@auth.route("/signup",methods=["GET","POST"])
def singup():
    nonce = secrets.token_urlsafe(16)
    session["nonce"] = nonce
    return google.authorize_redirect(redirect_uri=url_for("auth.callback",_external=True),nonce=nonce)
    

@auth.route("/callback",methods=["GET","POST"])
def callback():
    
    """Handle the OAuth callback."""
    try:
        # Fetch OAuth token
        token = google.authorize_access_token()
        user_info = google.parse_id_token(token,nonce=session.get("nonce")) #

        # Extract user details
        email = user_info.get("email")
        name = user_info.get("name")

        if not email:
            flash("Email not found in OAuth response!", "error")
            return render_template("index.html")

        # Check and store user in MongoDB
        user_collection = mongo.db.userdata
        existing_user = user_collection.find_one({"email": email})
        
        if not existing_user:
            # Store user details in session
            session["user"] = name
            session["mail"] = email
            session["tracked_search"] = []

            # Insert a new user
            user_collection.insert_one({"email": email, "name": name})
            flash("New user created successfully.", "success")
            return redirect(url_for("auth.dashboard"))
        else:
            flash("This gmail is already associated with an account, kindly login", "error")
            return render_template("login.html")


    except Exception as e:
        return f"<h1>Internal Server Error</h1><br><p>{e}</p>"


    


@auth.route("/login",methods=["GET","POST"])
def login():
    if request.method == "POST":
        data = request.form
        email = data.get("email")
        user = mongo.db.userdata.find_one({"email":email})
        if user:
            session["user"] = user["name"]
            session["mail"] = email
            userdata = mongo.db.usersearch.find({"email":email},{"_id":0,"email":0})
            if userdata:
                session["tracked_search"] = dumps(userdata)
            print(session["tracked_search"])
            flash("Logged in successfully!","message")
            return redirect("dashboard")
        else:
            flash("User doesn't exists!","error")
            return render_template("index.html")
            
    
    return render_template("login.html")

@auth.route("/dashboard",methods=["GET","POST"])
def dashboard():
    return render_template("dashboard.html",result=[])


@auth.route("logout",methods=["GET"])
def logout():
    session.clear()
    flash("Logged out successfully!","message")
    return render_template("index.html")


@auth.route("/search",methods=["GET","POST"])
def search():
    if request.method == "POST":
        search_query = request.form
        source = search_query.get("from")
        destination = search_query.get("to")
        date = search_query.get("departure-date")
        direct_flight = search_query.get("direct_flight")
        option = search_query.get("options")
        trackerList = search_query.get("trackerStorage")
        removeTrackerList = search_query.get("remove_trackers")
        email = session.get("mail")
        # senior_citizen = search_query.get("senior_citizen")
        # doctors_nurses = search_query.get("doctors_nurses")
        print(f"Query data:{source},{destination},{date},{option},{trackerList},{removeTrackerList}")
        if trackerList:
            flight_infos = json.loads(trackerList)
            # print(f"Flight info:{flight_infos}")
            # print("####################PREV DATA#######################")
            # print(session.get("prev_query"))
            # print("###################################################")
            for flight in flight_infos:
                try:
                    mongo.db.usersearch.insert_one({
                        "email":email,
                        "source":session["prev_query"]["source"],
                        "destination":session["prev_query"]["destination"],
                        "date":session["prev_query"]["date"],
                        "take_off":flight[2],
                        "landing_at":flight[3],
                        "flight_no":flight[0],
                        "price":flight[1]
                    })
                except Exception as e:
                    print(f"An error occured:{e}")   
        else:
            print("previous result was not list")
        if removeTrackerList:
            remove_tracker = json.loads(removeTrackerList)
            for flight in remove_tracker:
                print(flight["date"],email,flight["flight_no"])
                try:
                    deleted_result = mongo.db.usersearch.delete_one(
                        {"email":email,
                        "date":flight["date"],
                        "flight_no":flight["flight_no"]
                    })
                    print(f"Deleted {deleted_result.deleted_count} document(s)")

                except Exception as e:
                    print(f"An error occured:{e}")
            userdata = mongo.db.usersearch.find({"email":email},{"_id":0,"email":0})  
        optimised_date = date_optimiser(date)
        
        print(optimised_date)
        if direct_flight == "on":
            direct_flight = True
        else:
            direct_flight = False
        # driver = create_headless_driver()
        async def run_script():
            try:
                return await asyncio.wait_for(asyncio.to_thread(cheapest_flight,source,destination,optimised_date,option,direct=direct_flight),
                                          timeout=90)
            except TimeoutError:
                return "timeout"
        results = asyncio.run(run_script())
        print(f"The fetched data is: {results}")

        # print(results)
        session["prev_query"] = {"source":source, "destination":destination, "date":date}



        # update tracked searches in session so that changes get reflected on the frontend
        try:
            userdata = mongo.db.usersearch.find({"email":email},{"_id":0,"email":0})
            if userdata:
                session["tracked_search"] = dumps(userdata)
                print(session["tracked_search"])
            else:
                session["tracked_search"] = []
        except Exception as e:
            print(f"An error occured:{e}")



    return render_template("dashboard.html",
                           result=results,
                           source=source,
                           destination=destination,
                           date=date,
                           option=option,
                           direct_flight=direct_flight)


"""

@scheduler.task("cron",id="update_price",hour=19,minute=56)
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

        
    
        if results!="error":
            try:
                for data in results:
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
        else:
            print("bhai gadbad ho gai!")

"""



