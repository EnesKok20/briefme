from pydantic_settings import BaseSettings    #.env dosyasini okumamizi sağlar.
from typing import Literal

class Settings(BaseSettings):
    """uygulama ayarlari.Tüm değerler .env dosyasından okunur"""

    ai_provider: Literal["claude","openai","gemini"] = "gemini"
    anthropic_api_key: str= ""
    apenai_api_key: str=""
    gemini_api_key: str=""

    #Gmail
    enable_gmail: bool = True
    gmail_credentials_path: str = "credentials.json"

    #Linkedin
    enable_linkedin : bool = True

    # Instagram
    enable_instagram: bool = True
    instagram_username: str = ""
    instagram_password: str = ""

    #Telegram Bildirimi
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""


    # Email bildirim
    notification_email: str = ""
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    # Zamanlama
    daily_report_time: str = "18:00"
    timezone: str = "Europe/Istanbul"

        # Veritabani
    database_url: str = "sqlite:///briefme.db"

    # Loglama
    log_level: str = "INFO"
    log_dir: str = "logs"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
    }


def get_settings() -> Settings:
    """Ayarları döndürür. .env dosyasını okur."""
    return Settings()