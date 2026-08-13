from datetime import datetime
from pathlib import Path

from src.reporters.charts import ChartGenerator
from src.notifiers.base import Report
from src.utils.logger import get_logger


class ReportBuilder:

    def __init__(self):
        self.logger = get_logger("reporter")
        self.charts = ChartGenerator()
        self.output_dir = Path("reports")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def build(self, report: Report, messages: list = None, results: list = None) -> str:
        self.logger.info("Building daily report...")

        source_chart = self.charts.source_pie(report.by_source)
        category_chart = self.charts.category_bar(report.by_category)
        sentiment_gauge = self.charts.sentiment_gauge(report.by_sentiment)
        sentiment_chart = self.charts.sentiment_breakdown(report.by_sentiment)
        priority_chart = self.charts.priority_donut(results or [])
        threat_chart = self.charts.threat_summary(results or [])

        critical_cards = self._cards(report.critical_items, "critical")
        opportunity_cards = self._cards(report.opportunities, "opportunity")
        all_cards = self._all_cards(messages, results)
        cat_sections = self._category_view(messages, results)
        threat_details = self._threat_view(messages, results)

        html = f"""<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
<title>BriefMe</title>
<script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
*{{margin:0;padding:0;box-sizing:border-box}}
html,body{{height:100%;overflow:hidden}}
body{{font-family:'Inter',sans-serif;background:#0F172A;color:#E2E8F0}}

.app{{height:100vh;display:flex;flex-direction:column;max-width:1200px;margin:0 auto}}

/* HEADER */
.hdr{{display:flex;justify-content:space-between;align-items:center;padding:12px 16px;border-bottom:1px solid #1E293B;flex-shrink:0}}
.hdr h1{{font-size:18px;font-weight:800;background:linear-gradient(135deg,#6366F1,#EC4899);-webkit-background-clip:text;-webkit-text-fill-color:transparent}}
.hdr .dt{{font-size:10px;color:#475569;margin-top:1px}}
.hdr-right{{display:flex;gap:8px;align-items:center}}
.lang{{background:#1E293B;border:1px solid #334155;border-radius:6px;padding:4px 10px;color:#94A3B8;font-size:11px;font-weight:600;cursor:pointer;transition:all .2s}}
.lang:hover{{border-color:#6366F1;color:#6366F1}}

/* STATS */
.stats{{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;padding:10px 16px;flex-shrink:0}}
.st{{background:#1E293B;border-radius:10px;padding:10px 6px;text-align:center;border:1px solid #334155}}
.st .n{{font-size:22px;font-weight:800}}
.st .l{{font-size:9px;color:#475569;text-transform:uppercase;letter-spacing:.5px;margin-top:2px}}

/* NAV */
.nav{{display:flex;gap:6px;padding:8px 16px;overflow-x:auto;flex-shrink:0;scrollbar-width:none}}
.nav::-webkit-scrollbar{{display:none}}
.nb{{flex-shrink:0;background:#1E293B;border:1px solid #334155;border-radius:8px;padding:7px 14px;color:#94A3B8;font-size:12px;font-weight:500;cursor:pointer;transition:all .2s;display:flex;align-items:center;gap:5px;white-space:nowrap}}
.nb:hover{{border-color:#6366F1;color:#E2E8F0}}
.nb.on{{background:#6366F1;border-color:#6366F1;color:#fff;box-shadow:0 4px 12px rgba(99,102,241,.3)}}

/* CONTENT */
.content{{flex:1;overflow-y:auto;overflow-x:hidden;padding:12px 16px;scrollbar-width:thin;scrollbar-color:#334155 transparent}}
.content::-webkit-scrollbar{{width:4px}}
.content::-webkit-scrollbar-thumb{{background:#334155;border-radius:4px}}

.sec{{display:none;animation:fadeUp .25s ease}}
.sec.on{{display:block}}
@keyframes fadeUp{{from{{opacity:0;transform:translateY(8px)}}to{{opacity:1;transform:translateY(0)}}}}

/* CHARTS */
.cg{{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}}
.cc{{background:#1E293B;border-radius:10px;padding:8px;border:1px solid #334155;overflow:hidden}}
.cc .js-plotly-plot,.cc .plotly{{width:100%!important;height:100%!important}}

/* MSG CARDS */
.mc{{background:#1E293B;border-radius:10px;padding:14px;margin-bottom:8px;border:1px solid #334155;transition:border-color .2s}}
.mc:hover{{border-color:#6366F1}}
.mc.p-critical{{border-left:3px solid #F87171}}
.mc.p-normal{{border-left:3px solid #60A5FA}}
.mc.p-low{{border-left:3px solid #475569}}
.mc .top{{display:flex;justify-content:space-between;align-items:center;margin-bottom:6px}}
.mc .snd{{font-size:14px;font-weight:600}}
.mc .sbj{{font-size:11px;color:#475569;margin-bottom:6px}}
.mc .sum{{font-size:12px;color:#94A3B8;line-height:1.5;margin-bottom:8px}}
.mc .act{{background:rgba(99,102,241,.08);border:1px solid rgba(99,102,241,.15);color:#818CF8;padding:6px 10px;border-radius:6px;font-size:11px}}
.mc .act::before{{content:"→ "}}

/* BADGES */
.b{{display:inline-block;padding:2px 8px;border-radius:5px;font-size:9px;font-weight:600;text-transform:uppercase;letter-spacing:.3px}}
.b-work{{background:rgba(129,140,248,.12);color:#818CF8}}
.b-personal{{background:rgba(52,211,153,.12);color:#34D399}}
.b-finance{{background:rgba(251,191,36,.12);color:#FBBF24}}
.b-promotion{{background:rgba(100,116,139,.12);color:#94A3B8}}
.b-notification{{background:rgba(96,165,250,.12);color:#60A5FA}}
.b-social{{background:rgba(244,114,182,.12);color:#F472B6}}
.b-threat{{background:rgba(248,113,113,.12);color:#F87171}}
.b-positive{{background:rgba(52,211,153,.12);color:#34D399}}
.b-negative{{background:rgba(248,113,113,.12);color:#F87171}}
.b-neutral{{background:rgba(100,116,139,.12);color:#94A3B8}}
.b-urgent{{background:rgba(251,191,36,.12);color:#FBBF24}}
.b-gmail{{background:rgba(248,113,113,.12);color:#F87171}}
.b-linkedin{{background:rgba(96,165,250,.12);color:#60A5FA}}
.b-instagram{{background:rgba(244,114,182,.12);color:#F472B6}}

.tags{{display:flex;gap:4px;flex-wrap:wrap;margin-top:8px}}
.tg{{background:#0F172A;color:#475569;padding:2px 8px;border-radius:4px;font-size:9px;border:1px solid #1E293B}}

.empty{{text-align:center;padding:30px;color:#475569}}
.empty .ei{{font-size:32px;margin-bottom:8px}}

.cat-hdr{{font-size:13px;font-weight:600;margin:14px 0 8px;display:flex;align-items:center;gap:6px}}
.cat-hdr .cnt{{color:#475569;font-weight:400;font-size:11px}}

/* FOOTER */
.ftr{{text-align:center;padding:10px;color:#334155;font-size:10px;flex-shrink:0;border-top:1px solid #1E293B}}

@media(max-width:768px){{
    .cg{{grid-template-columns:repeat(2,1fr)}}
    .stats{{grid-template-columns:repeat(4,1fr);gap:6px}}
    .st .n{{font-size:18px}}
}}
@media(max-width:480px){{
    .cg{{grid-template-columns:1fr 1fr}}
    .hdr h1{{font-size:16px}}
}}
</style>
</head>
<body>
<div class="app">

<div class="hdr">
    <div>
        <h1>BriefMe</h1>
        <div class="dt" id="dtText">{report.date} — <span data-tr="Günlük Rapor" data-en="Daily Report">Günlük Rapor</span></div>
    </div>
    <div class="hdr-right">
        <button class="lang" onclick="tLang()">EN/TR</button>
    </div>
</div>

<div class="stats">
    <div class="st"><div class="n">{report.total_messages}</div><div class="l" data-tr="Toplam" data-en="Total">Toplam</div></div>
    <div class="st"><div class="n" style="color:#F87171">{len(report.critical_items)}</div><div class="l" data-tr="Kritik" data-en="Critical">Kritik</div></div>
    <div class="st"><div class="n" style="color:#34D399">{len(report.opportunities)}</div><div class="l" data-tr="Fırsat" data-en="Opportunity">Fırsat</div></div>
    <div class="st"><div class="n" style="color:#FBBF24">{report.by_sentiment.get('urgent',0)}</div><div class="l" data-tr="Acil" data-en="Urgent">Acil</div></div>
</div>

<div class="nav">
    <button class="nb on" onclick="go('ov',this)"><span>📊</span><span data-tr="Genel" data-en="Overview">Genel</span></button>
    <button class="nb" onclick="go('cr',this)"><span>🔴</span><span data-tr="Kritik" data-en="Critical">Kritik</span></button>
    <button class="nb" onclick="go('op',this)"><span>🟢</span><span data-tr="Fırsatlar" data-en="Good News">Fırsatlar</span></button>
    <button class="nb" onclick="go('ms',this)"><span>📬</span><span data-tr="Mesajlar" data-en="Messages">Mesajlar</span></button>
    <button class="nb" onclick="go('ct',this)"><span>📁</span><span data-tr="Kategoriler" data-en="Categories">Kategoriler</span></button>
    <button class="nb" onclick="go('sc',this)"><span>🛡️</span><span data-tr="Güvenlik" data-en="Security">Güvenlik</span></button>
</div>

<div class="content">

    <div class="sec on" id="s-ov">
        <div class="cg">
            <div class="cc">{source_chart}</div>
            <div class="cc">{category_chart}</div>
            <div class="cc">{sentiment_gauge}</div>
            <div class="cc">{sentiment_chart}</div>
            <div class="cc">{priority_chart}</div>
            <div class="cc">{threat_chart}</div>
        </div>
    </div>

    <div class="sec" id="s-cr">
        {critical_cards if critical_cards else '<div class="empty"><div class="ei">✅</div><div data-tr="Kritik mesaj yok" data-en="No critical messages">Kritik mesaj yok</div></div>'}
    </div>

    <div class="sec" id="s-op">
        {opportunity_cards if opportunity_cards else '<div class="empty"><div class="ei">📭</div><div data-tr="Fırsat bulunamadı" data-en="No opportunities found">Fırsat bulunamadı</div></div>'}
    </div>

    <div class="sec" id="s-ms">
        {all_cards if all_cards else '<div class="empty"><div class="ei">📭</div><div data-tr="Mesaj yok" data-en="No messages">Mesaj yok</div></div>'}
    </div>

    <div class="sec" id="s-ct">
        {cat_sections}
    </div>

    <div class="sec" id="s-sc">
        <div class="cc" style="margin-bottom:12px">{threat_chart}</div>
        {threat_details}
    </div>

</div>

<div class="ftr">BriefMe — {datetime.now().strftime("%H:%M:%S")}</div>

</div>

<script>
let lang='tr';
function go(id,btn){{
    document.querySelectorAll('.sec').forEach(s=>s.classList.remove('on'));
    document.querySelectorAll('.nb').forEach(b=>b.classList.remove('on'));
    document.getElementById('s-'+id).classList.add('on');
    if(btn)btn.classList.add('on');
    document.querySelector('.content').scrollTop=0;
    setTimeout(()=>window.dispatchEvent(new Event('resize')),100);
}}
function tLang(){{
    lang=lang==='tr'?'en':'tr';
    document.querySelectorAll('[data-tr][data-en]').forEach(e=>{{e.textContent=e.getAttribute('data-'+lang)}});
}}
window.addEventListener('resize',()=>{{
    document.querySelectorAll('.js-plotly-plot').forEach(p=>{{
        if(p&&p.layout)Plotly.Plots.resize(p);
    }});
}});
</script>
</body>
</html>"""

        filename = f"briefme_{report.date}.html"
        filepath = self.output_dir / filename
        filepath.write_text(html, encoding="utf-8")
        self.logger.info(f"Report saved: {filepath}")
        report.summary_html = html
        return str(filepath)

    def _cards(self, items, ctype):
        if not items: return ""
        h = ""
        for i in items:
            src = i.get("source","")
            h += f'<div class="mc p-{ctype}"><div class="top"><div class="snd">{i.get("sender","?")}</div><span class="b b-{src}">{src.upper()}</span></div><div class="sbj">{i.get("subject","")}</div><div class="sum">{i.get("summary","")}</div></div>'
        return h

    def _all_cards(self, msgs, results):
        if not msgs or not results: return ""
        h = ""
        for m, r in zip(msgs, results):
            cat = getattr(r,"category","")
            sent = getattr(r,"sentiment","")
            pri = getattr(r,"priority","normal")
            summary = getattr(r,"summary","")
            action = getattr(r,"key_action","")
            tags = getattr(r,"tags",[])
            act_h = f'<div class="act">{action}</div>' if action else ""
            tag_h = '<div class="tags">'+"".join(f'<span class="tg">{t}</span>' for t in tags)+'</div>' if tags else ""
            h += f'<div class="mc p-{pri}"><div class="top"><div class="snd">{m.sender_name or m.sender}</div><div><span class="b b-{cat}">{cat}</span> <span class="b b-{sent}">{sent}</span></div></div><div class="sbj">{m.subject}</div><div class="sum">{summary}</div>{act_h}{tag_h}</div>'
        return h

    def _category_view(self, msgs, results):
        if not msgs or not results: return ""
        cats = {}
        for m, r in zip(msgs, results):
            c = getattr(r,"category","uncategorized")
            cats.setdefault(c, []).append((m, r))
        icons = {"work":"💼","personal":"👤","finance":"💰","promotion":"📢","notification":"🔔","social":"👥","threat":"⚠️","uncategorized":"📎"}
        h = ""
        for c, items in sorted(cats.items(), key=lambda x:len(x[1]), reverse=True):
            h += f'<div class="cat-hdr">{icons.get(c,"📎")} {c.capitalize()} <span class="cnt">({len(items)})</span></div>'
            for m, r in items:
                pri = getattr(r,"priority","normal")
                h += f'<div class="mc p-{pri}"><div class="snd">{m.sender_name or m.sender}</div><div class="sbj">{m.subject}</div><div class="sum">{getattr(r,"summary","")}</div></div>'
        return h

    def _threat_view(self, msgs, results):
        if not msgs or not results: return ""
        threats = [(m,r) for m,r in zip(msgs,results) if getattr(r,"is_threat",False)]
        if not threats:
            return '<div class="empty"><div class="ei">✅</div><div data-tr="Tehdit yok, güvendesiniz" data-en="No threats, you are safe">Tehdit yok, güvendesiniz</div></div>'
        h = ""
        for m, r in threats:
            conf = int(getattr(r,"threat_confidence",0)*100)
            h += f'<div class="mc p-critical"><div class="top"><div class="snd">{m.sender_name or m.sender}</div><span class="b b-threat">{getattr(r,"threat_type","").upper()}</span></div><div class="sbj">{m.subject}</div><div class="sum">{getattr(r,"summary","")}</div><div style="margin-top:6px;font-size:11px;color:#F87171">Tehdit Güveni: {conf}%</div></div>'
        return h