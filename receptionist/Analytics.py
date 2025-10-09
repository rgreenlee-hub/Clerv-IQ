"""
Elite AI Receptionist - Advanced Analytics (Fixed)
"""

import sqlite3
import requests
from datetime import datetime, timedelta

DB_PATH = "receptionist.db"

class Analytics:
    def __init__(self, db_path=DB_PATH, ghl_config=None):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row

        # Expect a dict: {"api_key": "...", "location_id": "..."}
        self.ghl_api_key = ghl_config.get("api_key") if ghl_config else None
        self.ghl_location_id = ghl_config.get("location_id") if ghl_config else None
        
        # Ensure tables exist
        self._init_tables()

    # -------------------------------
    # Initialize tables if missing
    # -------------------------------
    def _init_tables(self):
        cursor = self.conn.cursor()
        
        # Create tables if they don't exist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS call_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id TEXT,
                caller_phone TEXT,
                conversation TEXT,
                action TEXT,
                revenue_potential REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS email_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id TEXT,
                sender TEXT,
                subject TEXT,
                body TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sms_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id TEXT,
                phone TEXT,
                message TEXT,
                direction TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id TEXT,
                name TEXT,
                phone TEXT,
                email TEXT,
                intent TEXT,
                urgency TEXT,
                classification TEXT,
                lead_score INTEGER,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pipeline_leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id TEXT,
                status TEXT,
                value REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS appointments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id TEXT,
                status TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS activity_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id TEXT,
                event TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        self.conn.commit()

    # -------------------------------
    # ADDED: Save lead to database
    # -------------------------------
    def save_lead(self, lead):
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO leads (client_id, name, phone, email, intent, urgency, classification, lead_score, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            lead.client_id,
            lead.name,
            lead.phone,
            lead.email,
            lead.intent,
            lead.urgency,
            lead.urgency,  # classification = urgency for now
            lead.lead_score,
            lead.notes
        ))
        self.conn.commit()
        return cursor.lastrowid

    # -------------------------------
    # ADDED: Log call to database
    # -------------------------------
    def log_call(self, caller_phone, conversation, action, revenue_potential, client_id):
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO call_logs (client_id, caller_phone, conversation, action, revenue_potential)
            VALUES (?, ?, ?, ?, ?)
        """, (client_id, caller_phone, conversation, action, revenue_potential))
        self.conn.commit()
        return cursor.lastrowid

    # -------------------------------
    # ADDED: Log email
    # -------------------------------
    def log_email(self, client_id, sender, subject, body):
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO email_logs (client_id, sender, subject, body)
            VALUES (?, ?, ?, ?)
        """, (client_id, sender, subject, body))
        self.conn.commit()

    # -------------------------------
    # ADDED: Log SMS
    # -------------------------------
    def log_sms(self, client_id, phone, message, direction="outbound"):
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO sms_logs (client_id, phone, message, direction)
            VALUES (?, ?, ?, ?)
        """, (client_id, phone, message, direction))
        self.conn.commit()

    # -------------------------------
    # Helper: run query
    # -------------------------------
    def _fetch(self, query, params=()):
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        return cursor.fetchall()

    # -------------------------------
    # Daily activity summary
    # -------------------------------
    def get_daily_summary(self, client_id):
        today = datetime.utcnow().date()

        calls = self._fetch(
            "SELECT COUNT(*) as c FROM call_logs WHERE client_id=? AND DATE(created_at)=?",
            (client_id, today)
        )[0]["c"]

        emails = self._fetch(
            "SELECT COUNT(*) as c FROM email_logs WHERE client_id=? AND DATE(created_at)=?",
            (client_id, today)
        )[0]["c"]

        sms = self._fetch(
            "SELECT COUNT(*) as c FROM sms_logs WHERE client_id=? AND DATE(created_at)=?",
            (client_id, today)
        )[0]["c"]

        return {
            "client_id": client_id,
            "date": str(today),
            "calls": calls,
            "emails": emails,
            "sms": sms,
            "total_interactions": calls + emails + sms
        }

    # -------------------------------
    # Lead breakdown (Hot/Warm/Cold)
    # -------------------------------
    def get_lead_breakdown(self, client_id, days=7):
        since = datetime.utcnow().date() - timedelta(days=days)

        leads = self._fetch(
            "SELECT classification FROM leads WHERE client_id=? AND DATE(created_at)>=?",
            (client_id, since)
        )

        breakdown = {"Hot": 0, "Warm": 0, "Cold": 0}
        for row in leads:
            c = row["classification"]
            if c in breakdown:
                breakdown[c] += 1

        return breakdown

    # -------------------------------
    # Revenue potential (simple estimate)
    # -------------------------------
    def get_revenue_potential(self, client_id, days=30):
        since = datetime.utcnow().date() - timedelta(days=days)

        leads = self._fetch(
            "SELECT classification FROM leads WHERE client_id=? AND DATE(created_at)>=?",
            (client_id, since)
        )

        weights = {"Hot": 1000, "Warm": 500, "Cold": 100}
        total_value = sum(weights.get(row["classification"], 0) for row in leads)

        return {"client_id": client_id, "estimated_value": total_value}

    # -------------------------------
    # Channel breakdown
    # -------------------------------
    def get_channel_breakdown(self, client_id, days=30):
        since = datetime.utcnow().date() - timedelta(days=days)

        calls = self._fetch(
            "SELECT COUNT(*) as c FROM call_logs WHERE client_id=? AND DATE(created_at)>=?",
            (client_id, since)
        )[0]["c"]

        emails = self._fetch(
            "SELECT COUNT(*) as c FROM email_logs WHERE client_id=? AND DATE(created_at)>=?",
            (client_id, since)
        )[0]["c"]

        sms = self._fetch(
            "SELECT COUNT(*) as c FROM sms_logs WHERE client_id=? AND DATE(created_at)>=?",
            (client_id, since)
        )[0]["c"]

        total = calls + emails + sms
        return {
            "calls": calls,
            "emails": emails,
            "sms": sms,
            "total": total,
            "call_pct": round(calls / total * 100, 1) if total else 0,
            "email_pct": round(emails / total * 100, 1) if total else 0,
            "sms_pct": round(sms / total * 100, 1) if total else 0,
        }

    # -------------------------------
    # CRM: Pipeline summary
    # -------------------------------
    def get_pipeline_summary(self, client_id):
        rows = self._fetch(
            "SELECT status, COUNT(*) as c, SUM(value) as v "
            "FROM pipeline_leads WHERE client_id=? GROUP BY status",
            (client_id,)
        )
        return {
            row["status"]: {"count": row["c"], "value": row["v"] or 0}
            for row in rows
        }

    # -------------------------------
    # CRM: Weighted revenue forecast
    # -------------------------------
    def get_weighted_forecast(self, client_id):
        rows = self._fetch(
            "SELECT status, value FROM pipeline_leads WHERE client_id=?",
            (client_id,)
        )

        probabilities = {
            "New": 0.1,
            "Contacted": 0.25,
            "Qualified": 0.5,
            "Proposal": 0.7,
            "Closed Won": 1.0,
            "Closed Lost": 0.0
        }

        forecast = 0
        for row in rows:
            prob = probabilities.get(row["status"], 0)
            forecast += (row["value"] or 0) * prob

        return {"client_id": client_id, "weighted_forecast": forecast}

    # -------------------------------
    # GHL API metrics (pipeline + conversations)
    # -------------------------------
    def get_ghl_metrics(self):
        if not self.ghl_api_key or not self.ghl_location_id:
            return {"error": "Missing GHL credentials"}

        headers = {"Authorization": f"Bearer {self.ghl_api_key}"}

        try:
            pipeline_url = f"https://rest.gohighlevel.com/v1/pipelines/stats?locationId={self.ghl_location_id}"
            r1 = requests.get(pipeline_url, headers=headers)

            conv_url = f"https://rest.gohighlevel.com/v1/conversations?locationId={self.ghl_location_id}"
            r2 = requests.get(conv_url, headers=headers)

            return {
                "pipeline_stats": r1.json() if r1.status_code == 200 else {"error": f"Pipeline API error {r1.status_code}"},
                "conversations": r2.json() if r2.status_code == 200 else {"error": f"Conversations API error {r2.status_code}"}
            }
        except Exception as e:
            return {"error": f"GHL request failed: {str(e)}"}

    # -------------------------------
    # Generate time-series for charts
    # -------------------------------
    def get_timeseries(self, client_id, days=14):
        since = datetime.utcnow().date() - timedelta(days=days)
        rows = self._fetch(
            "SELECT DATE(created_at) as d, COUNT(*) as c FROM leads "
            "WHERE client_id=? AND DATE(created_at)>=? GROUP BY DATE(created_at) ORDER BY d",
            (client_id, since)
        )
        dates = [row["d"] for row in rows]
        counts = [row["c"] for row in rows]
        return dates, counts

    def get_appt_timeseries(self, client_id, days=14):
        since = datetime.utcnow().date() - timedelta(days=days)
        rows = self._fetch(
            "SELECT DATE(created_at) as d, status, COUNT(*) as c FROM appointments "
            "WHERE client_id=? AND DATE(created_at)>=? GROUP BY DATE(created_at), status ORDER BY d",
            (client_id, since)
        )
        series = {}
        for row in rows:
            d = row["d"]
            status = row["status"]
            c = row["c"]
            if d not in series:
                series[d] = {"Booked": 0, "Completed": 0, "No-Show": 0}
            if status in series[d]:
                series[d][status] += c
        dates = list(series.keys())
        booked = [series[d]["Booked"] for d in dates]
        completed = [series[d]["Completed"] for d in dates]
        no_shows = [series[d]["No-Show"] for d in dates]
        return dates, booked, completed, no_shows

    # -------------------------------
    # Full advanced analytics (dashboard-ready)
    # -------------------------------
    def get_advanced_analytics(self, client_id):
        daily = self.get_daily_summary(client_id)
        lead_breakdown = self.get_lead_breakdown(client_id)
        revenue_potential = self.get_revenue_potential(client_id)
        channel_breakdown = self.get_channel_breakdown(client_id)
        pipeline_summary = self.get_pipeline_summary(client_id)
        forecast = self.get_weighted_forecast(client_id)

        leads_total = sum(lead_breakdown.values())
        appts_total = pipeline_summary.get("Closed Won", {}).get("count", 0)
        conversion_rate = round((appts_total / leads_total) * 100, 2) if leads_total else 0
        roi = revenue_potential["estimated_value"]

        ghl = self.get_ghl_metrics()
        total_opps = 0
        pipeline_value = 0
        if isinstance(ghl, dict) and "pipeline_stats" in ghl:
            try:
                total_opps = ghl["pipeline_stats"].get("totalOpportunities", 0)
                pipeline_value = ghl["pipeline_stats"].get("totalValue", 0)
            except Exception:
                pass

        recent_activity = self._fetch(
            "SELECT created_at, event FROM activity_logs WHERE client_id=? "
            "ORDER BY created_at DESC LIMIT 10",
            (client_id,)
        )
        activity_list = [
            {"timestamp": row["created_at"], "message": row["event"]}
            for row in recent_activity
        ]

        dates, leads_over_time = self.get_timeseries(client_id, days=14)
        appt_dates, appt_booked, appt_completed, appt_no_shows = self.get_appt_timeseries(client_id, days=14)

        funnel = {
            "leads": leads_total,
            "booked": sum(appt_booked) if appt_booked else 0,
            "completed": sum(appt_completed) if appt_completed else 0,
            "won": pipeline_summary.get("Closed Won", {}).get("count", 0)
        }

        return {
            "total_leads": leads_total,
            "appointments": appts_total,
            "conversion_rate": conversion_rate,
            "roi": roi,
            "total_opps": total_opps,
            "pipeline_value": pipeline_value,
            "dates": dates,
            "leads_over_time": leads_over_time,
            "appt_dates": appt_dates,
            "appt_booked": appt_booked,
            "appt_completed": appt_completed,
            "appt_no_shows": appt_no_shows,
            "recent_activity": activity_list,
            "lead_breakdown": lead_breakdown,
            "channel_breakdown": channel_breakdown,
            "pipeline_summary": pipeline_summary,
            "forecast": {
                "weighted_forecast": forecast["weighted_forecast"]  # FIXED: Extract just the value for template
            },
            "daily_summary": daily,
            "ghl_raw": ghl,
            "funnel": funnel
        }