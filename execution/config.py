import os
from dotenv import load_dotenv

load_dotenv()

# Twilio Config
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")

# Owner Config
OWNER_PHONE_NUMBER = os.getenv("OWNER_PHONE_NUMBER")

# System Config
DATABASE_PATH = os.getenv("DATABASE_PATH", "execution/milo.db")
BASE_URL = os.getenv("BASE_URL", "http://localhost:5000")
POLLING_INTERVAL = 15  # Seconds
LOG_PATH = ".tmp/execution.log"
ENABLE_SENDING = os.getenv("ENABLE_SENDING", "false").lower() == "true"

# OpenAI Config
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = "gpt-4o-mini" # Cost effective, fast
MAX_TOKENS = 150
OPENAI_TIMEOUT = 10 # Seconds

# Initialize Client (Safe)
openai_client = None
if OPENAI_API_KEY:
    try:
        from openai import OpenAI
        openai_client = OpenAI(api_key=OPENAI_API_KEY)
    except ImportError:
        pass # Handle inside specific modules or log warning later

