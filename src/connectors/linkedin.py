import asyncio
from datetime import datetime, timezone

from linkedin_api import Linkedin

from src.connectors.base import BaseConnector, Message
from src.utils.logger import get_logger, log_event
from src.core.config import get_settings

CONNECT_TIMEOUT_S = 45
FETCH_TIMEOUT_S = 60


class LinkedInConnector(BaseConnector):
    """LinkedIn mesajlarını ve bağlantı isteklerini çeken connector.

    LinkedIn üçüncü taraf uygulamalara kişisel gelen kutusuna resmi bir API
    erişimi vermiyor; bu yüzden `linkedin-api` (LinkedIn'in dahili, dökümante
    edilmemiş Voyager API'sini kullanan, resmi olmayan bir kütüphane)
    kullanılıyor. Bunun sonucunda: (1) LinkedIn'in ToS'unu ihlal etme ve hesap
    kısıtlanma riski var, (2) yanıt alanları LinkedIn tarafında habersizce
    değişebilir — bu yüzden aşağıdaki alan-okuma kodu bilerek savunmacı
    yazıldı (her mesaj/davet kendi try/except'i içinde, tekil hata tüm
    taramayı düşürmez). Hesapta 2FA açıksa giriş genelde bir "challenge" ile
    başarısız olur; bu durum yakalanıp loglanır, pipeline diğer kaynaklarla
    devam eder (bkz. BriefMeEngine._collect).
    """

    def __init__(self):
        self.client = None
        self.logger = get_logger("linkedin")
        self.settings = get_settings()

    @property
    def name(self) -> str:
        return "linkedin"

    def _login(self) -> Linkedin:
        return Linkedin(self.settings.linkedin_email, self.settings.linkedin_password)

    async def connect(self) -> bool:
        self.logger.info("Connecting to LinkedIn...")
        try:
            self.client = await asyncio.wait_for(asyncio.to_thread(self._login), timeout=CONNECT_TIMEOUT_S)
            self.logger.info("LinkedIn connected successfully")
            return True
        except asyncio.TimeoutError:
            self.logger.error(f"LinkedIn girişi {CONNECT_TIMEOUT_S}s içinde tamamlanamadı (muhtemelen 2FA/challenge bekleniyor)")
            return False
        except Exception as e:
            self.logger.error(f"LinkedIn login failed (2FA/challenge tetiklenmiş olabilir): {e}")
            return False

    async def fetch_messages(self, since: datetime) -> list[Message]:
        if not self.client:
            return []

        try:
            dm_messages = await asyncio.wait_for(asyncio.to_thread(self._fetch_conversations, since), timeout=FETCH_TIMEOUT_S)
        except asyncio.TimeoutError:
            self.logger.error("LinkedIn mesaj taraması zaman aşımına uğradı")
            dm_messages = []

        try:
            invitations = await asyncio.wait_for(asyncio.to_thread(self._fetch_invitations), timeout=FETCH_TIMEOUT_S)
        except asyncio.TimeoutError:
            self.logger.error("LinkedIn bağlantı istekleri taraması zaman aşımına uğradı")
            invitations = []

        messages = [*dm_messages, *invitations]

        log_event(self.logger, "FETCH_DONE", {
            "source": "linkedin",
            "count": len(messages),
            "dms": len(dm_messages),
            "invitations": len(invitations),
        })
        return messages

    @staticmethod
    def _typed(container: dict, name_hint: str) -> dict:
        """LinkedIn'in dahili API'si alanları
        'com.linkedin.voyager.messaging.MessagingMember' gibi tam nitelikli
        isimlerle döner; bu isimler versiyona göre değişebildiği için tam
        eşleşme yerine alt string araması yapılıyor."""
        if not isinstance(container, dict):
            return {}
        return next((v for k, v in container.items() if name_hint in k), {})

    def _fetch_conversations(self, since: datetime) -> list[Message]:
        self.logger.info("Fetching LinkedIn messages...")
        messages = []

        try:
            data = self.client.get_conversations()
            elements = data.get("elements", []) if isinstance(data, dict) else []

            for conv in elements:
                try:
                    messages.extend(self._parse_conversation(conv, since))
                except Exception as e:
                    self.logger.error(f"Failed to parse a LinkedIn conversation: {e}")

            self.logger.info(f"Found {len(messages)} LinkedIn messages")

        except Exception as e:
            self.logger.error(f"Failed to fetch LinkedIn conversations: {e}")

        return messages

    def _parse_conversation(self, conv: dict, since: datetime) -> list[Message]:
        out = []
        conv_urn = conv.get("entityUrn", "")
        unread = conv.get("unreadCount", 0)

        for event in conv.get("events", []):
            created_at = event.get("createdAt")
            if not created_at:
                continue

            ts = datetime.fromtimestamp(created_at / 1000, tz=timezone.utc).astimezone().replace(tzinfo=None)
            if ts < since:
                continue

            content = self._typed(event.get("eventContent", {}), "MessageEvent")
            body = content.get("attributedBody", {}).get("text", "")
            if not body:
                continue

            sender_profile = self._typed(event.get("from", {}), "MessagingMember").get("miniProfile", {})
            sender_name = " ".join(filter(None, [sender_profile.get("firstName"), sender_profile.get("lastName")])).strip()
            sender = sender_profile.get("publicIdentifier") or sender_name or "linkedin_user"

            out.append(Message(
                id=f"li_{conv_urn}_{created_at}",
                source="linkedin",
                sender=sender,
                sender_name=sender_name or sender,
                subject="LinkedIn Mesajı",
                body=body,
                timestamp=ts,
                is_read=unread == 0,
                raw_data={"conversation_urn": conv_urn},
            ))
        return out

    def _fetch_invitations(self) -> list[Message]:
        self.logger.info("Fetching LinkedIn connection invitations...")
        messages = []

        try:
            invites = self.client.get_invitations(start=0, limit=20)

            for invite in invites or []:
                try:
                    inviter = invite.get("fromMember") or invite.get("invitee") or {}
                    name = " ".join(filter(None, [inviter.get("firstName"), inviter.get("lastName")])).strip()
                    name = name or "Bilinmeyen kullanıcı"
                    headline = inviter.get("headline", "")

                    messages.append(Message(
                        id=f"li_invite_{invite.get('entityUrn', name)}",
                        source="linkedin",
                        sender=inviter.get("publicIdentifier") or name,
                        sender_name=name,
                        subject="Bağlantı İsteği",
                        body=f"{name} seninle bağlantı kurmak istiyor. {headline}".strip(),
                        timestamp=datetime.now(),
                        raw_data={
                            "type": "invitation",
                            "shared_secret": invite.get("sharedSecret", ""),
                            "entity_urn": invite.get("entityUrn", ""),
                        },
                    ))
                except Exception as e:
                    self.logger.error(f"Failed to parse a LinkedIn invitation: {e}")

            self.logger.info(f"Found {len(messages)} invitations")

        except Exception as e:
            self.logger.error(f"Failed to fetch LinkedIn invitations: {e}")

        return messages

    async def disconnect(self) -> None:
        self.client = None
