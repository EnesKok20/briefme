import os
import base64
from datetime import datetime
from email.utils import parsedate_to_datetime

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from src.connectors.base import BaseConnector, Message
from src.utils.logger import get_logger, log_event
from src.core.config import get_settings

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
]

class GmailConnector(BaseConnector):

    def __init__(self):
        self.service = None
        self.creds = None
        self.logger = get_logger("gmail")
        self.settings = get_settings()

    @property
    def name(self) -> str:
        return "gmail"

    async def connect(self) -> bool:
        self.logger.info("Connecting to Gmail...")

        creds = None
        token_path = "token.json"
        creds_path = self.settings.gmail_credentials_path

        # Daha önce giriş yapıldıysa token'ı oku
        if os.path.exists(token_path):
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)

        # Token yoksa veya süresi dolmuşsa yenile
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
                creds = flow.run_local_server(port=0)

            # Token'ı kaydet (bir dahakine tekrar giriş yapma)
            with open(token_path, "w") as token:
                token.write(creds.to_json())

        self.creds = creds
        self.service = build("gmail", "v1", credentials=creds)
        self.logger.info("Gmail connected successfully")
        return True

    async def fetch_messages(self, since: datetime) -> list[Message]:
        self.logger.info(f"Fetching emails since {since.isoformat()}")

        since_str = since.strftime("%Y/%m/%d")
        query = f"after:{since_str}"

        messages = []
        results = self.service.users().messages().list(
            userId="me", q=query, maxResults=100
        ).execute()

        raw_messages = results.get("messages", [])
        self.logger.info(f"Found {len(raw_messages)} emails")

        for raw in raw_messages:
            try:
                msg_data = self.service.users().messages().get(
                    userId="me", id=raw["id"], format="full"
                ).execute()

                headers = {
                    h["name"].lower(): h["value"]
                    for h in msg_data.get("payload", {}).get("headers", [])
                }

                body = self._extract_body(msg_data)

                msg = Message(
                    id=raw["id"],
                    source="gmail",
                    sender=headers.get("from", ""),
                    sender_name=self._parse_sender_name(headers.get("from", "")),
                    subject=headers.get("subject", "(No subject)"),
                    body=body,
                    timestamp=self._parse_date(headers.get("date", "")),
                    is_read="UNREAD" not in msg_data.get("labelIds", []),
                    has_attachments=self._has_attachments(msg_data),
                    labels=msg_data.get("labelIds", []),
                    raw_data={"snippet": msg_data.get("snippet", "")},
                )
                messages.append(msg)

            except Exception as e:
                self.logger.error(f"Failed to parse email {raw['id']}: {e}")

        log_event(self.logger, "FETCH_DONE", {
            "source": "gmail",
            "count": len(messages),
        })
        return messages

    def _extract_body(self, msg_data: dict) -> str:
        """Email gövdesini çıkar. Ekli dosyası olan mailler genelde
        multipart/mixed içine multipart/alternative gömer, bu yüzden
        parçalar iç içe geçebilir — düz (tek seviye) tarama bu durumda
        gövdeyi kaçırıp snippet'e düşerdi, o yüzden recursive tarıyoruz."""
        payload = msg_data.get("payload", {})

        if "body" in payload and payload["body"].get("data"):
            return self._decode_part(payload["body"]["data"])

        plain = self._find_part(payload, "text/plain")
        if plain:
            return plain

        html_body = self._find_part(payload, "text/html")
        if html_body:
            return html_body

        return msg_data.get("snippet", "")

    def _find_part(self, payload: dict, mime_type: str) -> str:
        """Verilen mime type'a sahip ilk parçayı, iç içe multipart'lar
        dahil olmak üzere derinlemesine arar."""
        for part in payload.get("parts", []):
            if part.get("mimeType") == mime_type:
                data = part.get("body", {}).get("data", "")
                if data:
                    return self._decode_part(data)
            if part.get("parts"):
                nested = self._find_part(part, mime_type)
                if nested:
                    return nested
        return ""

    @staticmethod
    def _decode_part(data: str) -> str:
        try:
            return base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
        except Exception:
            return ""

    def _parse_sender_name(self, from_header: str) -> str:
        """'Enes Kok <enes@mail.com>' -> 'Enes Kok'"""
        if "<" in from_header:
            return from_header.split("<")[0].strip().strip('"')
        return from_header

    def _parse_date(self, date_str: str) -> datetime:
        """Email tarih header'ını datetime'a çevir. `parsedate_to_datetime`
        header'da saat dilimi varsa (neredeyse her zaman) timezone-aware bir
        datetime döner; sistemin geri kalanı (Message.timestamp default'u,
        diğer connector'lar) naive datetime kullanıyor, o yüzden yerel saate
        çevirip tzinfo'yu düşürüyoruz — aksi halde ileride naive/aware
        datetime karşılaştırması sessizce TypeError patlatabilir."""
        try:
            parsed = parsedate_to_datetime(date_str)
            if parsed.tzinfo is not None:
                parsed = parsed.astimezone().replace(tzinfo=None)
            return parsed
        except Exception:
            return datetime.now()

    def _has_attachments(self, msg_data: dict) -> bool:
        """Ek dosya var mı kontrol et."""
        parts = msg_data.get("payload", {}).get("parts", [])
        for part in parts:
            if part.get("filename"):
                return True
        return False