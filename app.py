from flask import Flask, render_template, send_from_directory
import os

# ---------------------
# Basic Flask Setup
# ---------------------
template_dir = os.path.abspath("templates")
static_dir = os.path.abspath("static")

app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)

# Disable caching so changes appear instantly
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

# ---------------------
# Public Website Pages
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

@app.route("/contact")
def contact():
    return render_template("contact.html")

@app.route("/privacy")
def privacy():
    return render_template("privacy.html")

@app.route("/terms")
def terms():
    return render_template("terms.html")

# ---------------------
# Static Files
# ---------------------
@app.route("/static/<path:filename>")
def serve_static(filename):
    return send_from_directory(static_dir, filename)

# ---------------------
# Run App
# ---------------------
if __name__ == "__main__":
    print("Running static website server on http://127.0.0.1:5000")
    app.run(debug=True, port=5000)
