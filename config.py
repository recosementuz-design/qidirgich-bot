import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
DATABASE_URL = os.getenv("DATABASE_URL")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN topilmadi")

if not API_ID:
    raise RuntimeError("API_ID topilmadi")

if not API_HASH:
    raise RuntimeError("API_HASH topilmadi")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL topilmadi")

API_ID = int(API_ID)
