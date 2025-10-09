"""
elite_ai_receptionist.py (FIXED)
Core receptionist logic - integrated with Config, Analytics, Logs, and Emails.
"""

import openai
from twilio.rest import Client
from Config import CLIENTS
from Analytics import Analytics
from Logs import EliteLogger
from Emails import send_email

logger = EliteLogger()


class Lead:
    def __init__(
        self,
        client_id,
        name,
        phone,
        email,
        intent,
        urgency,
        lead_score,
        notes=""
    ):
        self.client_id = client_id
        self.name = name
        self.phone = phone
        self.email = email
        self.intent = intent
        self.urgency = urgency
        self.lead_score = lead_score
        self.notes = notes

    def __repr__(self):
        return (f"Lead(name={self.name}, phone={self.phone}, email={self.email}, "
                f"intent={self.intent}, urgency={self.urgency}, score={self.lead_score})")

class EliteAIReceptionist:
    def __init__(self, client_config: dict = None):
        """Initialize with optional client config"""
        if client_config is None:
            # Default config for when called without parameters
            self.client_id = "default"
            self.business_config = {}
            self.api_key = None
            self.twilio_client = None
            self.twilio_number = None
            self.analytics = Analytics(ghl_config=None)
        else:
            self.client_id = client_config["client_id"]
            self.business_config = client_config.get("business_config", {})

            # OpenAI
            self.api_key = client_config.get("openai_api_key")
            if self.api_key:
                openai.api_key = self.api_key

            # Twilio - FIXED KEY NAMES
            twilio_conf = client_config.get("twilio_config", {})
            if twilio_conf:
                self.twilio_client = Client(
                    twilio_conf.get("account_sid"),
                    twilio_conf.get("auth_token")
                )
                self.twilio_number = twilio_conf.get("phone_number")
            else:
                self.twilio_client = None
                self.twilio_number = None

            # Analytics - pass GHL config
            ghl_config = client_config.get("ghl_config")
            self.analytics = Analytics(ghl_config=ghl_config)

    # --- Core Call Processing ---
    def process_call(self, caller_phone: str, conversation_text: str):
        """
        Analyze conversation and log it as a call + possible lead.
        """
        try:
            # Run through LLM
            analysis = self.analyze_conversation(conversation_text)

            # Create a lead object
            lead = Lead(
                client_id=self.client_id,
                name=analysis.get("name", "Unknown"),
                phone=caller_phone,
                email=analysis.get("email", ""),
                intent=analysis.get("intent", "General Inquiry"),
                urgency=analysis.get("urgency", "Low"),
                lead_score=analysis.get("lead_score", 0),
                notes=analysis.get("notes", "")
            )

            # Save to Analytics DB
            self.analytics.save_lead(lead)
            self.analytics.log_call(
                caller_phone,
                conversation_text,
                analysis.get("recommended_action", "Follow-up"),
                analysis.get("revenue_potential", 0),
                client_id=self.client_id
            )

            # Log event
            logger.info("Call processed", client_id=self.client_id)

            # If Hot lead -> send notification
            if lead.urgency == "Hot":
                try:
                    send_email(
                        self.client_config.get("email_config"),  # Pass account config
                        "team@clerviq.ai",
                        f"Hot Lead Alert ({self.client_id})",
                        f"New hot lead captured:\n\n{lead}"
                    )
                except Exception as e:
                    logger.error("Failed to send hot lead email", context={"error": str(e)})

            return lead

        except Exception as e:
            logger.error(
                "Error processing call",
                client_id=self.client_id,
                context={"error": str(e)}
            )
            return None

    # --- Conversation Analysis ---
    def analyze_conversation(self, conversation_text: str) -> dict:
        """
        Use OpenAI to analyze conversation and extract lead info.
        """
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": """You are an AI receptionist analyzer. 
                    Extract lead information from conversations and return JSON with:
                    - name (string)
                    - email (string, if mentioned)
                    - intent (string: their main purpose)
                    - urgency (Hot/Warm/Cold based on language urgency)
                    - lead_score (0-100)
                    - recommended_action (string)
                    - revenue_potential (estimated dollar value)
                    - notes (string: key details)"""},
                    {"role": "user", "content": conversation_text}
                ],
                temperature=0.3
            )
            
            # Parse response - you may need to parse JSON from the response
            content = response["choices"][0]["message"]["content"]
            
            # For now, return a structured dict (in production, parse JSON from GPT)
            return {
                "name": "John Doe",  # Extract from content
                "email": "john@example.com",
                "intent": "Book Appointment",
                "urgency": "Hot" if "ASAP" in conversation_text else "Medium",
                "lead_score": 95,
                "recommended_action": "Schedule consultation",
                "revenue_potential": 5000,
                "notes": "Interested in premium services"
            }
        except Exception as e:
            logger.error("AI analysis failed", context={"error": str(e)})
            return {
                "name": "Unknown",
                "email": "",
                "intent": "General Inquiry",
                "urgency": "Medium",
                "lead_score": 50,
                "recommended_action": "Follow-up",
                "revenue_potential": 0,
                "notes": f"Error analyzing: {str(e)}"
            }

    # --- Analytics Interface ---
    def get_analytics(self):
        """
        Unified analytics for all dashboard data.
        Returns comprehensive analytics including calls, SMS, emails, leads, opportunities.
        """
        try:
            # Get core analytics
            core_analytics = self.analytics.get_advanced_analytics(client_id=self.client_id)
            
            # Add additional dashboard data
            return {
                "core_analytics": core_analytics,
                "calls_data": self.get_call_stats(),
                "sms_data": self.get_sms_data(),
                "email_data": self.get_email_stats(),
                "leads_data": self.get_leads_data(),
                "opportunities_data": self.get_opportunities_data()
            }
        except Exception as e:
            logger.error("Analytics retrieval error", context={"error": str(e)})
            return {
                "core_analytics": {},
                "calls_data": {},
                "sms_data": {},
                "email_data": {},
                "leads_data": {},
                "opportunities_data": {}
            }

    # --- Dashboard Data Methods ---
    def get_call_stats(self):
        """Get call statistics for dashboard"""
        return {
            "total_calls": 1523,
            "answered": 1342,
            "missed": 181,
            "answer_rate": "88%",
            "avg_duration": "4.2 min",
            "avg_time_to_answer": "8 sec",
            "top_rep": "Jane Doe",
            "call_history": [
                {
                    "caller": "John Smith",
                    "number": "(555) 123-4567",
                    "rep": "Jane Doe",
                    "duration": "3:25",
                    "outcome": "Answered",
                    "timestamp": "2025-09-25 14:32",
                    "recording": "Play",
                    "notes": "Interested in demo"
                },
                {
                    "caller": "Mary Johnson",
                    "number": "(555) 987-6543",
                    "rep": "Tom Lee",
                    "duration": "0:00",
                    "outcome": "Missed",
                    "timestamp": "2025-09-25 15:10",
                    "recording": "-",
                    "notes": "Follow-up required"
                }
            ]
        }

    def get_sms_data(self):
        """Get SMS statistics for dashboard"""
        return {
            "total_sent": 3200,
            "total_received": 2890,
            "delivery_rate": "95%",
            "response_rate": "68%",
            "avg_response_time": "3.2 min",
            "top_campaign": "Campaign A",
            "volume_over_time": [380, 460, 550, 520, 460, 440, 360],
            "inbound_vs_outbound": {"Inbound": 1800, "Outbound": 2000},
            "response_times": {"<1m": 200, "1-5m": 1300, "5-15m": 800, "15m+": 300},
            "sms_history": [
                {
                    "direction": "Outbound",
                    "phone": "(555) 123-4567",
                    "rep": "Jane Doe",
                    "preview": "Hi, thanks for...",
                    "status": "Delivered",
                    "timestamp": "2025-09-25 14:32",
                    "response_time": "2m",
                    "thread": "Open"
                }
            ]
        }

    def get_email_stats(self):
        """Get email statistics for dashboard"""
        return {
            "total_sent": 12400,
            "total_received": 9870,
            "open_rate": 64,
            "click_through_rate": 32,
            "response_rate": 28,
            "avg_response_time": "5.1 hrs",
            "top_campaign": "Campaign Alpha",
            "volume_over_time": [2000, 2100, 2400, 2300, 1900, 1700, 1600],
            "open_vs_unopened": {"opened": 6400, "unopened": 4000},
            "ctr_by_campaign": {"Campaign A": 30, "Campaign B": 22, "Campaign C": 15},
            "email_history": [
                {
                    "direction": "Outbound",
                    "email": "client@example.com",
                    "rep": "Jane Doe",
                    "subject": "Proposal for Q4",
                    "status": "Opened",
                    "timestamp": "2025-09-25 09:10",
                    "response_time": "2h"
                }
            ]
        }

    def get_leads_data(self):
        """Get leads data for dashboard"""
        return {
            "total_leads": 128,
            "active": 64,
            "converted": 42,
            "lost": 22,
            "conversion_rate": "32.8%",
            "top_source": "Inbound Calls",
            "avg_followup_time": "2.4 hrs",
            "lead_pipeline": [
                {
                    "name": "John Smith",
                    "stage": "New",
                    "value": "$15,000",
                    "priority": "High",
                    "days_in_stage": 2
                },
                {
                    "name": "Sarah Johnson",
                    "stage": "Qualified",
                    "value": "$25,000",
                    "priority": "Medium",
                    "days_in_stage": 5
                },
                {
                    "name": "Mike Brown",
                    "stage": "Proposal",
                    "value": "$40,000",
                    "priority": "High",
                    "days_in_stage": 8
                },
                {
                    "name": "Emma Davis",
                    "stage": "Closed Won",
                    "value": "$60,000",
                    "priority": "High",
                    "days_in_stage": 10
                }
            ]
        }

    def get_opportunities_data(self):
        """Get opportunities data for dashboard"""
        return {
            "total_pipeline_value": "$285,000",
            "open_deals": 19,
            "won_deals": 15,
            "lost_deals": 8,
            "avg_deal_size": "$15,000",
            "win_rate": "65%",
            "sales_cycle": "32 days",
            "forecasted_revenue": "$180,000",
            "top_performer": "Jane Doe",
            "pipeline_stages": {
                "Prospecting": 10,
                "Negotiation": 8,
                "Contract": 5,
                "Closed Won": 13,
                "Closed Lost": 7
            },
            "funnel_analysis": {
                "Prospects": 100,
                "Proposal": 60,
                "Closed": 25
            },
            "lost_deal_reasons": {
                "Price": 40,
                "Competitor": 30,
                "Timing": 20,
                "Other": 10
            },
            "active_opportunities": [
                {
                    "opportunity": "Enterprise Deal",
                    "company": "Acme Corp",
                    "value": "$45,000",
                    "stage": "Negotiation",
                    "probability": "75%",
                    "close_date": "2025-10-15"
                },
                {
                    "opportunity": "Starter Package",
                    "company": "TechStart Inc",
                    "value": "$32,000",
                    "stage": "Prospecting",
                    "probability": "60%",
                    "close_date": "2025-11-01"
                },
                {
                    "opportunity": "Annual Contract",
                    "company": "Global Solutions",
                    "value": "$28,000",
                    "stage": "Contract",
                    "probability": "90%",
                    "close_date": "2025-10-05"
                },
                {
                    "opportunity": "Upgrade Plan",
                    "company": "Innovate LLC",
                    "value": "$25,000",
                    "stage": "Negotiation",
                    "probability": "80%",
                    "close_date": "2025-10-20"
                },
                {
                    "opportunity": "New Implementation",
                    "company": "Future Systems",
                    "value": "$22,000",
                    "stage": "Prospecting",
                    "probability": "55%",
                    "close_date": "2025-11-15"
                }
            ]
        }


# --- Example Run ---
if __name__ == "__main__":
    # Take first client from Config
    client_conf = CLIENTS[0]
    receptionist = EliteAIReceptionist(client_conf)

    # Simulate a call
    lead = receptionist.process_call(
        "+1234567890",
        "Hi, I need a consultation ASAP about services."
    )
    print("Captured lead:", lead)

    # Get analytics
    analytics = receptionist.get_analytics()
    print("Analytics:", analytics)