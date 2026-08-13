import argparse
import asyncio

from src.core.engine import BriefMeEngine
from src.core.config import get_settings
from src.utils.logger import get_logger


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

    # TODO: Connector'lar eklenecek
    # engine.add_connector(GmailConnector())
    # engine.add_connector(LinkedInConnector())
    # engine.add_connector(InstagramConnector())

    # TODO: Analyzer'lar eklenecek
    # engine.add_analyzer(ClassifierAnalyzer())
    # engine.add_analyzer(SentimentAnalyzer())

    # TODO: Notifier'lar eklenecek
    # engine.add_notifier(TelegramNotifier())
    # engine.add_notifier(EmailNotifier())

    if not engine.connectors:
        logger.warning("No connectors configured yet.")
        logger.info("Next step: implement Gmail connector.")
        return

    report = await engine.run()
    logger.info(f"Done. {report.total_messages} messages processed.")


def main():
    args = parse_args()

    if args.run_now:
        asyncio.run(run_now())
    elif args.start:
        print("Scheduler mode — coming soon")
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