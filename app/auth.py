from flask import Blueprint, request, flash, session, redirect, url_for, render_template
from . import mongo,mail
from .model import User
from authlib.integrations.flask_client import OAuth
from dotenv import load_dotenv
import os
import secrets
from app.static.scripts.script import cheapest_flight,date_optimiser,create_headless_driver,flight_booking
import json
from bson.json_util import dumps
import asyncio
from flask_mail import Message
import logging


logging.basicConfig(level=logging.INFO)




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
        logging.info("MongoDB connection is successful")
    except Exception as e:
        logging.error(f"MongoDB connection failed: {e}")
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
    session.clear()
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
        track_cheap = search_query.get("track_cheap")
    
        logging.info(f"Query data:{source},{destination},{date},{option},{direct_flight},{trackerList},{removeTrackerList}")
        if trackerList:
            flight_infos = json.loads(trackerList)
            
            for flight in flight_infos:
                try:
                    mongo.db.usersearch.insert_one({
                        "email":email,
                        "source":session["prev_query"]["source"],
                        "destination":session["prev_query"]["destination"],
                        "date":session["prev_query"]["date"],
                        "take_off":flight[3],
                        "landing_at":flight[4],
                        "take_off_date":flight[8],
                        "landing_date":flight[9],
                        "terminal_takeoff":flight[6],
                        "terminal_landing":flight[7],
                        "duration":flight[5],
                        "flight_no":flight[0],
                        "tag":flight[1],
                        "price":flight[2],
                        "option":session["prev_query"]["option"],
                        "direct":session["prev_query"]["direct"],
                        "url":flight[10],
                        "price_change":"neutral",
                        "trackCheap":False
                    })
                except Exception as e:
                    logging.error(f"An error occured:{e}")   
        else:
            logging.info("previous result was not list")
        if removeTrackerList:
            remove_tracker = json.loads(removeTrackerList)
            for flight in remove_tracker:
                logging.info(flight["date"],email,flight["flight_no"])
                try:
                    deleted_result = mongo.db.usersearch.delete_one(
                        {
                            "email":email,
                            "date":flight["date"],
                            "flight_no":flight["flight_no"]
                        })
                    logging.info(f"Deleted {deleted_result.deleted_count} document(s)")

                except Exception as e:
                    logging.error(f"An error occured:{e}")
            userdata = mongo.db.usersearch.find({"email":email},{"_id":0,"email":0})  
        optimised_date = date_optimiser(date)
        
        logging.info(optimised_date)
        if direct_flight == "on":
            direct_flight = True
        else:
            direct_flight = False
        driver = create_headless_driver()
        # function to run cheapest_flight function asynchronously
        async def run_script():
            try:
                return await asyncio.wait_for(asyncio.to_thread(cheapest_flight,driver,source,destination,optimised_date,option,direct=direct_flight),
                                        timeout=120)
            except TimeoutError:
                driver.quit()
                logging.error("timeout")
                return "timeout"
            
        # creating task for flight search for monitoring purpose
        # loop = asyncio.new_event_loop()
        # asyncio.set_event_loop(loop)
        # task = loop.create_task(run_script())
        # session['test'] = "test"
        # session.modified = True
        results = asyncio.run(run_script())

        # results format: [flight_no with flight name, non-stop tags, price, take-off time, land time, flight duration, takeoff terminal, landing terminal, takeoff date, landing date, booking_url]
        logging.info(f"result: {results}")
        if track_cheap:
            try:
                mongo.db.usersearch.insert_one({
                    "email":email,
                    "source":source,
                    "destination":destination,
                    "date":date,
                    "take_off":results[0][3],
                    "landing_at":results[0][4],
                    "take_off_date":results[0][8],
                    "landing_date":results[0][9],
                    "terminal_takeoff":results[0][6],
                    "terminal_landing":results[0][7],
                    "duration":results[0][5],
                    "flight_no":results[0][0],
                    "tag":results[0][1],
                    "price":results[0][2],
                    "option":option,
                    "direct":direct_flight,
                    "url":results[0][10],
                    "price_change":"neutral",
                    "trackCheap":True
                })
            except Exception as e:
                logging.error(f"Can't track cheapest:{e}") 

        # print(results)
        session["prev_query"] = {"source":source, "destination":destination, "date":date, "option":option, "direct":direct_flight}



        # update tracked searches in session so that changes get reflected on the frontend
        try:
            userdata = mongo.db.usersearch.find({"email":email},{"_id":0,"email":0,"direct":0,"option":0,"trackCheap":0})
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
                        direct_flight=direct_flight,
                        track_cheap=track_cheap)
    else:
        logging.info("get request sent!")
        return render_template("dashboard.html",result=[])



@auth.route("/logout",methods=["GET"])
def logout():
    if "flight_driver" in session:
            print(session["flight_driver"])
            driver = session["flight_driver"]
            try:
                driver.quit()
            except Exception as err:
                print(f"An error occured:{err}")
    else:
        print("no driver found")
    session.clear()
    return render_template("index.html")

@auth.route("/feedback", methods=["GET","POST"])
def feedback():
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        feedback = request.form.get("feedback")
        rating = request.form.get("rating")  # Get the star rating
        if not rating:
            rating = 0
        else: 
            rating = int(rating)

        # Process the feedback (e.g., save to database or send an email)
        print(f"Feedback received from {name} ({email}): {feedback} - Rating: {rating}")
        try:
            msg = Message(
                subject=f"Feedback: Ratings{'⭐' * rating } given by {name}:{email}",
                recipients=[os.getenv("GMAIL-ACCOUNT")],
                body=feedback
            )
            mail.send(msg)
            flash("Feedback sent successfully","message")
        except Exception as err:
            print(f"mail ni gaya {err}")
            flash("An error occured try again","error")
        
        
    
    return render_template("feedback.html")


@auth.route("redirect_to_booking_page",methods=["GET","POST"])
def redirect_to_booking_page():
    
    if request.method == "POST":
        form_data = request.form
        print(form_data)
        url = form_data.get("booking_url")
        flight_no = form_data.get("flight_no")
        return redirect(url)
        result = flight_booking(url,flight_no)
        if result == "success":
            return flash("Redirected successfully","message")
        else:
            return flash("An error occure","error")
    else:
        return redirect(url)
    





