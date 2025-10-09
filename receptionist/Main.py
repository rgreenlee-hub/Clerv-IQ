"""
Elite AI Receptionist - Main Controller (FIXED)
---------------------------------------
This connects all components with proper error handling
"""

import time
from Config import CLIENTS
from TwilioHandler import TwilioHandler
from brain import ReceptionistBrain
from Emails import process_email, send_email
from Analytics import Analytics
from Logs import EliteLogger

logger = EliteLogger()
brain = ReceptionistBrain()


def run_receptionist_for_client(client):
    """
    Run the receptionist for a single client
    """
    try:
        client_id = client["client_id"]
        logger.success(
            f"Initializing receptionist for {client['business_config']['company_name']}",
            client_id=client_id
        )

        # Setup Twilio handler
        twilio = TwilioHandler(client["twilio_config"])
        
        # Setup Analytics with GHL config
        analytics = Analytics(ghl_config=client.get("ghl_config"))

        # Main loop
        while True:
            # 1. Process incoming calls/SMS (simulated for now)
            try:
                # In production, this would be triggered by Twilio webhooks
                # For now, simulate incoming message
                incoming_msg = "Hi, I'd like to book an appointment."
                ai_reply = brain.analyze_message(incoming_msg)

                # Example: send SMS reply
                # result = twilio.send_sms("+14445556666", ai_reply)
                
                logger.info(
                    f"Message processed | Incoming: {incoming_msg[:50]}... | Reply generated",
                    client_id=client_id
                )
            except Exception as e:
                logger.error(
                    "Call/SMS handling error",
                    client_id=client_id,
                    context={"error": str(e)}
                )

            # 2. Process emails
            try:
                email_results = process_email(client["email_config"])
                for result in email_results:
                    ai_reply = brain.analyze_message(result["body"])
                    
                    # Log the email
                    analytics.log_email(
                        client_id=client_id,
                        sender=result["from"],
                        subject=result["subject"],
                        body=result["body"]
                    )
                    
                    logger.info(
                        f"Email processed from {result['from']} - {result['classification']}",
                        client_id=client_id
                    )
                    
                    # Auto-reply for leads
                    if result["classification"] == "lead":
                        try:
                            send_email(
                                client["email_config"],
                                result["from"],
                                f"Re: {result['subject']}",
                                ai_reply
                            )
                        except Exception as e:
                            logger.error(
                                "Email auto-reply failed",
                                client_id=client_id,
                                context={"error": str(e)}
                            )
            except Exception as e:
                logger.error(
                    "Email handling error",
                    client_id=client_id,
                    context={"error": str(e)}
                )

            # 3. Update analytics
            try:
                report = analytics.get_advanced_analytics(client_id)
                logger.success(
                    f"Analytics updated - {report.get('total_leads', 0)} total leads",
                    client_id=client_id
                )
            except Exception as e:
                logger.error(
                    "Analytics error",
                    client_id=client_id,
                    context={"error": str(e)}
                )

            # Wait before next loop (60 seconds)
            time.sleep(60)

    except KeyboardInterrupt:
        logger.warning(f"Receptionist stopped for {client_id}")
        return
    except Exception as e:
        logger.error(
            "Client initialization error",
            client_id=client.get("client_id", "unknown"),
            context={"error": str(e)}
        )


if __name__ == "__main__":
    logger.info("🚀 Elite AI Receptionist System Starting...")

    # For production: run each client in a separate thread/process
    # For now, run the first client
    if CLIENTS:
        run_receptionist_for_client(CLIENTS[0])
    else:
        logger.error("No clients configured in Config.py")