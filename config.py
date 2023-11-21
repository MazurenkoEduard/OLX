import os

from dotenv import load_dotenv

load_dotenv("data/.env")

CREATOR_ID = os.getenv("CREATOR_ID")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
