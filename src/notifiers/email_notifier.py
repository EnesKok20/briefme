import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

from src.notifiers.base import BaseNotifier, Report
from src.core.config import get_settings
from src.utils.logger import get_logger, log_event


SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
]


class EmailNotifier(BaseNotifier):

    def __init__(self):
        self.logger = get_logger("email_notifier")
        self.settings = get_settings()

    @property
    def name(self) -> str:
        return "email"

    async def send(self, report: Report) -> bool:
        self.logger.info("Sending daily report via email...")

        try:
            creds = Credentials.from_authorized_user_file("token.json", SCOPES)
            service = build("gmail", "v1", credentials=creds)

            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"BriefMe — {report.date} | {report.total_messages} mesaj analiz edildi"
            msg["From"] = self.settings.notification_email or self.settings.smtp_user
            msg["To"] = self.settings.notification_email or self.settings.smtp_user

            text_part = MIMEText(self._build_text(report), "plain", "utf-8")
            html_part = MIMEText(self._build_html(report), "html", "utf-8")

            msg.attach(text_part)
            msg.attach(html_part)

            raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
            service.users().messages().send(
                userId="me",
                body={"raw": raw},
            ).execute()

            log_event(self.logger, "REPORT_SENT", {"channel": "email"})
            self.logger.info("Email sent successfully")
            return True

        except Exception as e:
            self.logger.error(f"Failed to send email: {e}")
            return False

    def _build_text(self, report: Report) -> str:
        lines = [
            f"BriefMe - Gunluk Rapor ({report.date})",
            f"Toplam: {report.total_messages} mesaj",
            f"Kritik: {len(report.critical_items)}",
            f"Firsat: {len(report.opportunities)}",
        ]
        for source, count in report.by_source.items():
            lines.append(f"  {source}: {count}")
        return "\n".join(lines)

    def _build_html(self, report: Report) -> str:
        # Stat kartları
        critical_count = len(report.critical_items)
        opportunity_count = len(report.opportunities)
        urgent_count = report.by_sentiment.get("urgent", 0)
        threat_count = sum(1 for _ in report.by_category.items() if _[0] == "threat")

        # Kaynak bar'ları
        source_bars = ""
        total = report.total_messages or 1
        source_colors = {"gmail": "#EA4335", "linkedin": "#0A66C2", "instagram": "#E1306C"}
        for src, count in report.by_source.items():
            pct = int((count / total) * 100)
            color = source_colors.get(src, "#6366F1")
            source_bars += f'''
            <tr>
                <td style="padding:6px 0;color:#94A3B8;font-size:13px;width:90px">{src.upper()}</td>
                <td style="padding:6px 0">
                    <div style="background:#1E293B;border-radius:6px;overflow:hidden;height:24px">
                        <div style="background:{color};height:24px;width:{max(pct,8)}%;border-radius:6px;text-align:right;padding-right:8px;line-height:24px;color:white;font-size:11px;font-weight:600">{count}</div>
                    </div>
                </td>
            </tr>'''

        # Kategori satırları
        cat_icons = {"work": "💼", "personal": "👤", "finance": "💰", "promotion": "📢", "notification": "🔔", "social": "👥", "threat": "⚠️", "uncategorized": "📎"}
        cat_colors = {"work": "#818CF8", "personal": "#34D399", "finance": "#FBBF24", "promotion": "#64748B", "notification": "#60A5FA", "social": "#F472B6", "threat": "#F87171", "uncategorized": "#475569"}
        cat_rows = ""
        for cat, count in sorted(report.by_category.items(), key=lambda x: x[1], reverse=True):
            icon = cat_icons.get(cat, "📎")
            color = cat_colors.get(cat, "#64748B")
            cat_rows += f'''
            <tr>
                <td style="padding:8px 12px;border-bottom:1px solid #1E293B">
                    <span style="font-size:16px">{icon}</span>
                    <span style="color:#E2E8F0;font-size:14px;margin-left:8px">{cat.capitalize()}</span>
                </td>
                <td style="padding:8px 12px;border-bottom:1px solid #1E293B;text-align:right">
                    <span style="background:{color};color:white;padding:3px 12px;border-radius:12px;font-size:12px;font-weight:600">{count}</span>
                </td>
            </tr>'''

        # Duygu satırları
        sent_icons = {"positive": "😊", "negative": "😟", "neutral": "😐", "urgent": "🔥"}
        sent_colors = {"positive": "#34D399", "negative": "#F87171", "neutral": "#64748B", "urgent": "#FBBF24"}
        sent_rows = ""
        for sent, count in report.by_sentiment.items():
            icon = sent_icons.get(sent, "❓")
            color = sent_colors.get(sent, "#64748B")
            sent_rows += f'''
            <td style="text-align:center;padding:12px">
                <div style="font-size:24px;margin-bottom:4px">{icon}</div>
                <div style="font-size:22px;font-weight:800;color:{color}">{count}</div>
                <div style="font-size:11px;color:#64748B;text-transform:uppercase">{sent}</div>
            </td>'''

        # Kritik kartları
        critical_html = ""
        if report.critical_items:
            cards = ""
            for item in report.critical_items:
                cards += f'''
                <tr><td style="padding:8px 0">
                    <div style="background:#1E293B;border-left:3px solid #F87171;border-radius:8px;padding:14px">
                        <div style="color:#E2E8F0;font-weight:600;font-size:14px">{item.get("sender", "?")}</div>
                        <div style="color:#64748B;font-size:12px;margin-top:2px">{item.get("subject", "")}</div>
                        <div style="color:#94A3B8;font-size:13px;margin-top:8px">{item.get("summary", "")}</div>
                    </div>
                </td></tr>'''
            critical_html = f'''
            <tr><td style="padding:24px 32px 0">
                <div style="font-size:16px;font-weight:700;color:#F87171;margin-bottom:12px">🔴 Kritik Mesajlar</div>
                <table width="100%" cellpadding="0" cellspacing="0">{cards}</table>
            </td></tr>'''

        # Fırsat kartları
        opportunity_html = ""
        if report.opportunities:
            cards = ""
            for item in report.opportunities:
                cards += f'''
                <tr><td style="padding:8px 0">
                    <div style="background:#1E293B;border-left:3px solid #34D399;border-radius:8px;padding:14px">
                        <div style="color:#E2E8F0;font-weight:600;font-size:14px">{item.get("sender", "?")}</div>
                        <div style="color:#64748B;font-size:12px;margin-top:2px">{item.get("subject", "")}</div>
                        <div style="color:#94A3B8;font-size:13px;margin-top:8px">{item.get("summary", "")}</div>
                    </div>
                </td></tr>'''
            opportunity_html = f'''
            <tr><td style="padding:24px 32px 0">
                <div style="font-size:16px;font-weight:700;color:#34D399;margin-bottom:12px">🟢 Firsatlar</div>
                <table width="100%" cellpadding="0" cellspacing="0">{cards}</table>
            </td></tr>'''

        return f'''<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#0F172A;font-family:'Segoe UI',Arial,sans-serif">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#0F172A;padding:20px 0">
<tr><td align="center">
<table width="600" cellpadding="0" cellspacing="0" style="background:#0F172A">

    <!-- HEADER -->
    <tr><td style="padding:32px;text-align:center;background:linear-gradient(135deg,#1E2761,#4A6CF7);border-radius:16px 16px 0 0">
        <div style="font-size:28px;font-weight:800;color:white;letter-spacing:1px">BriefMe</div>
        <div style="color:rgba(255,255,255,0.6);font-size:13px;margin-top:6px">Gunluk Iletisim Istihbarat Raporu</div>
        <div style="color:rgba(255,255,255,0.4);font-size:12px;margin-top:4px">{report.date}</div>
    </td></tr>

    <!-- STATS -->
    <tr><td style="padding:24px 32px">
        <table width="100%" cellpadding="0" cellspacing="0">
        <tr>
            <td style="text-align:center;padding:16px;background:#1E293B;border-radius:12px;width:25%">
                <div style="font-size:28px;font-weight:800;color:#E2E8F0">📬 {report.total_messages}</div>
                <div style="font-size:10px;color:#64748B;text-transform:uppercase;margin-top:4px;letter-spacing:1px">Toplam</div>
            </td>
            <td style="width:8px"></td>
            <td style="text-align:center;padding:16px;background:#1E293B;border-radius:12px;width:25%">
                <div style="font-size:28px;font-weight:800;color:#F87171">🚨 {critical_count}</div>
                <div style="font-size:10px;color:#64748B;text-transform:uppercase;margin-top:4px;letter-spacing:1px">Kritik</div>
            </td>
            <td style="width:8px"></td>
            <td style="text-align:center;padding:16px;background:#1E293B;border-radius:12px;width:25%">
                <div style="font-size:28px;font-weight:800;color:#34D399">✨ {opportunity_count}</div>
                <div style="font-size:10px;color:#64748B;text-transform:uppercase;margin-top:4px;letter-spacing:1px">Firsat</div>
            </td>
            <td style="width:8px"></td>
            <td style="text-align:center;padding:16px;background:#1E293B;border-radius:12px;width:25%">
                <div style="font-size:28px;font-weight:800;color:#FBBF24">🔥 {urgent_count}</div>
                <div style="font-size:10px;color:#64748B;text-transform:uppercase;margin-top:4px;letter-spacing:1px">Acil</div>
            </td>
        </tr>
        </table>
    </td></tr>

    <!-- SOURCES -->
    <tr><td style="padding:0 32px 24px">
        <div style="background:#1E293B;border-radius:12px;padding:20px">
            <div style="font-size:14px;font-weight:700;color:#94A3B8;margin-bottom:12px;text-transform:uppercase;letter-spacing:1px">Kaynaklar</div>
            <table width="100%" cellpadding="0" cellspacing="0">{source_bars}</table>
        </div>
    </td></tr>

    <!-- CATEGORIES -->
    <tr><td style="padding:0 32px 24px">
        <div style="background:#1E293B;border-radius:12px;padding:20px">
            <div style="font-size:14px;font-weight:700;color:#94A3B8;margin-bottom:8px;text-transform:uppercase;letter-spacing:1px">Kategoriler</div>
            <table width="100%" cellpadding="0" cellspacing="0">{cat_rows}</table>
        </div>
    </td></tr>

    <!-- SENTIMENT -->
    <tr><td style="padding:0 32px 24px">
        <div style="background:#1E293B;border-radius:12px;padding:20px">
            <div style="font-size:14px;font-weight:700;color:#94A3B8;margin-bottom:8px;text-transform:uppercase;letter-spacing:1px">Duygu Analizi</div>
            <table width="100%" cellpadding="0" cellspacing="0">
            <tr>{sent_rows}</tr>
            </table>
        </div>
    </td></tr>

    <!-- SECURITY -->
    <tr><td style="padding:0 32px 24px">
        <div style="background:#1E293B;border-radius:12px;padding:20px;text-align:center">
            <div style="font-size:36px;margin-bottom:4px">{"✅" if threat_count == 0 else "⚠️"}</div>
            <div style="font-size:14px;color:{"#34D399" if threat_count == 0 else "#F87171"};font-weight:600">{"Tehdit Tespit Edilmedi" if threat_count == 0 else f"{threat_count} Tehdit Tespit Edildi!"}</div>
        </div>
    </td></tr>

    {critical_html}
    {opportunity_html}

    <!-- FOOTER -->
    <tr><td style="padding:32px;text-align:center;border-top:1px solid #1E293B">
        <div style="color:#334155;font-size:11px">BriefMe — AI-Powered Communication Intelligence</div>
        <div style="color:#1E293B;font-size:10px;margin-top:4px">Bu rapor otomatik olusturulmustur</div>
    </td></tr>

</table>
</td></tr>
</table>
</body>
</html>'''