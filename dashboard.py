from flask import Blueprint, render_template
from datetime import datetime
from receptionist.elite_ai_receptionist import EliteAIReceptionist
from Config import CLIENTS

# ---------- Blueprint ----------
dashboard_bp = Blueprint("dashboard", __name__)

# ---------- Local "in-memory" DB (backup in case receptionist isn't running) ----------
DB = {
    "leads": [],
    "appointments": [],
    "opps": [],
    "activity_feed": []
}

# ---------- Helper Functions ----------
def log_activity(message):
    """Logs any receptionist events like calls, SMS, emails."""
    DB["activity_feed"].append({
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "message": message
    })


def get_dashboard_stats():
    """Try pulling live analytics from receptionist, fallback to local mock data."""
    try:
        client_conf = CLIENTS[0]
        receptionist = EliteAIReceptionist(client_conf)
        analytics_data = receptionist.get_analytics()
        
        # Get core analytics
        core = analytics_data.get('core_analytics', {})
        
        # Format for chart.js
        stats = {
            **core,  # Spread all core analytics
            # Format chart data with labels and data arrays
            "leads_over_time": {
                "labels": core.get("dates", []),
                "data": core.get("leads_over_time", [])
            },
            "appointments_trend": {
                "labels": core.get("appt_dates", []),
                "data": core.get("appt_booked", [])
            },
            "channel_breakdown": {
                "labels": ["Calls", "SMS", "Email"],
                "data": [
                    core.get("channel_breakdown", {}).get("calls", 0),
                    core.get("channel_breakdown", {}).get("sms", 0),
                    core.get("channel_breakdown", {}).get("emails", 0)
                ]
            },
            "pipeline_stages": {
                "labels": list(core.get("pipeline_summary", {}).keys()),
                "data": [v.get("count", 0) for v in core.get("pipeline_summary", {}).values()]
            },
            "funnel": {
                "labels": ["Leads", "Booked", "Completed", "Won"],
                "data": [
                    core.get("funnel", {}).get("leads", 0),
                    core.get("funnel", {}).get("booked", 0),
                    core.get("funnel", {}).get("completed", 0),
                    core.get("funnel", {}).get("won", 0)
                ]
            }
        }
        return stats
        
    except Exception as e:
        print(f"[WARNING] Could not fetch live analytics: {e}")
        # Fallback to local dummy stats
        return {
            "calls_data": {},
            "sms_data": {},
            "email_data": {},
            "leads_data": {},
            "opportunities": [],
            "forecast": {
                "labels": ["Jan", "Feb", "Mar"],
                "data": [1000, 2000, 3000],
                "weighted_forecast": 3000
            },
            "lead_breakdown": {"Hot": 0, "Warm": 0, "Cold": 0},
            "leads_over_time": {"labels": ["Week 1", "Week 2", "Week 3"], "data": [5, 10, 15]},
            "appointments_trend": {"labels": ["Mon", "Tue", "Wed"], "data": [2, 3, 5]},
            "channel_breakdown": {"labels": ["Calls", "SMS", "Email"], "data": [10, 20, 30]},
            "pipeline_stages": {"labels": ["Stage 1", "Stage 2", "Stage 3"], "data": [3, 6, 9]},
            "funnel": {"labels": ["Leads", "Opportunities", "Deals"], "data": [100, 40, 10]},
            "recent_activity": DB.get("activity_feed", [])
        }

# ---------- Dashboard + Sidebar Routes ----------
@dashboard_bp.route("/dashboard")
def dashboard():
    stats = get_dashboard_stats()
    return render_template("dashboard.html", stats=stats)

@dashboard_bp.route("/calls")
def calls_page():
    stats = get_dashboard_stats()
    calls = stats.get("calls_data", {})
    if not calls:
        calls = [a for a in DB.get("activity_feed", []) if "call" in a["message"].lower()]
    return render_template("calls.html", data=calls)

@dashboard_bp.route("/sms")
def sms_page():
    stats = get_dashboard_stats()
    sms = stats.get("sms_data", {})
    if not sms:
        sms = [a for a in DB.get("activity_feed", []) if "sms" in a["message"].lower()]
    return render_template("sms.html", data=sms)

@dashboard_bp.route("/emails")
def emails_page():
    stats = get_dashboard_stats()
    emails = stats.get("email_data", {})
    if not emails:
        emails = [a for a in DB.get("activity_feed", []) if "email" in a["message"].lower()]
    return render_template("emails.html", data=emails)

@dashboard_bp.route("/leads")
def leads_page():
    stats = get_dashboard_stats()
    leads = stats.get("leads_data", {})
    if not leads:
        # fallback example data
        leads = {
            "total_leads": 100,
            "active": 40,
            "converted": 30,
            "lost": 30,
            "conversion_rate": "32.8%",
            "top_source": "Inbound Calls",
            "avg_followup_time": "2.4 hrs",
            "lead_pipeline": [
                {"name": "John Smith", "stage": "New", "value": "$15,000", "priority": "High", "days_in_stage": 2},
                {"name": "Sarah Johnson", "stage": "Qualified", "value": "$25,000", "priority": "Medium", "days_in_stage": 5},
                {"name": "Mike Brown", "stage": "Proposal", "value": "$40,000", "priority": "High", "days_in_stage": 8},
                {"name": "Emma Davis", "stage": "Closed Won", "value": "$60,000", "priority": "High", "days_in_stage": 10},
            ]
        }
    return render_template("leads.html", data=leads)

@dashboard_bp.route("/opportunities")
def opportunities_page():
    stats = get_dashboard_stats()
    opps = stats.get("opportunities", [])
    return render_template("opportunities.html", opps=opps)

@dashboard_bp.route("/analytics")
def analytics_page():
    stats = get_dashboard_stats()
    return render_template("analytics.html", stats=stats)

@dashboard_bp.route("/integrations")
def integrations_page():
    integrations = {
        "twilio": {"status": "Connected", "last_sync": "2025-10-01"},
        "stripe": {"status": "Connected", "last_sync": "2025-10-02"},
        "google": {"status": "Pending", "last_sync": None},
    }
    return render_template("integrations.html", integrations=integrations)

@dashboard_bp.route("/billing")
def billing_page():
    billing = {
        "plan": "Concierge Plan",
        "price": "$2,000 / month",
        "status": "Active",
        "renewal": "2025-11-01"
    }
    return render_template("billing.html", billing=billing)

@dashboard_bp.route("/settings")
def settings_page():
    user = {"name": "Demo User", "email": "demo@clerviq.com"}
    company = {"name": "ClervIQ Inc.", "industry": "Real Estate AI"}
    return render_template("settings.html", user=user, company=company)