import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DATABASE_URL = "sqlite+aiosqlite:///bot.db"
DEBUG = os.getenv("DEBUG",0)


PRICING = {
    "gpt-4-turbo": {"input": 0.01 / 1000, "output": 0.03 / 1000},  # $0.01 per 1K input tokens, $0.03 per 1K output tokens
    "gpt-3.5-turbo": {"input": 0.002 / 1000, "output": 0.004 / 1000},  # $0.002 per 1K input tokens
    "whisper-1": {"audio": 0.006 / 60},  # $0.006 per minute of audio
    "tts-1": {"audio": 0.015 / 1000},  # Example: $0.015 per 1K characters
}