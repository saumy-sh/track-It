from flask import Blueprint, request, jsonify, flash, session, redirect, url_for, render_template
from flask_mail import Message
from . import mail, mongo
from .model import User
from authlib.integrations.flask_client import OAuth
from dotenv import load_dotenv
import os
import secrets

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


@auth.route("/",methods=["GET"])
def main_page():
    test_connection()
    return render_template("index.html")

@auth.route("/signup",methods=["GET","POST"])
def singup():
    nonce = secrets.token_urlsafe(16)
    session["nonce"] = nonce
    # authorization_url, state = google.create_authorization_url(url_for("auth.callback",_external=True))
    # session["state"] = state
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
            # Insert a new user
            user_collection.insert_one({"email": email, "name": name})
            flash("New user created successfully.", "success")
            return redirect(url_for("auth.dashboard"))
        else:
            flash("This gmail is already associated with an account, kindly login", "error")
            return render_template("login.html")


    except Exception as e:
        return f"<h1>Internal Server Error</h1><br><p>{e}</p>"


    # flow.fetch_token(authorization_response=request.url)

    # credentials = flow.credentials
    # request_session = requests.Session()
    # token_request = google.auth.transport.requests.Request(session=request_session)
    
    # # Get user info
    # userinfo_response = requests.get(
    #     "https://www.googleapis.com/oauth2/v3/userinfo",
    #     headers={"Authorization": f"Bearer {credentials.token}"}
    # )
    # userinfo = userinfo_response.json()
    # email = userinfo["email"]

    """
    # sending mail 
    msg = Message("Login Successful", recipients=[email])
    msg.body = "You have successfully logged in to your account!"

    try:
        mail.send(msg)
        return f"Email sent to {email}"
    except Exception as e:
        return f"Failed to send email: {str(e)}"


    test_connection()
    from main import app
    # mongo.cx.close()
    # mongo.init_app(app)
    print(app.config["MONGO_URI"])
    print("###############################################")
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
    """



@auth.route("/login",methods=["GET","POST"])
def login():
    if request.method == "POST":
        data = request.form
        mail = data.get("email")
        print(mail)
        print("###############################################")
        test_connection()
        # reconnect to mongodb
        # mongo.cx.close()
        # mongo.init_app(app)
        user = mongo.db.userdata.find_one({"email":mail})
        if user:
            session["user"] = user["name"]
            flash("Logged in successfully!","message")
            return redirect("dashboard")
        else:
            flash("User doesn't exists!","error")
            return render_template("index.html")
            
    
    return render_template("login.html")

@auth.route("/dashboard",methods=["GET","POST"])
def dashboard():
    print(session["user"])
    return render_template("dashboard.html")


@auth.route("logout",methods=["GET"])
def logout():
    session.clear()
    flash("Logged out successfully!","message")
    return render_template("index.html")

@auth.route("/search",methods=["GET","POST"])
def search():
    return render_template("dashboard.html")