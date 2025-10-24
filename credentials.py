from dotenv import load_dotenv
import os

load_dotenv()
ChatGPT_TOKEN = os.getenv('ai_token',"")
BOT_TOKEN = os.getenv("bot_token","")