from twilio.rest import Client
from execution.config import (
    TWILIO_ACCOUNT_SID, 
    TWILIO_AUTH_TOKEN, 
    TWILIO_PHONE_NUMBER
)
from execution.utils.logging import logger

class TwilioConnector:
    def __init__(self):
        if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
            logger.warning("Twilio credentials missing. Connector in mock mode.")
            self.client = None
        else:
            self.client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

    def send_sms(self, to_number, body):
        """
        Sends an SMS via Twilio.
        Returns the SID if successful, None if failed (exceptions logged).
        """
        if not self.client:
            logger.info(f"[MOCK] Sending SMS to {to_number}: {body}")
            return "mock_sid_123"

        try:
            message = self.client.messages.create(
                body=body,
                from_=TWILIO_PHONE_NUMBER,
                to=to_number
            )
            logger.info(f"Twilio message sent. SID: {message.sid}")
            return message.sid
        except Exception as e:
            logger.error(f"Failed to send Twilio SMS: {e}")
            raise e
