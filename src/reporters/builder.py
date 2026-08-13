from datetime import datetime
import html
from pathlib import Path
from typing import Any, List, Optional

from src.notifiers.base import Report
from src.reporters.charts import ChartGenerator
from src.utils.logger import get_logger


SOURCE_ICONS = {"gmail": "✉", "linkedin": "in", "instagram": "◎"}
CATEGORY_LABELS = ChartGenerator.CATEGORY_LABELS
SENTIMENT_LABELS = ChartGenerator.SENTIMENT_LABELS
PRIORITY_LABELS = ChartGenerator.PRIORITY_LABELS


class ReportBuilder:
    """BriefMe günlük HTML raporlarını modern, koyu temalı ve duyarlı
    (responsive) bir arayüzle oluşturan ve dosyalayan servis sınıfı.
    """

    def __init__(self, output_dir: str = "reports") -> None:
        self.logger = get_logger("reporter")
        self.charts = ChartGenerator()
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def build(self, report: Report, messages: Optional[List[Any]] = None, results: Optional[List[Any]] = None) -> str:
        """Rapor verilerini ve grafikleri birleştirerek şık bir HTML raporu üretir."""
        self.logger.info("Günlük rapor oluşturuluyor...")

        source_chart = self.charts.source_pie(report.by_source)
        category_chart = self.charts.category_bar(report.by_category)
        sentiment_gauge = self.charts.sentiment_gauge(report.by_sentiment)
        sentiment_chart = self.charts.sentiment_breakdown(report.by_sentiment)
        priority_chart = self.charts.priority_donut(results or [])
        threat_chart = self.charts.threat_summary(results or [])

        critical_html = self._build_section(report.critical_items, "critical")
        opportunity_html = self._build_section(report.opportunities, "opportunity")

        message_cards = ""
        if messages and results:
            message_cards = self._build_message_cards(messages, results)

        threat_count = sum(1 for r in (results or []) if getattr(r, "is_threat", False))

        html_content = self._get_html_template(
            report=report,
            threat_count=threat_count,
            source_chart=source_chart,
            category_chart=category_chart,
            sentiment_gauge=sentiment_gauge,
            sentiment_chart=sentiment_chart,
            priority_chart=priority_chart,
            threat_chart=threat_chart,
            critical_html=critical_html,
            opportunity_html=opportunity_html,
            message_cards=message_cards,
        )

        filename = f"briefme_{report.date}.html"
        filepath = self.output_dir / filename
        filepath.write_text(html_content, encoding="utf-8")
        self.logger.info(f"Rapor kaydedildi: {filepath}")

        report.summary_html = html_content
        return str(filepath)

    def _source_dot(self, source: str) -> str:
        color = ChartGenerator.SOURCE_COLORS.get(source, ChartGenerator.INK_MUTED)
        icon = SOURCE_ICONS.get(source, "•")
        return f'<span class="source-dot" style="--dot:{color}" title="{html.escape(source.capitalize())}">{icon}</span>'

    def _build_section(self, items: List[dict], section_type: str) -> str:
        """Kritik veya fırsat öğeleri için özel bölüm kartları oluşturur."""
        if not items:
            return ""

        icons = {"critical": "🔴", "opportunity": "🟢"}
        titles = {"critical": "Kritik & Acil", "opportunity": "Fırsatlar & Güzel Haberler"}
        anchors = {"critical": "critical", "opportunity": "opportunities"}

        cards = ""
        for item in items:
            source = html.escape(item.get("source", ""))
            sender = html.escape(item.get("sender", "Bilinmeyen"))
            subject = html.escape(item.get("subject", ""))
            summary = html.escape(item.get("summary", ""))

            cards += f"""
            <div class="message-card {section_type}">
                <div class="card-top">
                    {self._source_dot(item.get("source", ""))}
                    <span class="badge {source}">{CATEGORY_LABELS.get(source, source.capitalize())}</span>
                </div>
                <div class="sender">{sender}</div>
                <div class="subject">{subject}</div>
                <div class="summary">{summary}</div>
            </div>"""

        return f"""
        <section class="section" id="{anchors.get(section_type, '')}">
            <h2>{icons.get(section_type, '')} {titles.get(section_type, '')}<span class="count-pill">{len(items)}</span></h2>
            <div class="card-list">{cards}</div>
        </section>"""

    def _build_message_cards(self, messages: List[Any], results: List[Any]) -> str:
        """Tüm mesajlar için filtrelenebilir, detaylı kartlar üretir."""
        cards = ""
        for msg, result in zip(messages, results):
            category = getattr(result, "category", "uncategorized") or "uncategorized"
            sentiment = getattr(result, "sentiment", "neutral") or "neutral"
            priority = getattr(result, "priority", "normal") or "normal"
            source = getattr(msg, "source", "")
            is_threat = getattr(result, "is_threat", False)
            response_needed = getattr(result, "response_needed", False)
            deadline = getattr(result, "deadline", "")
            summary = html.escape(getattr(result, "summary", ""))
            key_action = html.escape(getattr(result, "key_action", ""))
            tags = getattr(result, "tags", [])

            tag_html = ""
            if tags:
                tag_html = '<div class="tags">' + "".join(
                    f'<span class="tag">{html.escape(str(t))}</span>' for t in tags
                ) + "</div>"

            action_html = ""
            if key_action:
                action_html = f'<div class="action">→ {key_action}</div>'

            meta_chips = ""
            if is_threat:
                meta_chips += '<span class="chip chip-threat">⚠ Tehdit tespit edildi</span>'
            if response_needed:
                meta_chips += '<span class="chip chip-response">⏰ Yanıt gerekli</span>'
            if deadline:
                meta_chips += f'<span class="chip chip-deadline">📅 {html.escape(str(deadline))}</span>'
            meta_html = f'<div class="meta-chips">{meta_chips}</div>' if meta_chips else ""

            sender_name = html.escape(getattr(msg, "sender_name", None) or getattr(msg, "sender", "Bilinmeyen"))
            subject = html.escape(getattr(msg, "subject", ""))
            search_blob = html.escape(f"{sender_name} {subject}".lower())

            cat_esc = html.escape(category)
            sent_esc = html.escape(sentiment)
            pr_esc = html.escape(priority)

            cards += f"""
            <div class="message-card {pr_esc}" data-priority="{pr_esc}" data-category="{cat_esc}" data-search="{search_blob}">
                <div class="card-top">
                    {self._source_dot(source)}
                    <span class="badge {cat_esc}">{CATEGORY_LABELS.get(category, category.capitalize())}</span>
                    <span class="badge {sent_esc}">{SENTIMENT_LABELS.get(sentiment, sentiment.capitalize())}</span>
                    <span class="priority-tag {pr_esc}">{PRIORITY_LABELS.get(priority, priority.capitalize())}</span>
                </div>
                <div class="sender">{sender_name}</div>
                <div class="subject">{subject}</div>
                <div class="summary">{summary}</div>
                {action_html}
                {meta_html}
                {tag_html}
            </div>"""

        return f"""
        <section class="section" id="messages">
            <h2>📬 Tüm Mesajlar<span class="count-pill">{len(messages)}</span></h2>
            <div class="toolbar">
                <input type="text" id="msg-search" class="search-input" placeholder="Gönderen veya konuya göre ara…">
                <div class="filter-chips" id="priority-filters">
                    <button class="chip-filter active" data-filter="all">Tümü</button>
                    <button class="chip-filter" data-filter="critical">Kritik</button>
                    <button class="chip-filter" data-filter="normal">Normal</button>
                    <button class="chip-filter" data-filter="low">Düşük</button>
                </div>
            </div>
            <div class="card-list" id="message-list">{cards}</div>
            <div class="empty-state" id="empty-state" hidden>Aramanızla eşleşen mesaj bulunamadı.</div>
        </section>"""

    def _badge_css(self) -> str:
        colors = {**ChartGenerator.CATEGORY_COLORS, **ChartGenerator.SENTIMENT_COLORS}
        rules = [
            f'.badge.{key} {{ background: {color}26; color: {color}; box-shadow: inset 0 0 0 1px {color}4d; }}'
            for key, color in colors.items()
        ]
        return "\n        ".join(rules)

    def _priority_css(self) -> str:
        rules = []
        for key, color in ChartGenerator.PRIORITY_COLORS.items():
            rules.append(f'.message-card.{key} {{ border-left-color: {color}; }}')
            rules.append(f'.priority-tag.{key} {{ color: {color}; }}')
        return "\n        ".join(rules)

    def _get_html_template(self, **kwargs) -> str:
        """HTML şablonunu ve modern CSS stil tanımlarını döner."""
        report: Report = kwargs.get("report")
        generation_time = datetime.now().strftime("%H:%M:%S")
        threat_count = kwargs.get("threat_count", 0)

        nav_links = ""
        if kwargs.get("critical_html"):
            nav_links += '<a href="#critical">Kritik</a>'
        if kwargs.get("opportunity_html"):
            nav_links += '<a href="#opportunities">Fırsatlar</a>'
        if kwargs.get("message_cards"):
            nav_links += '<a href="#messages">Tüm Mesajlar</a>'

        extra_stat = ""
        if kwargs.get("threat_chart"):
            extra_stat = f"""
            <div class="stat-card" style="--accent: {ChartGenerator.STATUS_COLORS['serious']}">
                <div class="stat-icon">🛡️</div>
                <div class="stat-body">
                    <div class="number">{threat_count}</div>
                    <div class="label">Tehdit</div>
                </div>
            </div>"""

        chart_blocks = [
            kwargs.get("source_chart"), kwargs.get("category_chart"),
            kwargs.get("sentiment_gauge"), kwargs.get("sentiment_chart"),
            kwargs.get("priority_chart"), kwargs.get("threat_chart"),
        ]
        chart_html = "\n".join(
            f'<div class="chart-card">{c}</div>' for c in chart_blocks if c
        )

        return f"""<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BriefMe — Günlük Rapor ({report.date})</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        :root {{
            --bg-plane: #05070f;
            --bg-glow-1: #1e2761;
            --bg-glow-2: #0f766e;
            --surface: #0f172a;
            --surface-alt: #131c31;
            --card-bg: rgba(30, 41, 59, 0.45);
            --card-border: rgba(148, 163, 184, 0.10);
            --text-primary: #e2e8f0;
            --text-secondary: #94a3b8;
            --text-muted: #64748b;
            --brand: #3987e5;
            --brand-2: #9085e9;
            --radius-sm: 10px;
            --radius-md: 16px;
            --radius-lg: 22px;
            --shadow-soft: 0 8px 30px rgba(0,0,0,0.35);
        }}

        * {{ margin: 0; padding: 0; box-sizing: border-box; }}

        html {{ scroll-behavior: smooth; color-scheme: dark; }}

        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: var(--bg-plane);
            color: var(--text-primary);
            line-height: 1.6;
            min-height: 100vh;
            background-image:
                radial-gradient(700px circle at 12% -10%, rgba(30,39,97,0.55), transparent 55%),
                radial-gradient(600px circle at 100% 0%, rgba(15,118,110,0.25), transparent 50%);
            background-repeat: no-repeat;
        }}

        .container {{ max-width: 1160px; margin: 0 auto; padding: 28px 20px 60px; }}

        @media (prefers-reduced-motion: no-preference) {{
            .fade-in {{ animation: fadeInUp 0.5s ease both; }}
        }}
        @keyframes fadeInUp {{
            from {{ opacity: 0; transform: translateY(10px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}

        /* Header */
        .header {{
            position: relative;
            overflow: hidden;
            background: linear-gradient(135deg, #1e2761 0%, #2a3a8c 45%, #3987e5 100%);
            padding: 44px 40px;
            border-radius: var(--radius-lg);
            margin-bottom: 20px;
            box-shadow: var(--shadow-soft);
        }}

        .header::after {{
            content: "";
            position: absolute;
            inset: 0;
            background: radial-gradient(420px circle at 90% -20%, rgba(255,255,255,0.18), transparent 60%);
            pointer-events: none;
        }}

        .header-top {{ display: flex; align-items: center; justify-content: space-between; gap: 16px; flex-wrap: wrap; position: relative; }}

        .brand {{ display: flex; align-items: center; gap: 12px; }}

        .brand-mark {{
            width: 44px; height: 44px; border-radius: 12px;
            background: rgba(255,255,255,0.14);
            border: 1px solid rgba(255,255,255,0.25);
            display: flex; align-items: center; justify-content: center;
            font-size: 20px; font-weight: 800; color: #fff;
            backdrop-filter: blur(6px);
        }}

        .brand h1 {{ font-size: 26px; font-weight: 800; letter-spacing: -0.5px; color: #fff; }}
        .brand .tagline {{ font-size: 12.5px; color: rgba(255,255,255,0.75); font-weight: 500; }}

        .header-date {{
            font-size: 13px; font-weight: 600; color: #fff;
            background: rgba(255,255,255,0.12);
            border: 1px solid rgba(255,255,255,0.2);
            padding: 8px 16px; border-radius: 999px;
            backdrop-filter: blur(6px);
        }}

        /* Sticky quick-nav */
        .quicknav {{
            position: sticky; top: 0; z-index: 20;
            display: flex; gap: 8px; overflow-x: auto;
            padding: 10px 4px; margin-bottom: 20px;
            background: rgba(5,7,15,0.75);
            backdrop-filter: blur(10px);
            border-bottom: 1px solid var(--card-border);
        }}
        .quicknav a {{
            flex: 0 0 auto;
            color: var(--text-secondary); text-decoration: none;
            font-size: 13px; font-weight: 600;
            padding: 7px 14px; border-radius: 999px;
            border: 1px solid var(--card-border);
            transition: all 0.15s ease;
        }}
        .quicknav a:hover {{ color: #fff; border-color: var(--brand); background: rgba(57,135,229,0.12); }}

        /* Stat strip */
        .stats-row {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
            gap: 14px;
            margin-bottom: 20px;
        }}

        .stat-card {{
            --accent: var(--brand);
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: var(--radius-md);
            padding: 18px 20px;
            display: flex; align-items: center; gap: 14px;
            box-shadow: var(--shadow-soft);
            backdrop-filter: blur(10px);
            transition: transform 0.2s ease, border-color 0.2s ease;
        }}
        .stat-card:hover {{ transform: translateY(-3px); border-color: var(--accent); }}

        .stat-icon {{
            width: 42px; height: 42px; border-radius: 12px;
            display: flex; align-items: center; justify-content: center;
            font-size: 19px;
            background: color-mix(in srgb, var(--accent) 18%, transparent);
            box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--accent) 35%, transparent);
        }}

        .stat-card .number {{ font-size: 28px; font-weight: 800; color: var(--text-primary); line-height: 1.1; }}
        .stat-card .label {{ font-size: 12.5px; color: var(--text-secondary); margin-top: 2px; font-weight: 500; }}

        /* Charts */
        .chart-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 14px;
            margin-bottom: 20px;
        }}

        .chart-card {{
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: var(--radius-md);
            padding: 14px;
            box-shadow: var(--shadow-soft);
            backdrop-filter: blur(10px);
            display: flex; justify-content: center; align-items: center;
            min-height: 240px;
            overflow: hidden;
        }}

        /* Sections */
        .section {{
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: var(--radius-md);
            padding: 24px;
            margin-bottom: 16px;
            box-shadow: var(--shadow-soft);
            backdrop-filter: blur(10px);
            scroll-margin-top: 70px;
        }}

        .section h2 {{
            font-size: 17px; font-weight: 700;
            color: var(--text-primary);
            margin-bottom: 16px;
            display: flex; align-items: center; gap: 10px;
        }}

        .count-pill {{
            font-size: 12px; font-weight: 700; color: var(--text-secondary);
            background: rgba(148,163,184,0.12);
            padding: 2px 10px; border-radius: 999px;
        }}

        .card-list {{ display: flex; flex-direction: column; gap: 10px; }}

        /* Toolbar */
        .toolbar {{ display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 16px; }}

        .search-input {{
            flex: 1 1 220px;
            background: rgba(15,23,42,0.6);
            border: 1px solid var(--card-border);
            color: var(--text-primary);
            padding: 9px 14px; border-radius: 10px; font-size: 13.5px;
            font-family: inherit;
        }}
        .search-input::placeholder {{ color: var(--text-muted); }}
        .search-input:focus {{ outline: none; border-color: var(--brand); }}

        .filter-chips {{ display: flex; gap: 6px; flex-wrap: wrap; }}
        .chip-filter {{
            font-family: inherit;
            font-size: 12.5px; font-weight: 600;
            color: var(--text-secondary);
            background: rgba(148,163,184,0.08);
            border: 1px solid var(--card-border);
            padding: 7px 14px; border-radius: 999px; cursor: pointer;
            transition: all 0.15s ease;
        }}
        .chip-filter:hover {{ color: var(--text-primary); }}
        .chip-filter.active {{ background: var(--brand); color: #fff; border-color: var(--brand); }}

        .empty-state {{
            text-align: center; padding: 30px; color: var(--text-muted); font-size: 13.5px;
        }}

        /* Message card */
        .message-card {{
            border: 1px solid var(--card-border);
            border-left: 3px solid var(--text-muted);
            border-radius: var(--radius-sm);
            padding: 16px 18px;
            background: rgba(15, 23, 42, 0.4);
            transition: transform 0.15s ease, background 0.15s ease, box-shadow 0.15s ease;
        }}
        .message-card:hover {{
            transform: translateX(2px);
            background: rgba(15, 23, 42, 0.65);
            box-shadow: 0 6px 18px rgba(0,0,0,0.25);
        }}

        .card-top {{ display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin-bottom: 8px; }}

        .source-dot {{
            width: 22px; height: 22px; border-radius: 7px;
            display: flex; align-items: center; justify-content: center;
            font-size: 10.5px; font-weight: 700; color: #05070f;
            background: var(--dot);
            flex-shrink: 0;
        }}

        .message-card .sender {{ font-weight: 700; color: var(--text-primary); font-size: 14.5px; }}
        .message-card .subject {{ color: var(--text-secondary); font-size: 13px; margin: 3px 0 6px; }}
        .message-card .summary {{ color: #cbd5e1; font-size: 13.5px; margin: 4px 0; }}

        .message-card .action {{
            background: rgba(57, 135, 229, 0.12);
            color: #7ab0f2;
            padding: 7px 12px;
            border-radius: 8px;
            font-size: 12.5px;
            margin-top: 8px;
            font-weight: 600;
            display: inline-block;
        }}

        .meta-chips {{ display: flex; gap: 6px; flex-wrap: wrap; margin-top: 8px; }}
        .chip {{ font-size: 11.5px; font-weight: 600; padding: 3px 10px; border-radius: 999px; }}
        .chip-threat {{ background: rgba(208,59,59,0.15); color: #f28b8b; }}
        .chip-response {{ background: rgba(250,178,25,0.15); color: #f5c463; }}
        .chip-deadline {{ background: rgba(148,163,184,0.12); color: var(--text-secondary); }}

        .tags {{ display: flex; gap: 6px; flex-wrap: wrap; margin-top: 8px; }}
        .tag {{ background: rgba(148,163,184,0.10); color: var(--text-muted); padding: 3px 10px; border-radius: 999px; font-size: 11px; }}

        .priority-tag {{
            margin-left: auto;
            font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.03em;
        }}

        .badge {{
            display: inline-block;
            padding: 3px 11px;
            border-radius: 999px;
            font-size: 11px;
            font-weight: 700;
        }}
        {self._badge_css()}
        {self._priority_css()}

        .footer {{
            text-align: center;
            padding: 30px 10px 10px;
            color: var(--text-muted);
            font-size: 12.5px;
        }}
        .footer strong {{ color: var(--text-secondary); }}

        @media (max-width: 640px) {{
            .header {{ padding: 30px 22px; }}
            .brand h1 {{ font-size: 21px; }}
            .container {{ padding: 18px 12px 40px; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header fade-in">
            <div class="header-top">
                <div class="brand">
                    <div class="brand-mark">B</div>
                    <div>
                        <h1>BriefMe</h1>
                        <div class="tagline">Günlük İletişim İstihbarat Raporu</div>
                    </div>
                </div>
                <div class="header-date">{report.date} · {report.total_messages} mesaj</div>
            </div>
        </div>

        <nav class="quicknav">
            <a href="#overview">Genel Bakış</a>
            {nav_links}
        </nav>

        <div id="overview">
            <div class="stats-row fade-in">
                <div class="stat-card" style="--accent: {ChartGenerator.PRIORITY_COLORS['normal']}">
                    <div class="stat-icon">📨</div>
                    <div class="stat-body">
                        <div class="number">{report.total_messages}</div>
                        <div class="label">Toplam Mesaj</div>
                    </div>
                </div>
                <div class="stat-card" style="--accent: {ChartGenerator.STATUS_COLORS['critical']}">
                    <div class="stat-icon">🚨</div>
                    <div class="stat-body">
                        <div class="number">{len(report.critical_items)}</div>
                        <div class="label">Kritik</div>
                    </div>
                </div>
                <div class="stat-card" style="--accent: {ChartGenerator.STATUS_COLORS['good']}">
                    <div class="stat-icon">✨</div>
                    <div class="stat-body">
                        <div class="number">{len(report.opportunities)}</div>
                        <div class="label">Fırsat</div>
                    </div>
                </div>
                <div class="stat-card" style="--accent: {ChartGenerator.STATUS_COLORS['warning']}">
                    <div class="stat-icon">🔥</div>
                    <div class="stat-body">
                        <div class="number">{report.by_sentiment.get('urgent', 0)}</div>
                        <div class="label">Acil</div>
                    </div>
                </div>
                {extra_stat}
            </div>

            <div class="chart-grid fade-in">{chart_html}</div>
        </div>

        {kwargs.get('critical_html')}
        {kwargs.get('opportunity_html')}
        {kwargs.get('message_cards')}

        <div class="footer">
            <strong>BriefMe</strong> — AI-Powered Communication Intelligence<br>
            Rapor oluşturulma: {generation_time}
        </div>
    </div>

    <script>
    (function () {{
        var search = document.getElementById('msg-search');
        var filterWrap = document.getElementById('priority-filters');
        var list = document.getElementById('message-list');
        var empty = document.getElementById('empty-state');
        if (!list) return;

        var cards = Array.prototype.slice.call(list.querySelectorAll('.message-card'));
        var activeFilter = 'all';

        function applyFilters() {{
            var q = (search && search.value || '').trim().toLowerCase();
            var visible = 0;
            cards.forEach(function (card) {{
                var matchesFilter = activeFilter === 'all' || card.dataset.priority === activeFilter;
                var matchesSearch = !q || card.dataset.search.indexOf(q) !== -1;
                var show = matchesFilter && matchesSearch;
                card.style.display = show ? '' : 'none';
                if (show) visible++;
            }});
            if (empty) empty.hidden = visible !== 0;
        }}

        if (search) search.addEventListener('input', applyFilters);
        if (filterWrap) {{
            filterWrap.addEventListener('click', function (e) {{
                var btn = e.target.closest('.chip-filter');
                if (!btn) return;
                filterWrap.querySelectorAll('.chip-filter').forEach(function (b) {{ b.classList.remove('active'); }});
                btn.classList.add('active');
                activeFilter = btn.dataset.filter;
                applyFilters();
            }});
        }}
    }})();

    (function () {{
        function resizeCharts() {{
            if (!window.Plotly) return;
            document.querySelectorAll('.js-plotly-plot').forEach(function (gd) {{ Plotly.Plots.resize(gd); }});
        }}
        window.addEventListener('load', resizeCharts);
        if (document.fonts && document.fonts.ready) {{
            document.fonts.ready.then(resizeCharts);
        }}
    }})();
    </script>
</body>
</html>"""

