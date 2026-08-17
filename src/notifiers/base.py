from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class Report:
    """
    Günlük rapor verisi.
    Engine analiz bittikten sonra bu objeyi oluşturur,
    notifier'lara iletir.
    """
    date: str
    total_messages: int
    by_source: dict = field(default_factory=dict)
    by_category: dict = field(default_factory=dict)
    by_sentiment: dict = field(default_factory=dict)
    by_priority: dict = field(default_factory=dict)
    threat_count: int = 0
    critical_items: list = field(default_factory=list)
    opportunities: list = field(default_factory=list)
    # Her mesaj için zenginleştirilmiş özet (category, sentiment, tags,
    # key_action, deadline, response_needed dahil), priority_score'a göre
    # azalan sırada. Hem web raporu hem email bildirimi buradan besleniyor.
    all_items: list = field(default_factory=list)
    summary_html: str = ""
    charts: dict = field(default_factory=dict)


class BaseNotifier(ABC):
    """
    Tüm bildirim göndericilerin base class'ı.
    Telegram, Email, Webhook hepsi bu arayüzü kullanır.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @abstractmethod
    async def send(self, report: Report) -> bool:
        ...