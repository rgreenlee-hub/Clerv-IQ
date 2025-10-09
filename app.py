import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'receptionist')))


import sqlite3
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file, Response
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_mail import Mail, Message
from dashboard import dashboard_bp
from auth import auth_bp  # ADDED

import traceback

# ---------------------
# Flask Setup
# ---------------------
template_dir = os.path.abspath('templates')
static_dir = os.path.abspath('static')
app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "supersecretkey-change-this-in-production")

# Ensure instance folder exists
os.makedirs(app.instance_path, exist_ok=True)

# Ensure instance folder exists
os.makedirs(app.instance_path, exist_ok=True)

# Enable detailed error output
app.config['PROPAGATE_EXCEPTIONS'] = True

@app.errorhandler(500)
def internal_error(error):
    print("=" * 50)
    print("500 ERROR DETAILS:")
    print(traceback.format_exc())
    print("=" * 50)
    return f"<pre>{traceback.format_exc()}</pre>", 500

# ---------------------
# Register Blueprints
# ---------------------
# TEMPORARILY DISABLED - will fix after site is live
# from receptionist_bridge import bridge_bp
# app.register_blueprint(bridge_bp, url_prefix="/api/receptionist")
app.register_blueprint(dashboard_bp)
app.register_blueprint(auth_bp)  # ADDED

# ---------------------
# Database
# ---------------------
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(app.instance_path, "users.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

# ---------------------
# Auth
# ---------------------
bcrypt = Bcrypt(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# ---------------------
# Mail
# ---------------------
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME', 'your_email@gmail.com')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD', 'your_app_password')
mail = Mail(app)

# Initialize mail for auth module
from auth import init_mail
init_mail(mail)

# ---------------------
# Optional Integrations
# ---------------------
try:
    import stripe
    stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "sk_test_yourSecretKey")
    STRIPE_PUBLIC_KEY = os.getenv("STRIPE_PUBLIC_KEY", "pk_test_yourPublicKey")
    STRIPE_PRICE_ID = os.getenv("STRIPE_PRICE_ID", "price_yourStripePriceID")
    STRIPE_AVAILABLE = True
except ImportError:
    print("Warning: Stripe not available")
    STRIPE_AVAILABLE = False
    STRIPE_PUBLIC_KEY = ""
    STRIPE_PRICE_ID = ""

try:
    from twilio.twiml.voice_response import VoiceResponse
    from twilio.twiml.messaging_response import MessagingResponse
    TWILIO_AVAILABLE = True
except ImportError:
    print("Warning: Twilio not available")
    TWILIO_AVAILABLE = False

try:
    from receptionist.brain import ReceptionistBrain
    brain = ReceptionistBrain()
    RECEPTIONIST_AVAILABLE = True
except ImportError as e:
    print(f"Warning: ReceptionistBrain not available: {e}")
    brain = None
    RECEPTIONIST_AVAILABLE = False

# Analytics and Config are optional for now
try:
    from Config import CLIENTS
    from Analytics import Analytics
    analytics = Analytics()
except ImportError as e:
    print(f"Warning: Analytics module not available: {e}")
    CLIENTS = []
    analytics = None
# ---------------------
# User Model
# ---------------------
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    onboarding_complete = db.Column(db.Boolean, default=False)
    client_id = db.Column(db.Integer, nullable=True)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ---------------------
# Helper Functions
# ---------------------
def get_receptionist_db():
    if RECEPTIONIST_AVAILABLE:
        db_path = os.path.join(os.path.dirname(__file__), "Receptionist", "receptionist.db")
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn
    return None

# ---------------------
# Routes (Public)
# ---------------------
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/features")
def features():
    return render_template("features.html")

@app.route("/pricing")
def pricing():
    return render_template("pricing.html")

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        name = request.form.get("name", "")
        email = request.form.get("email", "")
        company = request.form.get("company", "")
        revenue = request.form.get("revenue", "")
        industry = request.form.get("industry", "")
        message = request.form.get("message", "")

        try:
            msg = Message(f"New Contact Form Submission from {name}",
                          sender=app.config['MAIL_USERNAME'],
                          recipients=[app.config['MAIL_USERNAME']])
            msg.body = (
                f"Name: {name}\nEmail: {email}\nCompany: {company}\n"
                f"Revenue: {revenue}\nIndustry: {industry}\n\nMessage:\n{message}"
            )
            mail.send(msg)
            flash("Your message has been sent successfully!", "success")
        except Exception as e:
            print(f"Mail error: {e}")
            flash("Message received! (Email not configured)", "info")
        
        return redirect(url_for("contact"))
    
    return render_template("contact.html")

# ---------------------
# Auth
# ---------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "")
        password = request.form.get("password", "")
        
        user = User.query.filter_by(email=email).first()
        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user)
            # Send user to dashboard blueprint
            return redirect(url_for("dashboard.dashboard")) if user.onboarding_complete else redirect(url_for("onboarding"))
        else:
            return render_template("login.html", error="Invalid credentials")
    
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form.get("email", "")
        password = request.form.get("password", "")
        
        if User.query.filter_by(email=email).first():
            return render_template("register.html", error="Email already exists")
        
        hashed_password = bcrypt.generate_password_hash(password).decode("utf-8")
        
        client_id = 1
        if RECEPTIONIST_AVAILABLE:
            conn = get_receptionist_db()
            if conn:
                cur = conn.cursor()
                cur.execute("INSERT INTO clients (company_name, email, password_hash) VALUES (?, ?, ?)",
                            ("Company", email, hashed_password))
                client_id = cur.lastrowid
                conn.commit()
                conn.close()
        
        new_user = User(email=email, password=hashed_password, client_id=client_id)
        db.session.add(new_user)
        db.session.commit()
        
        flash("Registration successful! Please log in.", "success")
        return redirect(url_for("login"))
    
    return render_template("register.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

@app.route("/onboarding", methods=["GET", "POST"])
@login_required
def onboarding():
    if current_user.onboarding_complete:
        return redirect(url_for("dashboard.dashboard"))
    
    if request.method == "POST":
        current_user.onboarding_complete = True
        db.session.commit()
        return redirect(url_for("dashboard.dashboard"))
    
    return render_template("onboarding.html")

# ---------------------
# Stripe Billing
# ---------------------
@app.route("/create-checkout-session", methods=["POST"])
@login_required
def create_checkout_session():
    if not STRIPE_AVAILABLE:
        return jsonify(error="Stripe not configured"), 400
    
    try:
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{"price": STRIPE_PRICE_ID, "quantity": 1}],
            mode="subscription",
            success_url=url_for("finish_onboarding", _external=True),
            cancel_url=url_for("dashboard.dashboard", _external=True),
            customer_email=current_user.email,
        )
        return jsonify({"sessionId": checkout_session["id"]})
    except Exception as e:
        return jsonify(error=str(e)), 403

# ADDED: Stripe payment endpoint for register.html
@app.route("/charge", methods=["POST"])
def charge():
    """Handle Stripe payment from registration wizard"""
    if not STRIPE_AVAILABLE:
        return jsonify({"success": False, "error": "Stripe not configured"}), 400
    
    try:
        data = request.json
        payment_method_id = data.get("payment_method")
        billing = data.get("billing", {})
        
        # Create a payment intent (adjust amount as needed)
        payment_intent = stripe.PaymentIntent.create(
            amount=200000,  # $2000.00 in cents - adjust based on your pricing
            currency="usd",
            payment_method=payment_method_id,
            confirm=True,
            description="ClervIQ Subscription",
            receipt_email=billing.get("email")
        )
        
        return jsonify({"success": True, "payment_intent_id": payment_intent.id})
        
    except stripe.error.CardError as e:
        return jsonify({"success": False, "error": e.user_message}), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/finish_onboarding")
@login_required
def finish_onboarding():
    current_user.onboarding_complete = True
    db.session.commit()
    return redirect(url_for("dashboard.dashboard"))

# ---------------------
# Webhooks (Twilio)
# ---------------------
if TWILIO_AVAILABLE:
    @app.route("/voice", methods=["POST"])
    def voice():
        transcript = request.form.get("SpeechResult", "")
        ai_reply = brain.analyze_message(transcript) if RECEPTIONIST_AVAILABLE and brain else "Hello, thank you for calling!"
        resp = VoiceResponse()
        resp.say(ai_reply)
        return str(resp)

    @app.route("/sms", methods=["POST"])
    def sms():
        body = request.form.get("Body", "")
        ai_reply = brain.analyze_message(body) if RECEPTIONIST_AVAILABLE and brain else "Thank you for your message!"
        resp = MessagingResponse()
        resp.message(ai_reply)
        return str(resp)

# ---------------------
# Voice Reply Route (Twilio will hit this during calls)
# ---------------------
@app.route("/voice_reply", methods=["POST"])
def voice_reply():
    """Handle incoming calls with AI-generated voice responses"""
    try:
        from receptionist.tts_engine import generate_speech
        
        # Get user input from Twilio (speech-to-text result)
        user_input = request.form.get("SpeechResult", "Hello from ClervIQ.")
        
        # Generate AI voice response
        audio_file = generate_speech(user_input, filename="response.wav")
        
        # Create Twilio response
        response = VoiceResponse()
        response.play(url=request.url_root + "static/response.wav")
        
        return Response(str(response), mimetype="text/xml")
    
    except Exception as e:
        print(f"Voice reply error: {e}")
        # Fallback response
        response = VoiceResponse()
        response.say("Thank you for calling ClervIQ.")
        return Response(str(response), mimetype="text/xml")

# ---------------------
# Legal Pages
# ---------------------
@app.route("/privacy")
def privacy():
    return render_template("privacy.html")

@app.route("/terms")
def terms():
    return render_template("terms.html")


# ---------------------
# API Endpoints - Connect Calls Page
# ---------------------
# TEMPORARILY DISABLED
# from receptionist.elite_ai_receptionist import EliteAIReceptionist

# @app.route('/api/calls', methods=['GET'])
# def get_calls_data():
#     try:
#         from receptionist.elite_ai_receptionist import EliteAIReceptionist
#         receptionist = EliteAIReceptionist()  # Now works without params
#         call_stats = receptionist.get_call_stats()
#         return jsonify(call_stats)
#     except Exception as e:
#         return jsonify({"error": str(e)}), 500

# @app.route('/sms')
# def sms_dashboard():
#     from receptionist.elite_ai_receptionist import get_sms_data
#     sms_data = get_sms_data()
#     return render_template('sms.html', data=sms_data)

# @app.route("/analytics")
# def analytics_page():
#     from elite_ai_receptionist import EliteAIReceptionist
#     from Config import CLIENTS

#     # use your test or first client
#     receptionist = EliteAIReceptionist(CLIENTS[0])
#     analytics_data = receptionist.get_analytics()

#     return render_template("analytics.html", analytics_data=analytics_data)

# ---------------------
# Startup
# ---------------------
if __name__ == "__main__":
    with app.app_context():
        db.create_all()

        # Auto-create default admin user
        if not User.query.filter_by(email="admin@example.com").first():
            default_user = User(
                email="admin@example.com",
                password=bcrypt.generate_password_hash("password123").decode("utf-8"),
                onboarding_complete=True,
                client_id=1
            )
            db.session.add(default_user)
            db.session.commit()
            print("Default admin user created: admin@example.com / password123")
        else:
            print("Admin user already exists")

    print("Starting Flask app...")
    app.run(debug=True, port=5000)