import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.environ["BOT_TOKEN"]
API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
DATABASE_URL = os.environ["DATABASE_URL"]
STRING_SESSION = os.environ.get("STRING_SESSION", "").strip()
ADMIN_TELEGRAM_ID = int(os.environ["ADMIN_TELEGRAM_ID"])
