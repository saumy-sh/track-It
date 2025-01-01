from flask import Blueprint, request, flash, session, redirect, url_for, render_template
from . import mongo
from .model import User
from authlib.integrations.flask_client import OAuth
from dotenv import load_dotenv
import os
import secrets
from app.static.scripts.script import cheapest_flight,date_optimiser
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
    if session["flight_task"]:
        task = session["flight_task"]
        if not task.done():
            task.cancel()
            print("Task cancelled")
        else:
            print("task done")
    else:
        print("not found!!")
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
        track_cheap = search_query.get("track_cheap")
    
        print(f"Query data:{source},{destination},{date},{option},{direct_flight},{trackerList},{removeTrackerList}")
        if trackerList:
            flight_infos = json.loads(trackerList)
            
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
                        "price":flight[1],
                        "option":session["prev_query"]["option"],
                        "direct":session["prev_query"]["direct"],
                        "trackCheap":False
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

        # function to run cheapest_flight function asynchronously
        async def run_script():
            try:
                return await asyncio.wait_for(asyncio.to_thread(cheapest_flight,source,destination,optimised_date,option,direct=direct_flight),
                                          timeout=90)
            except TimeoutError:
                return "timeout"
            
        # creating task for flight search for monitoring purpose
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        task = loop.create_task(run_script())
        session['flight_task'] = task
        print("flight task stored:",session["flight_task"])
        results = loop.run_until_complete(run_script())
        # print(f"The fetched data is: {results}")

        if track_cheap:
            try:
                mongo.db.usersearch.insert_one({
                    "email":email,
                    "source":source,
                    "destination":destination,
                    "date":date,
                    "take_off":results[0][2],
                    "landing_at":results[0][3],
                    "flight_no":results[0][0],
                    "price":results[0][1],
                    "option":option,
                    "direct":direct_flight,
                    "trackCheap":True
                })
            except Exception as e:
                print(f"Can't track cheapest:{e}") 

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
                           direct_flight=direct_flight)




