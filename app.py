import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'receptionist')))


import sqlite3
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file, Response, session
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_mail import Mail, Message
from dashboard import dashboard_bp
from auth import auth_bp
from flask import send_from_directory

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

# Enable detailed error output
app.config['PROPAGATE_EXCEPTIONS'] = True

@app.errorhandler(500)
def internal_error(error):
    print("=" * 50)
    print("500 ERROR DETAILS:")
    print(traceback.format_exc())
    print("=" * 50)
    return f"<pre>{traceback.format_exc()}</pre>", 500

app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

# ---------------------
# Register Blueprints (MOVED HERE - AFTER APP CREATION)
# ---------------------
from chatbot_routes import chatbot_bp
app.register_blueprint(chatbot_bp)

# ENABLE EVERYTHING! 🔥
app.register_blueprint(dashboard_bp)  # ✅ ENABLED
app.register_blueprint(auth_bp)  # ✅ ENABLED

# Note: receptionist_bridge commented out if not ready yet
# from receptionist_bridge import bridge_bp
# app.register_blueprint(bridge_bp, url_prefix="/api/receptionist")

# PASSWORD RESET
from password_reset import password_reset_bp
app.register_blueprint(password_reset_bp)

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
    # Debug: Print what Flask sees
    import os
    print("=" * 50)
    print("CURRENT DIRECTORY:", os.getcwd())
    print("TEMPLATE FOLDER:", app.template_folder)
    print("FILES IN TEMPLATE FOLDER:", os.listdir(app.template_folder) if os.path.exists(app.template_folder) else "FOLDER NOT FOUND")
    print("=" * 50)
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
            return render_template("register.html", error="Email already exists", stripe_public_key=STRIPE_PUBLIC_KEY)
        
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
    
    return render_template("register.html", stripe_public_key=STRIPE_PUBLIC_KEY)

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
# Phone Number Hosting (Twilio) - UPDATED FIXED
# ---------------------
@app.route("/onboarding/host-number", methods=["POST"])
def host_number():
    """Send verification code to phone number"""
    try:
        from twilio.rest import Client

        phone_number = request.json.get("phone_number")

        if not phone_number:
            return jsonify({"success": False, "error": "Phone number required"}), 400

        # Check if Twilio is configured
        account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        verify_sid = os.getenv("TWILIO_VERIFY_SID")

        # Fallback if Twilio not configured
        if not account_sid or not auth_token or not TWILIO_AVAILABLE or not verify_sid:
            session['pending_phone'] = phone_number
            return jsonify({
                "success": True,
                "status": "saved",
                "message": "Phone number saved. We'll verify and set it up manually.",
                "skip_otp": True
            })

        # ✅ Twilio Verify setup
        client = Client(account_sid, auth_token)

        # ✅ Format phone number correctly (E.164)
        if not phone_number.startswith('+'):
            phone_number = '+1' + phone_number  # assumes US numbers

        # ✅ Send verification code using your Verify Service
        verification = client.verify.v2.services(verify_sid).verifications.create(
            to=phone_number,
            channel='sms'
        )

        # Store SID and pending phone in session
        session['verification_sid'] = verify_sid
        session['pending_phone'] = phone_number

        return jsonify({
            "success": True,
            "status": "otp_sent",
            "message": f"Verification code sent to {phone_number}"
        })

    except Exception as e:
        print(f"Phone verification error: {e}")
        import traceback
        traceback.print_exc()

        # Fallback: just save number if Twilio fails
        session['pending_phone'] = request.json.get("phone_number")
        return jsonify({
            "success": True,
            "status": "saved",
            "message": "Phone number saved. We'll verify and set it up within 24-48 hours.",
            "skip_otp": True
        })


@app.route("/onboarding/verify-otp", methods=["POST"])
def verify_otp():
    """Verify OTP code"""
    try:
        from twilio.rest import Client

        otp_code = request.json.get("otp_code")
        verification_sid = session.get('verification_sid')
        phone_number = session.get('pending_phone')

        if not verification_sid or not phone_number:
            return jsonify({"success": False, "error": "No pending verification"}), 400

        # Check Twilio config
        account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        auth_token = os.getenv("TWILIO_AUTH_TOKEN")

        if not account_sid or not auth_token:
            return jsonify({"success": False, "error": "Twilio not configured"}), 400

        client = Client(account_sid, auth_token)

        # ✅ Verify the OTP code
        verification_check = client.verify.v2.services(verification_sid).verification_checks.create(
            to=phone_number,
            code=otp_code
        )

        if verification_check.status == 'approved':
            # Success! Store verified phone
            session['verified_phone'] = phone_number
            session.pop('verification_sid', None)
            session.pop('pending_phone', None)

            # Notify admin by email
            try:
                msg = Message(
                    f"New Phone Number Verified - Needs Hosting",
                    sender=app.config['MAIL_USERNAME'],
                    recipients=[app.config['MAIL_USERNAME']]
                )
                msg.body = f"""
New customer verified their phone number:

Phone: {phone_number}

ACTION REQUIRED:
1. Go to Twilio Console: https://console.twilio.com/us1/develop/phone-numbers/port-host/hosted-numbers
2. Click "Host a Number"
3. Enter: {phone_number}
4. Submit hosting request
5. Takes 1-2 days to complete

Customer is waiting!
                """
                mail.send(msg)
            except Exception as e:
                print(f"Notification email failed: {e}")

            return jsonify({
                "success": True,
                "message": "✅ Phone verified! We'll complete hosting setup within 24-48 hours."
            })
        else:
            return jsonify({
                "success": False,
                "error": "Invalid code. Please try again."
            }), 400

    except Exception as e:
        print(f"OTP verification error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": "Verification failed. Please try again or skip this step."
        }), 400


# ---------------------
# Stripe Billing - UPDATED FOR BETA
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

# UPDATED: Free beta testing mode
@app.route("/charge", methods=["POST"])
def charge():
    """Handle Stripe payment from registration wizard - BETA TESTING MODE"""
    try:
        data = request.json
        billing = data.get("billing", {})
        
        print(f"🎉 BETA TESTER SIGNUP: {billing.get('email')}")
        
        # Return success without charging (for beta testing)
        return jsonify({
            "success": True,
            "payment_intent_id": "beta_test_free_access",
            "message": "Beta testing - no charge applied"
        })
        
    except Exception as e:
        print(f"Charge error: {e}")
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
# Emergency DB Init (TEMPORARY - for Render)
# ---------------------
@app.route("/init-db-now-delete-after")
def init_db_emergency():
    """Force database creation - DELETE THIS ROUTE AFTER USE!"""
    try:
        db.create_all()
        
        # Create admin if doesn't exist
        if not User.query.filter_by(email="admin@example.com").first():
            admin = User(
                email="admin@example.com",
                password=bcrypt.generate_password_hash("password123").decode("utf-8"),
                onboarding_complete=True,
                client_id=1
            )
            db.session.add(admin)
            db.session.commit()
        
        # Create demo if doesn't exist
        if not User.query.filter_by(email="demo@clerviq.com").first():
            demo = User(
                email="demo@clerviq.com",
                password=bcrypt.generate_password_hash("Demo2024!").decode("utf-8"),
                onboarding_complete=True,
                client_id=1
            )
            db.session.add(demo)
            db.session.commit()
        
        return """
        <html>
        <head>
            <style>
                body {
                    font-family: 'Courier New', monospace;
                    background: linear-gradient(135deg, #0a0e27 0%, #1a1f3a 100%);
                    color: #e8f0ff;
                    padding: 50px;
                }
                h1 { color: #00d4ff; }
                .success { background: rgba(0, 255, 170, 0.1); padding: 20px; border-radius: 10px; border: 1px solid #00ffaa; }
                .warning { background: rgba(255, 77, 77, 0.1); padding: 20px; border-radius: 10px; border: 1px solid #ff4d4d; margin-top: 20px; }
                a { color: #00d4ff; text-decoration: none; font-weight: bold; }
                a:hover { text-decoration: underline; }
            </style>
        </head>
        <body>
            <div class="success">
                <h1>✅ Database Initialized!</h1>
                <p><strong>Users created:</strong></p>
                <ul>
                    <li>admin@example.com / password123</li>
                    <li>demo@clerviq.com / Demo2024!</li>
                </ul>
            </div>
            <div class="warning">
                <p><strong>⚠️ NOW DELETE THIS ROUTE FROM CODE!</strong></p>
                <p>Remove the /init-db-now-delete-after route from app.py and redeploy.</p>
            </div>
            <p style="margin-top: 30px;"><a href='/login'>→ Go to Login</a></p>
        </body>
        </html>
        """
    except Exception as e:
        return f"<pre>Error: {str(e)}</pre>", 500


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
# Static file route for Render
# ---------------------
@app.route('/static/<path:filename>')
def serve_static(filename):
    static_dir = os.path.join(app.root_path, 'static')
    return send_from_directory(static_dir, filename)


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

        # ✅ DEMO ACCOUNT
        if not User.query.filter_by(email="demo@clerviq.com").first():
            demo_user = User(
                email="demo@clerviq.com",
                password=bcrypt.generate_password_hash("Demo2024!").decode("utf-8"),
                onboarding_complete=True,
                client_id=1
            )
            db.session.add(demo_user)
            db.session.commit()
            print("Demo user created: demo@clerviq.com / Demo2024!")
        else:
            print("Demo user already exists")

    print("Starting Flask app...")
    app.run(debug=True, port=5000)