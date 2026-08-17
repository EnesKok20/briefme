import asyncio
from datetime import datetime
from instagrapi import Client
from instagrapi.exceptions import (
    BadPassword, ChallengeRequired, TwoFactorRequired, ClientLoginRequired,
)

from src.connectors.base import BaseConnector, Message
from src.utils.logger import get_logger, log_event
from src.core.config import get_settings

CONNECT_TIMEOUT_S = 45
FETCH_TIMEOUT_S = 60


class InstagramConnector(BaseConnector):
    """Instagram DM'lerini ve takip isteklerini çeken connector.

    Instagram resmi API'si üçüncü taraf uygulamalara kişisel DM erişimi
    vermediği için `instagrapi` (resmi olmayan, senkron bir kütüphane)
    kullanılıyor. Senkron çağrılar `asyncio.to_thread` ile ayrı bir thread'e
    taşınıp süre sınırına bağlanıyor; aksi halde 2FA/challenge gibi
    yanıt bekleyen bir adımda tüm pipeline süresiz kilitlenebiliyordu.
    """

    def __init__(self):
        self.client = None
        self.logger = get_logger("instagram")
        self.settings = get_settings()

    @property
    def name(self) -> str:
        return "instagram"

    def _login(self) -> None:
        self.client = Client()
        self.client.delay_range = [1, 3]
        self.client.request_timeout = 30
        self.client.login(
            self.settings.instagram_username,
            self.settings.instagram_password,
        )

    async def connect(self) -> bool:
        self.logger.info("Connecting to Instagram...")
        try:
            await asyncio.wait_for(asyncio.to_thread(self._login), timeout=CONNECT_TIMEOUT_S)
            self.logger.info("Instagram connected successfully")
            return True
        except asyncio.TimeoutError:
            self.logger.error(f"Instagram girişi {CONNECT_TIMEOUT_S}s içinde tamamlanamadı (muhtemelen 2FA/challenge bekleniyor)")
            return False
        except TwoFactorRequired:
            self.logger.error("Instagram girişi 2FA doğrulaması istiyor — otomatik girişte desteklenmiyor, hesap ayarlarından 2FA'yı geçici kapatman gerekebilir")
            return False
        except ChallengeRequired:
            self.logger.error("Instagram güvenlik kontrolü (challenge) istedi — Instagram uygulamasından/tarayıcıdan giriş yapıp doğrulamayı tamamla, sonra tekrar dene")
            return False
        except BadPassword:
            self.logger.error("Instagram kullanıcı adı veya şifresi yanlış")
            return False
        except ClientLoginRequired as e:
            self.logger.error(f"Instagram oturumu geçersiz, yeniden giriş gerekiyor: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Instagram login failed: {e}")
            return False

    async def fetch_messages(self, since: datetime) -> list[Message]:
        if not self.client:
            return []

        try:
            dm_messages = await asyncio.wait_for(asyncio.to_thread(self._fetch_dms, since), timeout=FETCH_TIMEOUT_S)
        except asyncio.TimeoutError:
            self.logger.error("Instagram DM taraması zaman aşımına uğradı")
            dm_messages = []

        try:
            follow_requests = await asyncio.wait_for(asyncio.to_thread(self._fetch_follow_requests), timeout=FETCH_TIMEOUT_S)
        except asyncio.TimeoutError:
            self.logger.error("Instagram takip istekleri taraması zaman aşımına uğradı")
            follow_requests = []

        messages = [*dm_messages, *follow_requests]

        log_event(self.logger, "FETCH_DONE", {
            "source": "instagram",
            "count": len(messages),
            "dms": len(dm_messages),
            "follow_requests": len(follow_requests),
        })
        return messages

    def _fetch_dms(self, since: datetime) -> list[Message]:
        self.logger.info("Fetching Instagram DMs...")
        messages = []

        try:
            threads = self.client.direct_threads(amount=20)

            for thread in threads:
                for dm in thread.messages:
                    if dm.timestamp and dm.timestamp >= since:
                        sender = ""
                        sender_name = ""

                        if dm.user_id:
                            try:
                                user = self.client.user_info(dm.user_id)
                                sender = user.username
                                sender_name = user.full_name
                            except Exception:
                                sender = str(dm.user_id)

                        body = ""
                        if dm.text:
                            body = dm.text
                        elif dm.media:
                            body = "[Media paylasildi]"
                        elif dm.reel_share:
                            body = "[Reel paylasildi]"

                        msg = Message(
                            id=str(dm.id),
                            source="instagram",
                            sender=sender,
                            sender_name=sender_name,
                            subject="Instagram DM",
                            body=body,
                            timestamp=dm.timestamp,
                            is_read=dm.is_seen or False,
                            raw_data={"thread_id": str(thread.id)},
                        )
                        messages.append(msg)

            self.logger.info(f"Found {len(messages)} DMs")

        except Exception as e:
            self.logger.error(f"Failed to fetch DMs: {e}")

        return messages

    def _fetch_follow_requests(self) -> list[Message]:
        self.logger.info("Fetching follow requests...")
        messages = []

        try:
            pending = self.client.get_pending_friendships()

            for user_id in pending:
                try:
                    user = self.client.user_info(user_id)
                    msg = Message(
                        id=f"follow_req_{user_id}",
                        source="instagram",
                        sender=user.username,
                        sender_name=user.full_name,
                        subject="Takip Istegi",
                        body=f"{user.full_name} (@{user.username}) seni takip etmek istiyor. Takipci: {user.follower_count}, Gonderi: {user.media_count}",
                        timestamp=datetime.now(),
                        raw_data={
                            "type": "follow_request",
                            "follower_count": user.follower_count,
                            "media_count": user.media_count,
                            "is_verified": user.is_verified,
                        },
                    )
                    messages.append(msg)
                except Exception as e:
                    self.logger.error(f"Failed to get user info for {user_id}: {e}")

            self.logger.info(f"Found {len(messages)} follow requests")

        except Exception as e:
            self.logger.error(f"Failed to fetch follow requests: {e}")

        return messages

    async def disconnect(self) -> None:
        if self.client:
            try:
                self.client.logout()
            except Exception:
                pass