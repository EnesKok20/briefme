import argparse
import asyncio

from src.core.engine import BriefMeEngine
from src.core.config import get_settings
from src.utils.logger import get_logger
from src.connectors.gmail import GmailConnector
from src.analyzers.email_analyzer import EmailAnalyzer
from src.connectors.instagram import InstagramConnector
from src.notifiers.email_notifier import EmailNotifier



def parse_args():
    parser = argparse.ArgumentParser(
        description="BriefMe — AI-Powered Communication Intelligence",
    )
    parser.add_argument(
        "--run-now",
        action="store_true",
        help="Run the pipeline immediately",
    )
    parser.add_argument(
        "--start",
        action="store_true",
        help="Start the daily scheduler",
    )
    parser.add_argument(
        "--dashboard",
        action="store_true",
        help="Launch the web dashboard",
    )
    return parser.parse_args()


async def run_now():
    logger = get_logger("main")
    settings = get_settings()

    logger.info("BriefMe starting (manual run)")
    logger.info(f"AI Provider: {settings.ai_provider}")

    engine = BriefMeEngine()

    engine.add_analyzer(EmailAnalyzer())

    if settings.enable_gmail:
        engine.add_connector(GmailConnector())

    # if settings.enable_instagram:
    #     engine.add_connector(InstagramConnector())

    engine.add_notifier(EmailNotifier())

    if not engine.connectors:
        logger.warning("No connectors configured yet.")
        return

    report = await engine.run()

    # Rapor oluştur
    from src.reporters.builder import ReportBuilder
    builder = ReportBuilder()
    builder.build(report, engine._last_messages, engine._last_results)

    # Bildirimleri gönder
    await engine._notify(report)

    logger.info(f"Done. {report.total_messages} messages processed.")

def main():
    args = parse_args()

    if args.run_now:
        asyncio.run(run_now())
    elif args.start:
        from src.scheduler.jobs import start_scheduler
        start_scheduler()
    elif args.dashboard:
        print("Dashboard mode — coming soon")
    else:
        print("BriefMe — AI-Powered Communication Intelligence")
        print()
        print("Usage:")
        print("  python main.py --run-now      Run pipeline now")
        print("  python main.py --start        Start daily scheduler")
        print("  python main.py --dashboard    Open web dashboard")


if __name__ == "__main__":
    main()