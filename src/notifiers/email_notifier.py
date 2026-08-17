import base64
import html
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

from src.notifiers.base import BaseNotifier, Report
from src.reporters.charts import ChartGenerator
from src.core.config import get_settings
from src.utils.logger import get_logger, log_event


SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
]

CAT_ICONS = {"work": "💼", "personal": "👤", "finance": "💰", "promotion": "📢", "notification": "🔔", "social": "👥", "threat": "⚠️", "uncategorized": "📎"}
SENT_ICONS = {"positive": "😊", "negative": "😟", "neutral": "😐", "urgent": "🔥"}
ALL_MESSAGES_LIMIT = 50  # tek e-postanın Gmail'in ~102KB kırpma sınırını aşmaması için güvenlik tavanı


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
            f"Tehdit: {report.threat_count}",
            "",
            "Kaynaklar:",
        ]
        for source, count in report.by_source.items():
            lines.append(f"  {source}: {count}")

        if report.by_priority:
            lines.append("")
            lines.append("Oncelik dagilimi:")
            for p, count in report.by_priority.items():
                lines.append(f"  {p}: {count}")

        if report.critical_items:
            lines.append("")
            lines.append("KRITIK MESAJLAR:")
            for item in report.critical_items:
                lines.append(f"  - {item.get('sender', '?')}: {item.get('subject', '')}")

        return "\n".join(lines)

    # ---------- küçük yapı taşları ----------

    @staticmethod
    def _gmail_link(item: dict) -> str:
        """Gmail kaynaklı bir mesaj için doğrudan Gmail'de açan link üretir.
        message_id, Gmail API'nin verdiği gerçek mesaj id'si — bu URL formatı
        Gmail'in kendi 'View in Gmail' linkleriyle aynı desendir."""
        if item.get("source") != "gmail" or not item.get("message_id"):
            return ""
        return f"https://mail.google.com/mail/u/0/#all/{item['message_id']}"

    def _stat_tile(self, icon: str, value, label: str, color: str, href: str = "") -> str:
        inner = f'''
                <div style="font-size:24px;font-weight:800;color:{color}">{icon} {value}</div>
                <div style="font-size:10px;color:#64748B;text-transform:uppercase;margin-top:4px;letter-spacing:1px">{html.escape(label)}</div>'''
        if href:
            inner = f'<a href="{html.escape(href)}" style="text-decoration:none;display:block">{inner}</a>'
        return f'''
            <td style="text-align:center;padding:16px;background:#1E293B;border-radius:12px">{inner}
            </td>'''

    def _bar_row(self, label: str, count: int, pct: int, color: str, icon: str = "") -> str:
        prefix = f"{icon} " if icon else ""
        return f'''
            <tr>
                <td style="padding:6px 8px 6px 0;color:#94A3B8;font-size:13px;width:120px;white-space:nowrap">{prefix}{html.escape(label)}</td>
                <td style="padding:6px 0">
                    <div style="background:#0F172A;border-radius:6px;overflow:hidden;height:22px">
                        <div style="background:{color};height:22px;width:{max(pct, 6)}%;border-radius:6px;text-align:right;padding-right:8px;line-height:22px;color:white;font-size:11px;font-weight:600">{count}</div>
                    </div>
                </td>
            </tr>'''

    def _priority_bar(self, by_priority: dict) -> str:
        total = sum(by_priority.values()) or 1
        order = [p for p in ["critical", "normal", "low"] if p in by_priority]
        order += [p for p in by_priority if p not in order]

        segments = ""
        legend = ""
        for p in order:
            count = by_priority[p]
            pct = max(round((count / total) * 100), 3)
            color = ChartGenerator.PRIORITY_COLORS.get(p, ChartGenerator.INK_MUTED)
            label = ChartGenerator.PRIORITY_LABELS.get(p, p.capitalize())
            segments += f'<td style="background:{color};width:{pct}%;height:20px;font-size:0">&nbsp;</td>'
            legend += (
                f'<span style="display:inline-block;margin:6px 14px 0 0;font-size:12px;color:#94A3B8">'
                f'<span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:{color};margin-right:5px"></span>'
                f'{html.escape(label)}: {count}</span>'
            )

        bar = f'<table width="100%" cellpadding="0" cellspacing="0" style="border-radius:6px;overflow:hidden"><tr>{segments}</tr></table>'
        return bar, legend

    def _render_email_card(self, item: dict, accent_color: str) -> str:
        sender = html.escape(str(item.get("sender") or "?"))
        subject = html.escape(str(item.get("subject", "")))
        summary = html.escape(str(item.get("summary", "")))
        category = item.get("category") or "uncategorized"
        sentiment = item.get("sentiment") or "neutral"
        cat_color = ChartGenerator.CATEGORY_COLORS.get(category, ChartGenerator.INK_MUTED)
        cat_label = ChartGenerator.CATEGORY_LABELS.get(category, category.capitalize())
        sent_color = ChartGenerator.SENTIMENT_COLORS.get(sentiment, ChartGenerator.INK_MUTED)
        sent_label = ChartGenerator.SENTIMENT_LABELS.get(sentiment, sentiment.capitalize())
        key_action = html.escape(str(item.get("key_action", "") or ""))
        tags = item.get("tags") or []
        deadline = item.get("deadline", "")
        response_needed = item.get("response_needed", False)

        badges = (
            f'<span style="background:{cat_color};color:white;padding:2px 9px;border-radius:10px;font-size:10.5px;font-weight:700;margin-right:4px">{html.escape(cat_label)}</span>'
            f'<span style="background:{sent_color};color:white;padding:2px 9px;border-radius:10px;font-size:10.5px;font-weight:700">{html.escape(sent_label)}</span>'
        )

        action_html = (
            f'<div style="background:rgba(57,135,229,0.12);color:#7ab0f2;padding:6px 10px;border-radius:6px;'
            f'font-size:12px;font-weight:600;margin-top:8px;display:inline-block">→ {key_action}</div>'
            if key_action else ""
        )

        chips = ""
        if response_needed:
            chips += '<span style="background:rgba(250,178,25,0.15);color:#f5c463;padding:2px 9px;border-radius:10px;font-size:10.5px;font-weight:600;margin-right:4px">⏰ Yanıt gerekli</span>'
        if deadline:
            chips += f'<span style="background:rgba(148,163,184,0.12);color:#94A3B8;padding:2px 9px;border-radius:10px;font-size:10.5px;font-weight:600">📅 {html.escape(str(deadline))}</span>'
        chips_html = f'<div style="margin-top:6px">{chips}</div>' if chips else ""

        tags_html = ""
        if tags:
            tag_spans = "".join(
                f'<span style="background:rgba(148,163,184,0.10);color:#64748B;padding:2px 8px;border-radius:10px;font-size:10px;margin-right:4px">{html.escape(str(t))}</span>'
                for t in tags
            )
            tags_html = f'<div style="margin-top:6px">{tag_spans}</div>'

        gmail_url = self._gmail_link(item)
        open_button = (
            f'<a href="{html.escape(gmail_url)}" style="display:inline-block;margin-top:10px;background:{accent_color};'
            f'color:#0F172A;text-decoration:none;font-size:12px;font-weight:700;padding:8px 14px;border-radius:6px">✉ Gmail\'de Aç →</a>'
            if gmail_url else ""
        )

        return f'''
                <tr><td style="padding:8px 0">
                    <div style="background:#1E293B;border-left:3px solid {accent_color};border-radius:8px;padding:14px">
                        <div style="margin-bottom:6px">{badges}</div>
                        <div style="color:#E2E8F0;font-weight:600;font-size:14px">{sender}</div>
                        <div style="color:#64748B;font-size:12px;margin-top:2px">{subject}</div>
                        <div style="color:#94A3B8;font-size:13px;margin-top:8px">{summary}</div>
                        {action_html}
                        {chips_html}
                        {tags_html}
                        <div>{open_button}</div>
                    </div>
                </td></tr>'''

    def _digest_row(self, item: dict) -> str:
        sender = html.escape(str(item.get("sender") or "?"))
        subject = html.escape(str(item.get("subject", "")))
        summary = html.escape(str(item.get("summary", "")))
        category = item.get("category") or "uncategorized"
        priority = item.get("priority") or "normal"
        cat_color = ChartGenerator.CATEGORY_COLORS.get(category, ChartGenerator.INK_MUTED)
        cat_label = ChartGenerator.CATEGORY_LABELS.get(category, category.capitalize())
        pr_color = ChartGenerator.PRIORITY_COLORS.get(priority, ChartGenerator.INK_MUTED)

        gmail_url = self._gmail_link(item)
        open_link = (
            f' · <a href="{html.escape(gmail_url)}" style="color:#7ab0f2;text-decoration:none;font-size:11.5px;font-weight:600">Gmail\'de Aç →</a>'
            if gmail_url else ""
        )

        return f'''
            <tr>
                <td style="padding:10px 0 10px 10px;border-bottom:1px solid #1E293B;border-left:3px solid {pr_color}">
                    <span style="background:{cat_color};color:white;padding:2px 8px;border-radius:8px;font-size:10px;font-weight:700;margin-right:8px">{html.escape(cat_label)}</span>
                    <span style="color:#E2E8F0;font-size:13px;font-weight:600">{sender}</span>
                    <span style="color:#64748B;font-size:12px"> — {subject}</span>
                    <div style="color:#94A3B8;font-size:12.5px;margin-top:3px">{summary}{open_link}</div>
                </td>
            </tr>'''

    # ---------- ana şablon ----------

    def _build_html(self, report: Report) -> str:
        critical_count = len(report.critical_items)
        opportunity_count = len(report.opportunities)
        urgent_count = report.by_sentiment.get("urgent", 0)
        threat_count = report.threat_count

        # Kaynak bar'ları
        total = report.total_messages or 1
        source_bars = "".join(
            self._bar_row(src.upper(), count, int((count / total) * 100), ChartGenerator.SOURCE_COLORS.get(src, ChartGenerator.INK_MUTED))
            for src, count in report.by_source.items()
        )

        # Kategori bar'ları (rozet yerine görsel yüzde çubuğu — kaynak bloğuyla tutarlı)
        cat_rows = "".join(
            self._bar_row(
                ChartGenerator.CATEGORY_LABELS.get(cat, cat.capitalize()), count,
                int((count / total) * 100), ChartGenerator.CATEGORY_COLORS.get(cat, ChartGenerator.INK_MUTED),
                icon=CAT_ICONS.get(cat, "📎"),
            )
            for cat, count in sorted(report.by_category.items(), key=lambda x: x[1], reverse=True)
        )

        # Öncelik dağılımı (tek segmentli bar + lejant)
        priority_html = ""
        if report.by_priority:
            bar, legend = self._priority_bar(report.by_priority)
            priority_html = f'''
    <tr><td style="padding:0 32px 24px">
        <div style="background:#1E293B;border-radius:12px;padding:20px">
            <div style="font-size:14px;font-weight:700;color:#94A3B8;margin-bottom:12px;text-transform:uppercase;letter-spacing:1px">Öncelik Dağılımı</div>
            {bar}
            <div style="margin-top:10px">{legend}</div>
        </div>
    </td></tr>'''

        # Duygu satırları
        sent_rows = ""
        for sent, count in report.by_sentiment.items():
            icon = SENT_ICONS.get(sent, "❓")
            color = ChartGenerator.SENTIMENT_COLORS.get(sent, ChartGenerator.INK_MUTED)
            label = ChartGenerator.SENTIMENT_LABELS.get(sent, sent.capitalize())
            sent_rows += f'''
            <td style="text-align:center;padding:12px">
                <div style="font-size:24px;margin-bottom:4px">{icon}</div>
                <div style="font-size:22px;font-weight:800;color:{color}">{count}</div>
                <div style="font-size:11px;color:#64748B;text-transform:uppercase">{html.escape(label)}</div>
            </td>'''

        # Üstte dikkat çeken aksiyon şeridi: kritik mesaj varsa, e-postayı
        # açar açmaz "aşağıda seni bekleyen bir şey var" mesajı versin.
        action_banner = ""
        if critical_count > 0:
            action_banner = f'''
    <tr><td style="padding:16px 32px 0">
        <a href="#kritik-mesajlar" style="display:block;text-decoration:none;background:rgba(208,59,59,0.15);border:1px solid {ChartGenerator.STATUS_COLORS['critical']};border-radius:10px;padding:14px 16px;text-align:center">
            <span style="color:#f28b8b;font-size:14px;font-weight:700">⚡ {critical_count} kritik mesaj yanıt bekliyor — aşağıda incele ↓</span>
        </a>
    </td></tr>'''

        # Kritik kartları
        critical_html = ""
        if report.critical_items:
            cards = "".join(self._render_email_card(item, ChartGenerator.STATUS_COLORS['critical']) for item in report.critical_items)
            critical_html = f'''
    <tr><td id="kritik-mesajlar" style="padding:24px 32px 0">
        <div style="font-size:16px;font-weight:700;color:{ChartGenerator.STATUS_COLORS['critical']};margin-bottom:12px">🔴 Kritik Mesajlar</div>
        <table width="100%" cellpadding="0" cellspacing="0">{cards}</table>
    </td></tr>'''

        # Fırsat kartları
        opportunity_html = ""
        if report.opportunities:
            cards = "".join(self._render_email_card(item, ChartGenerator.STATUS_COLORS['good']) for item in report.opportunities)
            opportunity_html = f'''
    <tr><td id="firsatlar" style="padding:24px 32px 0">
        <div style="font-size:16px;font-weight:700;color:{ChartGenerator.STATUS_COLORS['good']};margin-bottom:12px">🟢 Fırsatlar</div>
        <table width="100%" cellpadding="0" cellspacing="0">{cards}</table>
    </td></tr>'''

        # Tüm mesajlar: "Toplam" rakamının arkasında gerçekte ne olduğunu
        # görebilmek için günün TÜM mesajları (kritik/fırsat dahil, tekrar
        # kompakt biçimde) önceliğe göre sıralı tek liste halinde.
        all_html = ""
        if report.all_items:
            shown = report.all_items[:ALL_MESSAGES_LIMIT]
            rows = "".join(self._digest_row(item) for item in shown)
            overflow_note = ""
            if len(report.all_items) > ALL_MESSAGES_LIMIT:
                overflow_note = (
                    f'<div style="color:#64748B;font-size:11.5px;margin-top:10px;text-align:center">'
                    f'+ {len(report.all_items) - ALL_MESSAGES_LIMIT} mesaj daha — tam liste için web raporuna bak</div>'
                )
            all_html = f'''
    <tr><td id="tum-mesajlar" style="padding:24px 32px 0">
        <div style="font-size:16px;font-weight:700;color:#E2E8F0;margin-bottom:4px">📋 Tüm Mesajlar ({report.total_messages})</div>
        <div style="font-size:12px;color:#64748B;margin-bottom:12px">Önceliğe göre sıralı — en önemli en üstte</div>
        <table width="100%" cellpadding="0" cellspacing="0">{rows}</table>
        {overflow_note}
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
        <div style="color:rgba(255,255,255,0.6);font-size:13px;margin-top:6px">Günlük İletişim İstihbarat Raporu</div>
        <div style="color:rgba(255,255,255,0.4);font-size:12px;margin-top:4px">{html.escape(str(report.date))}</div>
    </td></tr>

    <!-- STATS (her kutu ilgili bölüme atlar) -->
    <tr><td style="padding:24px 32px 8px">
        <table width="100%" cellpadding="0" cellspacing="0">
        <tr>
            {self._stat_tile("📨", report.total_messages, "Toplam", "#E2E8F0", href="#tum-mesajlar")}
            <td style="width:8px"></td>
            {self._stat_tile("🚨", critical_count, "Kritik", ChartGenerator.STATUS_COLORS['critical'], href="#kritik-mesajlar" if critical_count else "")}
            <td style="width:8px"></td>
            {self._stat_tile("✨", opportunity_count, "Fırsat", ChartGenerator.STATUS_COLORS['good'], href="#firsatlar" if opportunity_count else "")}
        </tr>
        </table>
    </td></tr>
    <tr><td style="padding:8px 32px 24px">
        <table width="100%" cellpadding="0" cellspacing="0">
        <tr>
            {self._stat_tile("🔥", urgent_count, "Acil", ChartGenerator.STATUS_COLORS['warning'], href="#duygu-analizi")}
            <td style="width:8px"></td>
            {self._stat_tile("🛡️", threat_count, "Tehdit", ChartGenerator.STATUS_COLORS['serious'] if threat_count else ChartGenerator.STATUS_COLORS['good'], href="#guvenlik-durumu")}
            <td style="width:8px"></td>
            <td></td>
        </tr>
        </table>
    </td></tr>

    {action_banner}

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
            <div style="font-size:14px;font-weight:700;color:#94A3B8;margin-bottom:12px;text-transform:uppercase;letter-spacing:1px">Kategoriler</div>
            <table width="100%" cellpadding="0" cellspacing="0">{cat_rows}</table>
        </div>
    </td></tr>

    {priority_html}

    <!-- SENTIMENT -->
    <tr><td id="duygu-analizi" style="padding:0 32px 24px">
        <div style="background:#1E293B;border-radius:12px;padding:20px">
            <div style="font-size:14px;font-weight:700;color:#94A3B8;margin-bottom:8px;text-transform:uppercase;letter-spacing:1px">Duygu Analizi</div>
            <table width="100%" cellpadding="0" cellspacing="0">
            <tr>{sent_rows}</tr>
            </table>
        </div>
    </td></tr>

    <!-- SECURITY -->
    <tr><td id="guvenlik-durumu" style="padding:0 32px 24px">
        <div style="background:#1E293B;border-radius:12px;padding:20px;text-align:center">
            <div style="font-size:36px;margin-bottom:4px">{"✅" if threat_count == 0 else "⚠️"}</div>
            <div style="font-size:14px;color:{ChartGenerator.STATUS_COLORS['good'] if threat_count == 0 else ChartGenerator.STATUS_COLORS['critical']};font-weight:600">{"Tehdit Tespit Edilmedi" if threat_count == 0 else f"{threat_count} Tehdit Tespit Edildi!"}</div>
        </div>
    </td></tr>

    {critical_html}
    {opportunity_html}
    {all_html}

    <!-- FOOTER -->
    <tr><td style="padding:32px;text-align:center;border-top:1px solid #1E293B">
        <div style="color:#334155;font-size:11px">BriefMe — AI-Powered Communication Intelligence</div>
        <div style="color:#1E293B;font-size:10px;margin-top:4px">Bu rapor otomatik oluşturulmuştur</div>
    </td></tr>

</table>
</td></tr>
</table>
</body>
</html>'''
