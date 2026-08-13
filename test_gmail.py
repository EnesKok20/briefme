import asyncio
from datetime import datetime, timedelta
from src.core.engine import BriefMeEngine
from src.connectors.gmail import GmailConnector
from src.analyzers.email_analyzer import EmailAnalyzer
from src.notifiers.email_notifier import EmailNotifier
from src.reporters.builder import ReportBuilder


async def test():
    engine = BriefMeEngine()
    engine.add_connector(GmailConnector())
    engine.add_analyzer(EmailAnalyzer())

    report = await engine.run(since=datetime.now() - timedelta(days=7))

    builder = ReportBuilder()
    builder.build(report, engine._last_messages, engine._last_results)

    notifier = EmailNotifier()
    success = await notifier.send(report)
    print(f"Email gonderildi: {success}")


asyncio.run(test())