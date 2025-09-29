import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    def __init__(self):
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "")
        self.chat_model = os.getenv("CHAT_MODEL", "gpt-4o-mini")
        self.max_retries = int(os.getenv("MAX_RETRIES", "3"))
        self.port = int(os.getenv("PORT", "5000"))
        self.debug = os.getenv("DEBUG", "True").lower() == "true"


settings = Settings()
