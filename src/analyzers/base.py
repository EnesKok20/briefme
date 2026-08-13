from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class AnalysisResult:
    """
    Tek bir mesajın analiz sonucu.
    Her analyzer bu objeyi zenginleştirir.
    """
    message_id: str

    # Kategori
    category: str = "uncategorized"
    subcategory: str = ""

    # Duygu analizi
    sentiment: str = "neutral"
    sentiment_score: float = 0.0

    # Öncelik
    priority: str = "normal"
    priority_score: int = 50

    # Tehdit tespiti
    is_threat: bool = False
    threat_type: str = ""
    threat_confidence: float = 0.0

    # Özet
    summary: str = ""
    key_action: str = ""

    # Meta bilgi
    tokens_used: int = 0
    processing_time_ms: float = 0.0
    errors: list[str] = field(default_factory=list)


class BaseAnalyzer(ABC):
    """
    Her analyzer bu sınıfı miras alır.
    Classifier, Sentiment, Threat, Summarizer
    hepsi bu arayüzü kullanır.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @abstractmethod
    async def analyze(self, message_body: str, context: dict = None) -> dict:
        ...