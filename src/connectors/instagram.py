from datetime import datetime
from instagrapi import Client

from src.connectors.base import BaseConnector, Message
from src.utils.logger import get_logger, log_event
from src.core.config import get_settings


class InstagramConnector(BaseConnector):

    def __init__(self):
        self.client = None
        self.logger = get_logger("instagram")
        self.settings = get_settings()

    @property
    def name(self) -> str:
        return "instagram"

    async def connect(self) -> bool:
        self.logger.info("Connecting to Instagram...")

        self.client = Client()
        self.client.delay_range = [1, 3]
        self.client.request_timeout = 30

        try:
            self.client.login(
                self.settings.instagram_username,
                self.settings.instagram_password,
            )
            self.logger.info("Instagram connected successfully")
            return True
        except Exception as e:
            self.logger.error(f"Instagram login failed: {e}")
            return False

    async def fetch_messages(self, since: datetime) -> list[Message]:
        messages = []

        dm_messages = self._fetch_dms(since)
        messages.extend(dm_messages)

        follow_requests = self._fetch_follow_requests()
        messages.extend(follow_requests)

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