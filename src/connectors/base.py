from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Message:
    """
    Herhangi bir platformdan gelen tek bir mesaj.
    Gmail maili de olabilir, LinkedIn mesajı da, Instagram DM'i de.
    Hepsi bu formata dönüşür.
    """
    id: str
    source: str                    # "gmail" | "linkedin" | "instagram"
    sender: str
    sender_name: str = ""
    subject: str = ""
    body: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    is_read: bool = False
    has_attachments: bool = False
    labels: list[str] = field(default_factory=list)
    raw_data: dict = field(default_factory=dict)

    def preview(self, max_len: int = 100) -> str:
        """İçeriğin kısa önizlemesi."""
        text = self.body[:max_len]
        return f"{text}..." if len(self.body) > max_len else text


class BaseConnector(ABC):
    """
    Tüm connector'ların base class'ı.
    Yeni platform eklemek için:
        1. Bu class'ı inherit et
        2. connect() ve fetch_messages() yaz
        3. Engine'e kaydet
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Connector adı: 'gmail', 'linkedin', 'instagram'"""
        ...

    @abstractmethod
    async def connect(self) -> bool:
        """Platforma bağlan. OAuth, API key vs."""
        ...

    @abstractmethod
    async def fetch_messages(self, since: datetime) -> list[Message]:
        """Belirtilen tarihten sonraki mesajları çek."""
        ...

    async def disconnect(self) -> None:
        """Bağlantıyı kapat. Override opsiyonel."""
        pass