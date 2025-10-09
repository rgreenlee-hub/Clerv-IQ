"""
TwilioHandler.py (FIXED)
Handles Twilio calls and SMS with proper error handling
"""

from twilio.rest import Client
from Logs import EliteLogger

logger = EliteLogger()


class TwilioHandler:
    def __init__(self, config):
        """
        Initialize Twilio client with proper error handling
        Args:
            config: dict with 'account_sid', 'auth_token', 'phone_number'
        """
        try:
            self.client = Client(config["account_sid"], config["auth_token"])
            self.phone_number = config["phone_number"]
            logger.success(f"Twilio initialized for {self.phone_number}")
        except Exception as e:
            logger.error("Twilio initialization failed", context={"error": str(e)})
            raise

    def make_call(self, to_number, url):
        """
        Make an outbound call
        Args:
            to_number: Phone number to call
            url: TwiML URL for call instructions
        Returns:
            Call SID if successful, None if failed
        """
        try:
            call = self.client.calls.create(
                to=to_number,
                from_=self.phone_number,
                url=url
            )
            logger.info(f"Call initiated to {to_number}", context={"sid": call.sid})
            return call
        except Exception as e:
            logger.error(f"Failed to make call to {to_number}", context={"error": str(e)})
            return None

    def send_sms(self, to_number, body):
        """
        Send an SMS message
        Args:
            to_number: Phone number to send to
            body: Message content
        Returns:
            Message SID if successful, None if failed
        """
        try:
            message = self.client.messages.create(
                to=to_number,
                from_=self.phone_number,
                body=body
            )
            logger.info(f"SMS sent to {to_number}", context={"sid": message.sid})
            return message
        except Exception as e:
            logger.error(f"Failed to send SMS to {to_number}", context={"error": str(e)})
            return None

    def get_call_logs(self, limit=50):
        """
        Retrieve recent call logs
        Args:
            limit: Number of recent calls to retrieve
        Returns:
            List of call objects
        """
        try:
            calls = self.client.calls.list(limit=limit)
            logger.info(f"Retrieved {len(calls)} call logs")
            return calls
        except Exception as e:
            logger.error("Failed to retrieve call logs", context={"error": str(e)})
            return []

    def get_message_logs(self, limit=50):
        """
        Retrieve recent SMS logs
        Args:
            limit: Number of recent messages to retrieve
        Returns:
            List of message objects
        """
        try:
            messages = self.client.messages.list(limit=limit)
            logger.info(f"Retrieved {len(messages)} message logs")
            return messages
        except Exception as e:
            logger.error("Failed to retrieve message logs", context={"error": str(e)})
            return []