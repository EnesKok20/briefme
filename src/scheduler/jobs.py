from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, timedelta
import asyncio

from src.core.engine import BriefMeEngine
from src.connectors.gmail import GmailConnector
from src.analyzers.email_analyzer import EmailAnalyzer
from src.notifiers.email_notifier import EmailNotifier
from src.reporters.builder import ReportBuilder
from src.core.config import get_settings
from src.utils.logger import get_logger


async def daily_briefing():
    """Her gün belirlenen saatte çalışan ana görev."""
    logger = get_logger("scheduler")
    logger.info("=" * 50)
    logger.info("Daily briefing started")

    try:
        engine = BriefMeEngine()
        settings = get_settings()

        engine.add_connector(GmailConnector())
        engine.add_analyzer(EmailAnalyzer())
        engine.add_notifier(EmailNotifier())

        report = await engine.run()

        builder = ReportBuilder()
        builder.build(report, engine._last_messages, engine._last_results)

        await engine._notify(report)

        logger.info(f"Daily briefing complete: {report.total_messages} messages")

    except Exception as e:
        logger.error(f"Daily briefing failed: {e}")


def start_scheduler():
    """Scheduler'ı başlat."""
    logger = get_logger("scheduler")
    settings = get_settings()

    hour, minute = settings.daily_report_time.split(":")

    async def run():
        scheduler = AsyncIOScheduler(timezone=settings.timezone)

        scheduler.add_job(
            daily_briefing,
            trigger=CronTrigger(hour=int(hour), minute=int(minute)),
            id="daily_briefing",
            name="BriefMe Daily Briefing",
            replace_existing=True,
        )

        scheduler.start()

        logger.info(f"Scheduler started. Daily briefing at {settings.daily_report_time} ({settings.timezone})")
        logger.info("Press Ctrl+C to stop")

        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("Scheduler stopped")
            scheduler.shutdown()

    asyncio.run(run())