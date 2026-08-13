import plotly.graph_objects as go
import plotly.io as pio


class ChartGenerator:
    """BriefMe için CVD-güvenli, doğrulanmış bir renk paletiyle
    Plotly grafikleri üreten servis sınıfı.

    Renk rolleri (kategori/durum/kaynak) burada tek noktadan
    tanımlanır; ReportBuilder rozet ve vurgu renklerini de
    buradan (ChartGenerator.*_COLORS) okuyarak grafik ile HTML
    arayüzünün birebir aynı paleti kullanmasını garanti eder.
    """

    # Kategori kimliği — sabit, döngüsüz sırayla atanmış (CVD ΔE >= 8, dark surface #0F172A)
    CATEGORY_COLORS = {
        "work": "#3987e5",
        "promotion": "#d95926",
        "personal": "#199e70",
        "finance": "#c98500",
        "social": "#d55181",
        "notification": "#9085e9",
        "threat": "#e66767",
        "uncategorized": "#64748b",
    }

    # Kaynak kimliği — sadece 3 seri, all-pairs doğrulanmış üçlü
    SOURCE_COLORS = {
        "gmail": "#3987e5",
        "linkedin": "#199e70",
        "instagram": "#d95926",
    }

    # Durum paleti — asla temalandırılmaz, ikon/etiketle birlikte kullanılır
    STATUS_COLORS = {
        "good": "#0ca30c",
        "warning": "#fab219",
        "serious": "#ec835a",
        "critical": "#d03b3b",
        "muted": "#64748b",
    }

    SENTIMENT_COLORS = {
        "positive": STATUS_COLORS["good"],
        "urgent": STATUS_COLORS["warning"],
        "negative": STATUS_COLORS["critical"],
        "neutral": STATUS_COLORS["muted"],
    }

    PRIORITY_COLORS = {
        "critical": STATUS_COLORS["critical"],
        "normal": "#3987e5",
        "low": STATUS_COLORS["muted"],
    }

    CATEGORY_LABELS = {
        "work": "İş", "personal": "Kişisel", "finance": "Finans",
        "promotion": "Promosyon", "notification": "Bildirim", "social": "Sosyal",
        "threat": "Tehdit", "uncategorized": "Diğer",
    }
    SENTIMENT_LABELS = {"positive": "Pozitif", "negative": "Negatif", "neutral": "Nötr", "urgent": "Acil"}
    PRIORITY_LABELS = {"critical": "Kritik", "normal": "Normal", "low": "Düşük"}

    INK_PRIMARY = "#E2E8F0"
    INK_SECONDARY = "#94A3B8"
    INK_MUTED = "#64748B"

    def __init__(self):
        self.base = dict(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Inter, -apple-system, 'Segoe UI', sans-serif", color=self.INK_SECONDARY, size=11),
            margin=dict(l=8, r=8, t=40, b=8),
            autosize=True,
            hoverlabel=dict(
                bgcolor="#1E293B", bordercolor="rgba(148,163,184,0.18)",
                font=dict(color=self.INK_PRIMARY, size=12, family="Inter, sans-serif"),
            ),
        )

    def _title(self, text: str) -> dict:
        return dict(text=text, font=dict(size=12, color=self.INK_MUTED), x=0.5, xanchor="center")

    def _to_html(self, fig) -> str:
        config = {"responsive": True, "displayModeBar": False}
        return pio.to_html(fig, include_plotlyjs=False, full_html=False, config=config)

    def source_pie(self, by_source: dict) -> str:
        if not by_source:
            return ""
        total = sum(by_source.values())
        colors = [self.SOURCE_COLORS.get(k, self.INK_MUTED) for k in by_source.keys()]
        fig = go.Figure(data=[go.Pie(
            labels=[k.capitalize() for k in by_source.keys()],
            values=list(by_source.values()),
            hole=0.64, pull=[0.02] * len(by_source),
            marker=dict(colors=colors, line=dict(color="#0F172A", width=2)),
            textinfo="label+percent", textfont=dict(size=10, color=self.INK_PRIMARY),
            hovertemplate="<b>%{label}</b><br>%{value} mesaj (%{percent})<extra></extra>",
        )])
        fig.update_layout(**self.base, title=self._title("Kaynak Dağılımı"),
            showlegend=False, height=220,
            annotations=[dict(text=f"<b>{total}</b>", x=0.5, y=0.5, font=dict(size=22, color=self.INK_PRIMARY), showarrow=False)])
        return self._to_html(fig)

    def category_bar(self, by_category: dict) -> str:
        if not by_category:
            return ""
        items = sorted(by_category.items(), key=lambda x: x[1], reverse=True)
        height = max(220, 42 * len(items) + 60)
        fig = go.Figure(data=[go.Bar(
            x=[v for _, v in items], y=[self.CATEGORY_LABELS.get(k, k.capitalize()) for k, _ in items],
            orientation="h", marker=dict(color=[self.CATEGORY_COLORS.get(k, self.INK_MUTED) for k, _ in items], cornerradius=4),
            text=[str(v) for _, v in items], textposition="outside", textfont=dict(size=11, color=self.INK_PRIMARY),
            hovertemplate="<b>%{y}</b>: %{x} mesaj<extra></extra>",
        )])
        fig.update_layout(**self.base, title=self._title("Kategori Dağılımı"),
            height=height, xaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
            yaxis=dict(showgrid=False, autorange="reversed", tickfont=dict(color=self.INK_SECONDARY, size=10)),
            bargap=0.35)
        return self._to_html(fig)

    def sentiment_gauge(self, by_sentiment: dict) -> str:
        total = sum(by_sentiment.values())
        if total == 0:
            return ""
        score = ((by_sentiment.get("positive", 0) - by_sentiment.get("negative", 0)) / total) * 100
        if score > 30:
            color = self.STATUS_COLORS["good"]
        elif score > -30:
            color = self.STATUS_COLORS["warning"]
        else:
            color = self.STATUS_COLORS["critical"]
        fig = go.Figure(go.Indicator(mode="gauge+number", value=score,
            number=dict(suffix="%", font=dict(size=22, color=self.INK_PRIMARY)),
            gauge=dict(axis=dict(range=[-100, 100], tickvals=[-100, 0, 100], ticktext=["Negatif", "Nötr", "Pozitif"],
                tickfont=dict(size=9, color=self.INK_MUTED), tickcolor="#1E293B"),
                bar=dict(color=color, thickness=0.7), bgcolor="#1E293B", borderwidth=0,
                steps=[dict(range=[-100, -30], color="rgba(208,59,59,0.08)"),
                    dict(range=[-30, 30], color="rgba(250,178,25,0.08)"),
                    dict(range=[30, 100], color="rgba(12,163,12,0.08)")])))
        fig.update_layout(**self.base, title=self._title("Duygu Skoru"), height=190)
        return self._to_html(fig)

    def sentiment_breakdown(self, by_sentiment: dict) -> str:
        if not by_sentiment:
            return ""
        emojis = {"positive": "😊", "negative": "😟", "neutral": "😐", "urgent": "🔥"}
        order = [k for k in ["positive", "neutral", "negative", "urgent"] if k in by_sentiment]
        order += [k for k in by_sentiment if k not in order]
        fig = go.Figure(data=[go.Bar(
            x=[self.SENTIMENT_LABELS.get(k, k.capitalize()) for k in order], y=[by_sentiment[k] for k in order],
            marker=dict(color=[self.SENTIMENT_COLORS.get(k, self.INK_MUTED) for k in order], cornerradius=6),
            text=[f"{emojis.get(k, '')} {by_sentiment[k]}" for k in order],
            textposition="outside", textfont=dict(size=11, color=self.INK_PRIMARY),
            hovertemplate="<b>%{x}</b>: %{y}<extra></extra>",
        )])
        fig.update_layout(**self.base, title=self._title("Duygu Dağılımı"),
            height=220, xaxis=dict(showgrid=False, tickfont=dict(color=self.INK_SECONDARY, size=10)),
            yaxis=dict(showgrid=True, gridcolor="rgba(148,163,184,0.08)", zeroline=False, tickfont=dict(color=self.INK_MUTED)),
            bargap=0.4)
        return self._to_html(fig)

    def priority_donut(self, results: list) -> str:
        counts = {}
        for r in results:
            p = getattr(r, "priority", "normal")
            counts[p] = counts.get(p, 0) + 1
        if not counts:
            return ""
        order = [k for k in ["critical", "normal", "low"] if k in counts]
        order += [k for k in counts if k not in order]
        fig = go.Figure(data=[go.Pie(
            labels=[self.PRIORITY_LABELS.get(k, k.capitalize()) for k in order], values=[counts[k] for k in order],
            hole=0.66, marker=dict(colors=[self.PRIORITY_COLORS.get(k, self.INK_MUTED) for k in order], line=dict(color="#0F172A", width=2)),
            textinfo="label+value", textfont=dict(size=10, color=self.INK_PRIMARY),
            hovertemplate="<b>%{label}</b>: %{value}<extra></extra>",
        )])
        fig.update_layout(**self.base, title=self._title("Öncelik Dağılımı"),
            height=220, showlegend=False)
        return self._to_html(fig)

    def threat_summary(self, results: list) -> str:
        if not results:
            return ""
        threats = len([r for r in results if getattr(r, "is_threat", False)])
        safe = len(results) - threats
        icon, color = ("✓", self.STATUS_COLORS["good"]) if threats == 0 else ("⚠", self.STATUS_COLORS["critical"])
        fig = go.Figure(data=[go.Pie(
            labels=["Güvenli", "Tehdit"], values=[safe, threats], hole=0.7, sort=False,
            marker=dict(colors=[self.STATUS_COLORS["good"], self.STATUS_COLORS["critical"]], line=dict(color="#0F172A", width=2)),
            textinfo="label+value", textfont=dict(size=10, color=self.INK_PRIMARY),
            hovertemplate="<b>%{label}</b>: %{value}<extra></extra>",
        )])
        fig.update_layout(**self.base, title=self._title("Güvenlik Taraması"),
            height=220, showlegend=False,
            annotations=[dict(text=icon, x=0.5, y=0.5, font=dict(size=30, color=color), showarrow=False)])
        return self._to_html(fig)
