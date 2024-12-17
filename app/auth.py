from . import mail
from flask import Blueprint,request,jsonify,flash,session,redirect,url_for,render_template
from google_auth_oauthlib.flow import Flow
import requests
from flask_mail import Message
from .model import User
import os
from dotenv import load_dotenv
from . import mongo

load_dotenv()

user_schema = User()
auth = Blueprint("auth",__name__)

# setting up OAuth credentials
SCOPES = ["https://www.googleapis.com/auth/userinfo.profile","https://www.googleapis.com/auth/userinfo.email","openid"]


flow = Flow.from_client_config(
    {
        "web": {
            "client_id":os.getenv("CLIENT_ID"),
            "client_secret": os.getenv("CLIENT_SECRET"),
            "auth_uri": os.getenv("AUTH_URI"),
            "token_uri": os.getenv("TOKEN_URI"),
            "auth_provider_x509_cert_url": os.getenv("AUTH_PROVIDER_CERT_URL"),
            "javascript_origins": os.getenv("ORIGINS"),
            "redirect_uris": os.getenv("REDIRECT_URI"),
            "project_id": os.getenv("PROJECT_ID"),
        }
    }
    , scopes=SCOPES,redirect_uri="http://localhost:5000/callback"
)


def test_connection():
    try:
        # Test connection
        print(mongo.db)  # This will raise an exception if the connection fails
        print("MongoDB connection is successful")
    except Exception as e:
        print(f"MongoDB connection failed: {e}")
    return None


@auth.route("/",methods=["GET"])
def main_page():
    test_connection()
    return render_template("index.html")

@auth.route("/signup",methods=["GET"])
def singup():

    authorization_url, state = flow.authorization_url()
    session["state"] = state
    return redirect(authorization_url)
    

@auth.route("/callback",methods=["GET","POST"])
def callback():
    
    flow.fetch_token(authorization_response=request.url)

    credentials = flow.credentials
    # request_session = requests.Session()
    # token_request = google.auth.transport.requests.Request(session=request_session)
    
    # Get user info
    userinfo_response = requests.get(
        "https://www.googleapis.com/oauth2/v3/userinfo",
        headers={"Authorization": f"Bearer {credentials.token}"}
    )
    userinfo = userinfo_response.json()
    email = userinfo["email"]

    """
    # sending mail 
    msg = Message("Login Successful", recipients=[email])
    msg.body = "You have successfully logged in to your account!"

    try:
        mail.send(msg)
        return f"Email sent to {email}"
    except Exception as e:
        return f"Failed to send email: {str(e)}"
    """
    user = mongo.db.userdata.find_one({"email":email})
    print("################################################################")
    if user:
        flash("This gmail is already associated with an account, kindly login","error")
        return render_template("login.html")
    else:
        user = user_schema.load({"email":email})
        mongo.db.userdata.insert_one(user)
        session["mail"] = email
        flash("Logged in sucessfully!","message")
        return redirect(url_for("auth.dashboard"))   



@auth.route("/login",methods=["GET","POST"])
def login():
    if request.method == "POST":
        data = request.form
        mail = data.get("email")
        user = mongo.db.userdata.find_one({"email":mail})
        if user:
            session["mail"] = mail
            flash("Logged in successfully!","message")
            return redirect("dashboard")
        else:
            flash("User doesn't exists!","error")
            
    
    return render_template("login.html")

@auth.route("/dashboard",methods=["GET","POST"])
def dashboard():
    return render_template("dashboard.html")


@auth.route("logout",methods=["GET"])
def logout():
    session.clear()
    return render_template("index.html")

@auth.route("/search",methods=["GET","POST"])
def search():
    return render_template("dashboard.html")