"""
Elite AI Receptionist - Config File
-----------------------------------
Complete client configurations for plug-and-play onboarding.
"""

CLIENTS = [
    {
        "client_id": "demo_dentist",
        "business_config": {
            "industry": "healthcare",
            "company_name": "Bright Smiles Dental",
            "phone": "(555) 111-2222",
            "services": [
                "dental implants",
                "teeth whitening",
                "general dentistry"
            ]
        },
        "openai_api_key": "sk-YOUR_OPENAI_KEY_HERE",  # ADDED
        "email_config": {
            "provider": "gmail",
            "imap_host": "imap.gmail.com",
            "smtp_host": "smtp.gmail.com",
            "smtp_port": 465,
            "email": "frontdesk@brightsmiles.com",
            "password": "APP_PASSWORD",
            "calendar_type": "google",
            "google_creds": "google_service_account.json"
        },
        "twilio_config": {
            "account_sid": "YOUR_TWILIO_SID",  # FIXED KEY NAMES
            "auth_token": "YOUR_TWILIO_TOKEN",
            "phone_number": "+1234567890"
        },
        "ghl_config": {
            "api_key": "YOUR_GHL_KEY",
            "location_id": "YOUR_LOCATION_ID"
        }
    },
    {
        "client_id": "demo_realtor",
        "business_config": {
            "industry": "real_estate",
            "company_name": "Premium Properties Group",
            "phone": "(555) 333-4444",
            "services": [
                "luxury home sales",
                "investment properties",
                "property management"
            ]
        },
        "openai_api_key": "sk-YOUR_OPENAI_KEY_HERE",  # ADDED
        "email_config": {
            "provider": "outlook",
            "imap_host": "outlook.office365.com",
            "smtp_host": "smtp.office365.com",
            "smtp_port": 587,
            "email": "realtor@premiumprops.com",
            "password": "APP_PASSWORD",
            "calendar_type": "outlook",
            "outlook_client_id": "YOUR_CLIENT_ID",
            "outlook_client_secret": "YOUR_SECRET",
            "outlook_tenant": "common"
        },
        "twilio_config": {
            "account_sid": "YOUR_TWILIO_SID",
            "auth_token": "YOUR_TWILIO_TOKEN",
            "phone_number": "+1987654321"
        },
        "ghl_config": {
            "api_key": "YOUR_GHL_KEY",
            "location_id": "YOUR_LOCATION_ID"
        }
    }
]