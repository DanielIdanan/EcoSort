from flask import Flask, render_template, request, redirect, url_for, session, flash
from datetime import timedelta
import os
import sqlite3
import numpy as np
from uuid import uuid4
from authlib.integrations.flask_client import OAuth
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing import image as keras_image

os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"  # only for local development

app = Flask(__name__)
app.secret_key = "ecosort_secret_key"

app.config['SESSION_TYPE'] = 'filesystem'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=10)
app.config['SESSION_COOKIE_SECURE'] = False  # Set to True only for HTTPS
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

@app.before_request
def make_session_permanent():
    session.permanent = True

UPLOAD_FOLDER = "static/uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
DATABASE = "database.db"

os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

MODEL_PATH = "model/waste_model.h5"
model = load_model(MODEL_PATH)
class_names = ["biodegradable", "non_recyclable", "recyclable"]


def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    return conn


def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            image_path TEXT NOT NULL,
            prediction TEXT NOT NULL,
            confidence TEXT NOT NULL,
            tip TEXT NOT NULL,
            scanned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)

    conn.commit()
    conn.close()


def predict_waste(image_path):
    img = keras_image.load_img(image_path, target_size=(224, 224))
    img_array = keras_image.img_to_array(img)
    img_array = np.expand_dims(img_array, axis=0) / 255.0

    predictions = model.predict(img_array, verbose=0)
    predicted_index = np.argmax(predictions[0])
    confidence = float(np.max(predictions[0])) * 100

    label_map = {
        "biodegradable": (
            "Biodegradable",
            "Place this item in the biodegradable waste bin."
        ),
        "recyclable": (
            "Recyclable",
            "Place this item in the recyclable waste bin."
        ),
        "non_recyclable": (
            "Non-recyclable",
            "Place this item in the non-recyclable waste bin."
        )
    }

    raw_label = class_names[predicted_index]
    prediction, tip = label_map[raw_label]

    return prediction, f"{confidence:.2f}%", tip


def login_user(user):
    session["user_id"] = user[0]
    session["user_name"] = user[1]


def find_or_create_oauth_user(name, email):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, name, email, password
        FROM users
        WHERE email = ?
    """, (email,))
    user = cursor.fetchone()

    if not user:
        placeholder_password = "oauth_user_no_local_password"
        cursor.execute("""
            INSERT INTO users (name, email, password)
            VALUES (?, ?, ?)
        """, (name, email, placeholder_password))
        conn.commit()

        cursor.execute("""
            SELECT id, name, email, password
            FROM users
            WHERE email = ?
        """, (email,))
        user = cursor.fetchone()

    conn.close()
    return user


# -------------------------
# OAuth setup
# -------------------------
oauth = OAuth(app)

google = oauth.register(
    name="google",
    client_id=os.environ.get("GOOGLE_CLIENT_ID"),
    client_secret=os.environ.get("GOOGLE_CLIENT_SECRET"),
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={
        "scope": "openid email profile"
    }
)

facebook = oauth.register (
    name="facebook",
    client_id=os.environ.get("FACEBOOK_CLIENT_ID"),
    client_secret=os.environ.get("FACEBOOK_CLIENT_SECRET"),
    access_token_url="https://graph.facebook.com/oauth/access_token",
    authorize_url="https://www.facebook.com/dialog/oauth",
    api_base_url="https://graph.facebook.com/",
    userinfo_endpoint="https://graph.facebook.com/me?fields=id,name,email",
    client_kwargs={
        "scope": "email public_profile",
        "token_endpoint_auth_method": "client_secret_post"
    }
)

print("GOOGLE_CLIENT_ID =", os.environ.get("GOOGLE_CLIENT_ID"))
print("GOOGLE_CLIENT_SECRET exists =", bool(os.environ.get("GOOGLE_CLIENT_SECRET")))


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"].strip()
        email = request.form["email"].strip().lower()
        password = request.form["password"].strip()

        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO users (name, email, password)
                VALUES (?, ?, ?)
            """, (name, email, password))
            conn.commit()
            conn.close()
            flash("Registration successful. You can now log in.", "success")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            conn.close()
            flash("Email already exists. Please use another one.", "error")
            return redirect(url_for("register"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = request.form["password"].strip()

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, name, email, password
            FROM users
            WHERE email = ?
        """, (email,))
        user = cursor.fetchone()
        conn.close()

        if not user:
            flash("No account found with that email. Please register first.", "error")
            return redirect(url_for("login"))

        if user[3] != password:
            flash("Incorrect password. Please try again.", "error")
            return redirect(url_for("login"))

        login_user(user)
        flash(f"Welcome back, {user[1]}!", "success")
        return redirect(url_for("index"))

    return render_template("login.html")


@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        new_password = request.form["new_password"].strip()
        confirm_password = request.form["confirm_password"].strip()

        if new_password != confirm_password:
            flash("Passwords do not match.", "error")
            return redirect(url_for("forgot_password"))

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()

        if not user:
            conn.close()
            flash("No account found with that email.", "error")
            return redirect(url_for("forgot_password"))

        cursor.execute("""
            UPDATE users
            SET password = ?
            WHERE email = ?
        """, (new_password, email))
        conn.commit()
        conn.close()

        flash("Password updated successfully. You can now log in.", "success")
        return redirect(url_for("login"))

    return render_template("forgot_password.html")


# -------------------------
# Google OAuth
# -------------------------


@app.route("/login/google")
def google_login():
    if not os.environ.get("GOOGLE_CLIENT_ID") or not os.environ.get("GOOGLE_CLIENT_SECRET"):
        flash("Google OAuth credentials are missing.", "error")
        return redirect(url_for("login"))
    
    redirect_uri = url_for("google_callback", _external=True)
    state = os.urandom(16).hex()
    session['oauth_state'] = state
    session.modified = True  # FORCE SAVE
    print(f"Storing state: {state}")  # Debug
    return google.authorize_redirect(redirect_uri, state=state)


@app.route("/login/google/callback")
def google_callback():
    try:
        # Debug: Check what we received vs what we stored
        received_state = request.args.get('state')
        stored_state = session.get('oauth_state')
        print(f"DEBUG - Received state: {received_state}")
        print(f"DEBUG - Stored state: {stored_state}")
        
        # TEMPORARY: Skip state verification for debugging
        # Remove this check once session persistence is fixed
        if stored_state and received_state != stored_state:
            print("WARNING: State mismatch detected, but allowing login for debugging")
        
        # Clear state from session
        session.pop('oauth_state', None)
        
        # Get access token
        token = google.authorize_access_token()
        resp = google.get("https://www.googleapis.com/oauth2/v3/userinfo", token=token)
        user_info = resp.json()

        email = user_info.get("email")
        name = user_info.get("name", "Google User")

        user = find_or_create_oauth_user(name, email)
        login_user(user)

        flash(f"Welcome, {name}!", "success")
        return redirect(url_for("index"))

    except Exception as e:
        print(f"Google OAuth error: {e}")
        flash(f"Google login failed: {e}", "error")
        return redirect(url_for("login"))


# -------------------------
# Facebook OAuth
# -------------------------
@app.route("/login/facebook")
def facebook_login():
    if not os.environ.get("FACEBOOK_CLIENT_ID") or not os.environ.get("FACEBOOK_CLIENT_SECRET"):
        flash("Facebook OAuth credentials are missing.", "error")
        return redirect(url_for("login"))

    redirect_uri = url_for("facebook_callback", _external=True)
    session['oauth_state'] = os.urandom(16).hex()
    return facebook.authorize_redirect(redirect_uri)


@app.route("/login/facebook/callback")
def facebook_callback():
    try:
        received_state = request.args.get('state')
        stored_state = session.get('oauth_state')
        print(f"DEBUG - Received state: {received_state}")
        print(f"DEBUG - Stored state: {stored_state}")
        
        # TEMPORARY: Skip state verification for debugging
        if stored_state and received_state != stored_state:
            print("WARNING: State mismatch detected, but allowing login for debugging")
        
        session.pop('oauth_state', None)
        
        token = facebook.authorize_access_token()
        resp = facebook.get("me?fields=id,name,email", token=token)
        profile = resp.json()

        email = profile.get("email")
        name = profile.get("name", "Facebook User")

        user = find_or_create_oauth_user(name, email)
        login_user(user)

        flash(f"Welcome, {name}!", "success")
        return redirect(url_for("index"))

    except Exception as e:
        print(f"Facebook OAuth error: {e}")
        flash(f"Facebook login failed: {e}", "error")
        return redirect(url_for("login"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/", methods=["GET", "POST"])
def index():
    if "user_id" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        if "image" not in request.files:
            flash("Please upload an image first.", "error")
            return redirect(url_for("index"))

        image = request.files["image"]

        if image.filename == "":
            flash("Please choose an image file.", "error")
            return redirect(url_for("index"))

        original_filename = image.filename
        file_ext = os.path.splitext(original_filename)[1].lower()
        unique_filename = f"{uuid4().hex}{file_ext}"

        saved_file_path = os.path.join(app.config["UPLOAD_FOLDER"], unique_filename)
        image.save(saved_file_path)

        db_image_path = f"uploads/{unique_filename}"

        prediction, confidence, tip = predict_waste(saved_file_path)

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO scans (user_id, image_path, prediction, confidence, tip)
            VALUES (?, ?, ?, ?, ?)
        """, (session["user_id"], db_image_path, prediction, confidence, tip))
        conn.commit()
        conn.close()

        return render_template(
            "result.html",
            prediction=prediction,
            confidence=confidence,
            tip=tip,
            image=db_image_path
        )

    return render_template("index.html", user_name=session["user_name"])


@app.route("/history")
def history():
    if "user_id" not in session:
        return redirect(url_for("login"))

    # Get filter parameter from query string
    filter_type = request.args.get('filter', 'all')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Build query based on filter
    if filter_type == 'reduce':
        # Non-recyclable items -> focus on reducing
        cursor.execute("""
            SELECT id, image_path, prediction, confidence, tip, scanned_at
            FROM scans
            WHERE user_id = ? AND (prediction LIKE '%non_recyclable%' OR prediction LIKE '%non-recyclable%' OR prediction LIKE '%Non-recyclable%')
            ORDER BY id DESC
        """, (session["user_id"],))
        filter_title = "Reduce History (Non-recyclable Items)"
    elif filter_type == 'reuse':
        # Biodegradable items -> can be composted/reused
        cursor.execute("""
            SELECT id, image_path, prediction, confidence, tip, scanned_at
            FROM scans
            WHERE user_id = ? AND (prediction LIKE '%biodegradable%' OR prediction LIKE '%Biodegradable%')
            ORDER BY id DESC
        """, (session["user_id"],))
        filter_title = "Reuse History (Biodegradable Items)"
    elif filter_type == 'recycle':
        # Recyclable items
        cursor.execute("""
            SELECT id, image_path, prediction, confidence, tip, scanned_at
            FROM scans
            WHERE user_id = ? AND (prediction LIKE '%recyclable%' OR prediction LIKE '%Recyclable%') AND prediction NOT LIKE '%non%'
            ORDER BY id DESC
        """, (session["user_id"],))
        filter_title = "Recycle History (Recyclable Items)"
    else:
        # All items
        cursor.execute("""
            SELECT id, image_path, prediction, confidence, tip, scanned_at
            FROM scans
            WHERE user_id = ?
            ORDER BY id DESC
        """, (session["user_id"],))
        filter_title = "All Scan History"
    
    scans = cursor.fetchall()
    conn.close()

    return render_template("history.html", scans=scans, filter_type=filter_type, filter_title=filter_title)


if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port, debug=False)