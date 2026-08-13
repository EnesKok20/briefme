import asyncio
from src.core.engine import BriefMeEngine
from src.connectors.gmail import GmailConnector
from src.analyzers.email_analyzer import EmailAnalyzer
from datetime import datetime, timedelta


async def test():
    engine = BriefMeEngine()
    engine.add_connector(GmailConnector())
    engine.add_analyzer(EmailAnalyzer())

    report = await engine.run(since=datetime.now() - timedelta(days=7))

    print(f"\nToplam: {report.total_messages} mesaj")
    print(f"Kaynaklar: {report.by_source}")
    print(f"Kategoriler: {report.by_category}")
    print(f"Duygular: {report.by_sentiment}")
    print(f"Kritik: {len(report.critical_items)}")
    print(f"Firsatlar: {len(report.opportunities)}")


asyncio.run(test())