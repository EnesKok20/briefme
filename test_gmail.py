import asyncio
from src.core.engine import BriefMeEngine
from src.connectors.gmail import GmailConnector
from src.analyzers.email_analyzer import EmailAnalyzer
from src.reporters.builder import ReportBuilder
from datetime import datetime, timedelta


async def test():
    engine = BriefMeEngine()
    engine.add_connector(GmailConnector())
    engine.add_analyzer(EmailAnalyzer())

    report = await engine.run(since=datetime.now() - timedelta(days=7))

    builder = ReportBuilder()
    filepath = builder.build(report, engine._last_messages, engine._last_results)

    print(f"\nRapor oluşturuldu: {filepath}")
    print(f"Tarayıcıda aç ve gör!")


asyncio.run(test())