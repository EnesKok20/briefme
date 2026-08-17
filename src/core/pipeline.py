from typing import Optional

from src.core.engine import BriefMeEngine
from src.core.config import Settings, get_settings, ConfigError
from src.connectors.gmail import GmailConnector
from src.connectors.instagram import InstagramConnector
from src.connectors.linkedin import LinkedInConnector
from src.analyzers.email_analyzer import EmailAnalyzer
from src.notifiers.email_notifier import EmailNotifier
from src.utils.logger import get_logger


def build_engine(settings: Optional[Settings] = None) -> BriefMeEngine:
    """Ayarlara göre connector/analyzer/notifier'ları kayıtlı bir BriefMeEngine
    döner. `main.py` (--run-now) ve `scheduler/jobs.py` (--start) aynı kurulum
    mantığını buradan paylaşır; böylece yeni bir connector eklendiğinde tek
    yerden devreye alınır, birinde unutulup diğerinde kalmaz."""
    settings = settings or get_settings()
    logger = get_logger("pipeline")

    # EmailAnalyzer'ın Gemini client'ı, key boşsa __init__ sırasında ham bir
    # ValueError fırlatıyor — burada erkenden, anlaşılır bir mesajla yakalıyoruz.
    if settings.ai_provider == "gemini" and not settings.gemini_api_key:
        raise ConfigError(
            "GEMINI_API_KEY .env dosyasında tanımlı değil. "
            ".env dosyasına GEMINI_API_KEY=... satırını ekleyip tekrar dene."
        )

    engine = BriefMeEngine()

    engine.add_analyzer(EmailAnalyzer())

    if settings.enable_gmail:
        engine.add_connector(GmailConnector())
    if settings.enable_instagram:
        engine.add_connector(InstagramConnector())
    if settings.enable_linkedin:
        engine.add_connector(LinkedInConnector())

    if settings.notification_email or settings.smtp_user:
        engine.add_notifier(EmailNotifier())
    else:
        logger.warning("No notification email configured — report will be built but not sent.")

    return engine
