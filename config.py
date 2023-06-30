import os

from dotenv import load_dotenv

load_dotenv("data/.env")

CREATOR_ID = int(os.getenv("CREATOR_ID"))
BOT_TOKEN = os.getenv("BOT_TOKEN")
CLIENT_ID = int(os.getenv("CLIENT_ID"))
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
