import asyncio
from datetime import datetime, timedelta
from typing import Optional

from src.connectors.base import BaseConnector, Message
from src.analyzers.base import BaseAnalyzer, AnalysisResult
from src.notifiers.base import BaseNotifier, Report
from src.utils.logger import get_logger, log_event


class BriefMeEngine:
    """
    Ana motor. Tüm pipeline'ı yönetir:
    Collect → Analyze → Report → Notify
    """

    def __init__(self):
        self.connectors: list[BaseConnector] = []
        self.analyzers: list[BaseAnalyzer] = []
        self.notifiers: list[BaseNotifier] = []
        self.logger = get_logger("engine")

    def add_connector(self, connector: BaseConnector) -> None:
        self.connectors.append(connector)
        self.logger.info(f"Connector registered: {connector.name}")

    def add_analyzer(self, analyzer: BaseAnalyzer) -> None:
        self.analyzers.append(analyzer)
        self.logger.info(f"Analyzer registered: {analyzer.name}")

    def add_notifier(self, notifier: BaseNotifier) -> None:
        self.notifiers.append(notifier)
        self.logger.info(f"Notifier registered: {notifier.name}")

    async def run(self, since: Optional[datetime] = None) -> Report:
        if since is None:
            since = datetime.now() - timedelta(hours=24)

        self.logger.info("=" * 50)
        self.logger.info("BriefMe pipeline starting")
        log_event(self.logger, "PIPELINE_START", {"since": since.isoformat()})

        all_messages = await self._collect(since)
        results = await self._analyze(all_messages)
        report = self._build_report(all_messages, results)
        await self._notify(report)

        log_event(self.logger, "PIPELINE_DONE", {
            "total_messages": len(all_messages),
        })
        return report

    async def _collect(self, since: datetime) -> list[Message]:
        all_messages = []

        for connector in self.connectors:
            try:
                self.logger.info(f"Fetching from {connector.name}...")
                await connector.connect()
                messages = await connector.fetch_messages(since)
                all_messages.extend(messages)
                log_event(self.logger, "FETCH_DONE", {
                    "source": connector.name,
                    "count": len(messages),
                })
            except Exception as e:
                self.logger.error(f"{connector.name} failed: {e}")
            finally:
                await connector.disconnect()

        self.logger.info(f"Total messages collected: {len(all_messages)}")
        return all_messages

    async def _analyze(self, messages: list[Message]) -> list[AnalysisResult]:
        results = []

        for i, msg in enumerate(messages, 1):
            result = AnalysisResult(message_id=msg.id)

            for analyzer in self.analyzers:
                try:
                    analysis = await analyzer.analyze(
                        message_body=msg.body,
                        context={
                            "sender": msg.sender,
                            "subject": msg.subject,
                            "source": msg.source,
                        },
                    )
                    for key, value in analysis.items():
                        if hasattr(result, key):
                            setattr(result, key, value)
                except Exception as e:
                    self.logger.error(f"{analyzer.name} failed on {msg.id}: {e}")
                    result.errors.append(f"{analyzer.name}: {str(e)}")

            results.append(result)

            if i % 25 == 0:
                self.logger.info(f"Analyzed {i}/{len(messages)} messages")

        self.logger.info(f"Analysis complete: {len(results)} messages")
        return results

    def _build_report(self, messages: list[Message], results: list[AnalysisResult]) -> Report:
        by_source = {}
        by_category = {}
        by_sentiment = {}
        critical_items = []
        opportunities = []

        for msg, result in zip(messages, results):
            by_source[msg.source] = by_source.get(msg.source, 0) + 1
            by_category[result.category] = by_category.get(result.category, 0) + 1
            by_sentiment[result.sentiment] = by_sentiment.get(result.sentiment, 0) + 1

            if result.priority == "critical":
                critical_items.append({
                    "source": msg.source,
                    "sender": msg.sender_name or msg.sender,
                    "subject": msg.subject,
                    "summary": result.summary,
                })

            if result.sentiment == "positive" and result.priority_score > 60:
                opportunities.append({
                    "source": msg.source,
                    "sender": msg.sender_name or msg.sender,
                    "subject": msg.subject,
                    "summary": result.summary,
                })

        report = Report(
            date=datetime.now().strftime("%Y-%m-%d"),
            total_messages=len(messages),
            by_source=by_source,
            by_category=by_category,
            by_sentiment=by_sentiment,
            critical_items=critical_items,
            opportunities=opportunities,
        )

        self.logger.info(
            f"Report: {report.total_messages} messages, "
            f"{len(critical_items)} critical, "
            f"{len(opportunities)} opportunities"
        )
        return report

    async def _notify(self, report: Report) -> None:
        for notifier in self.notifiers:
            try:
                success = await notifier.send(report)
                if success:
                    log_event(self.logger, "REPORT_SENT", {"channel": notifier.name})
                else:
                    self.logger.warning(f"{notifier.name} returned False")
            except Exception as e:
                self.logger.error(f"{notifier.name} failed: {e}")