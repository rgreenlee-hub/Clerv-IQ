"""
auth.py - User Authentication & Session Management
Handles signup, login, logout, and client session tracking
"""

from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mail import Mail, Message
import sqlite3
from datetime import datetime
import json

auth_bp = Blueprint("auth", __name__)

DB_PATH = "receptionist.db"

# Mail will be initialized from app.py
mail = None

def init_mail(mail_instance):
    """Initialize mail from app.py"""
    global mail
    mail = mail_instance

DB_PATH = "receptionist.db"

# -------------------------------
# Helper: Get database connection
# -------------------------------
def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

# -------------------------------
# Initialize auth tables
# -------------------------------
def init_auth_tables():
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            company_name TEXT NOT NULL,
            industry TEXT,
            phone TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS client_configs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id TEXT NOT NULL,
            openai_api_key TEXT,
            twilio_sid TEXT,
            twilio_token TEXT,
            twilio_phone TEXT,
            ghl_api_key TEXT,
            ghl_location_id TEXT,
            email_provider TEXT,
            email_address TEXT,
            email_password TEXT,
            FOREIGN KEY(client_id) REFERENCES users(client_id)
        )
    """)
    
    conn.commit()
    conn.close()

# Call this when app starts
init_auth_tables()

# -------------------------------
# SIGNUP Route
# -------------------------------
@auth_bp.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        company_name = request.form.get("company_name")
        industry = request.form.get("industry", "")
        phone = request.form.get("phone", "")
        
        # Generate unique client_id from company name
        client_id = company_name.lower().replace(" ", "_").replace(".", "")
        
        # Hash password
        password_hash = generate_password_hash(password)
        
        try:
            conn = get_db()
            cursor = conn.cursor()
            
            # Insert user
            cursor.execute("""
                INSERT INTO users (client_id, email, password_hash, company_name, industry, phone)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (client_id, email, password_hash, company_name, industry, phone))
            
            conn.commit()
            conn.close()
            
            flash("Account created successfully! Please log in.", "success")
            return redirect(url_for("auth.login"))
            
        except sqlite3.IntegrityError:
            flash("Email already exists. Please use a different email.", "error")
            return render_template("signup.html")
    
    return render_template("signup.html")

# -------------------------------
# LOGIN Route
# -------------------------------
@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()
        conn.close()
        
        if user and check_password_hash(user["password_hash"], password):
            # Set session
            session["client_id"] = user["client_id"]
            session["email"] = user["email"]
            session["company_name"] = user["company_name"]
            
            flash(f"Welcome back, {user['company_name']}!", "success")
            return redirect(url_for("dashboard.dashboard"))
        else:
            flash("Invalid email or password", "error")
            return render_template("login.html")
    
    return render_template("login.html")

# -------------------------------
# LOGOUT Route
# -------------------------------
@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully", "success")
    return redirect(url_for("auth.login"))

# -------------------------------
# ONBOARDING Route (API Keys Setup)
# -------------------------------
@auth_bp.route("/onboarding", methods=["GET", "POST"])
def onboarding():
    if "client_id" not in session:
        return redirect(url_for("auth.login"))
    
    if request.method == "POST":
        client_id = session["client_id"]
        
        # Get form data
        openai_key = request.form.get("openai_api_key")
        twilio_sid = request.form.get("twilio_sid")
        twilio_token = request.form.get("twilio_token")
        twilio_phone = request.form.get("twilio_phone")
        ghl_api_key = request.form.get("ghl_api_key", "")
        ghl_location_id = request.form.get("ghl_location_id", "")
        email_provider = request.form.get("email_provider", "gmail")
        email_address = request.form.get("email_address")
        email_password = request.form.get("email_password")
        
        try:
            conn = get_db()
            cursor = conn.cursor()
            
            # Check if config exists
            cursor.execute("SELECT id FROM client_configs WHERE client_id = ?", (client_id,))
            existing = cursor.fetchone()
            
            if existing:
                # Update existing config
                cursor.execute("""
                    UPDATE client_configs 
                    SET openai_api_key=?, twilio_sid=?, twilio_token=?, twilio_phone=?,
                        ghl_api_key=?, ghl_location_id=?, email_provider=?, 
                        email_address=?, email_password=?
                    WHERE client_id=?
                """, (openai_key, twilio_sid, twilio_token, twilio_phone,
                      ghl_api_key, ghl_location_id, email_provider,
                      email_address, email_password, client_id))
            else:
                # Insert new config
                cursor.execute("""
                    INSERT INTO client_configs 
                    (client_id, openai_api_key, twilio_sid, twilio_token, twilio_phone,
                     ghl_api_key, ghl_location_id, email_provider, email_address, email_password)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (client_id, openai_key, twilio_sid, twilio_token, twilio_phone,
                      ghl_api_key, ghl_location_id, email_provider, email_address, email_password))
            
            conn.commit()
            conn.close()
            
            flash("Configuration saved successfully!", "success")
            return redirect(url_for("dashboard.dashboard"))
            
        except Exception as e:
            flash(f"Error saving configuration: {str(e)}", "error")
            return render_template("onboarding.html")
    
    return render_template("onboarding.html")

# -------------------------------
# COMPLETE REGISTRATION (from register.html wizard)
# -------------------------------
@auth_bp.route("/auth/complete-registration", methods=["POST"])
def complete_registration():
    """Complete registration after onboarding wizard - FIXED VERSION"""
    data = request.json
    
    email = data.get("email")
    password = data.get("password")
    company_name = data.get("company_name")
    industry = data.get("industry", "")
    phone = data.get("phone", "")
    
    # Validate required fields
    if not email or not password or not company_name:
        return jsonify({"success": False, "error": "Missing required fields"}), 400
    
    # Generate client_id from company name
    client_id = company_name.lower().replace(" ", "_").replace(".", "").replace("-", "_")
    
    # Hash password
    password_hash = generate_password_hash(password)
    
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Create user account in receptionist.db
        cursor.execute("""
            INSERT INTO users (client_id, email, password_hash, company_name, industry, phone)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (client_id, email, password_hash, company_name, industry, phone))
        
        # Create initial client config
        cursor.execute("""
            INSERT INTO client_configs 
            (client_id, email_provider, email_address)
            VALUES (?, ?, ?)
        """, (client_id, "gmail", email))
        
        conn.commit()
        conn.close()
        
        # Auto-login: Create session
        session["client_id"] = client_id
        session["email"] = email
        session["company_name"] = company_name
        
        return jsonify({
            "success": True,
            "message": "Account created successfully!",
            "redirect": "/dashboard"
        })
        
    except sqlite3.IntegrityError as e:
        return jsonify({
            "success": False,
            "error": "Email already exists. Please use a different email."
        }), 400
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Error creating account: {str(e)}"
        }), 500

# -------------------------------
# Helper: Get client config from DB
# -------------------------------
def get_client_config(client_id):
    """
    Retrieves client configuration from database
    Returns dict in same format as Config.CLIENTS
    """
    conn = get_db()
    cursor = conn.cursor()
    
    # Get user info
    cursor.execute("SELECT * FROM users WHERE client_id = ?", (client_id,))
    user = cursor.fetchone()
    
    # Get config
    cursor.execute("SELECT * FROM client_configs WHERE client_id = ?", (client_id,))
    config = cursor.fetchone()
    
    conn.close()
    
    if not user or not config:
        return None
    
    # Format as CLIENTS dict structure
    return {
        "client_id": client_id,
        "business_config": {
            "industry": user["industry"] or "general",
            "company_name": user["company_name"],
            "phone": user["phone"] or "",
            "services": []
        },
        "openai_api_key": config["openai_api_key"],
        "email_config": {
            "provider": config["email_provider"],
            "email": config["email_address"],
            "password": config["email_password"],
            "imap_host": "imap.gmail.com" if config["email_provider"] == "gmail" else "outlook.office365.com",
            "smtp_host": "smtp.gmail.com" if config["email_provider"] == "gmail" else "smtp.office365.com",
            "smtp_port": 465 if config["email_provider"] == "gmail" else 587
        },
        "twilio_config": {
            "account_sid": config["twilio_sid"],
            "auth_token": config["twilio_token"],
            "phone_number": config["twilio_phone"]
        },
        "ghl_config": {
            "api_key": config["ghl_api_key"] or "",
            "location_id": config["ghl_location_id"] or ""
        }
    }

# -------------------------------
# Helper: Require login decorator
# -------------------------------
def login_required(f):
    """Decorator to require login for routes"""
    from functools import wraps
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "client_id" not in session:
            flash("Please log in to access this page", "error")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    
    return decorated_function