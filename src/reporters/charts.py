import plotly.graph_objects as go
import plotly.io as pio


class ChartGenerator:

    def __init__(self):
        self.palette = {
            "work": "#818CF8", "personal": "#34D399", "finance": "#FBBF24",
            "promotion": "#64748B", "notification": "#60A5FA", "social": "#F472B6",
            "threat": "#F87171", "uncategorized": "#475569",
            "positive": "#34D399", "negative": "#F87171",
            "neutral": "#64748B", "urgent": "#FBBF24",
            "critical": "#F87171", "normal": "#60A5FA", "low": "#475569",
        }
        self.source_colors = {
            "gmail": "#F87171", "linkedin": "#60A5FA", "instagram": "#F472B6",
        }
        self.base = dict(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Inter, sans-serif", color="#CBD5E1", size=11),
            margin=dict(l=10, r=10, t=36, b=10),
            autosize=True,
        )

    def _to_html(self, fig):
        config = {"responsive": True, "displayModeBar": False}
        return pio.to_html(fig, include_plotlyjs=False, full_html=False, config=config)

    def source_pie(self, by_source: dict) -> str:
        total = sum(by_source.values())
        colors = [self.source_colors.get(k, "#818CF8") for k in by_source.keys()]
        fig = go.Figure(data=[go.Pie(
            labels=[k.upper() for k in by_source.keys()],
            values=list(by_source.values()),
            hole=0.6, pull=[0.02]*len(by_source),
            marker=dict(colors=colors, line=dict(color="#0F172A", width=2)),
            textinfo="label+percent", textfont=dict(size=10, color="#CBD5E1"),
            hovertemplate="<b>%{label}</b><br>%{value} mesaj<extra></extra>",
        )])
        fig.update_layout(**self.base, title=dict(text="Kaynak", font=dict(size=12, color="#64748B"), x=0.5),
            showlegend=False, height=200,
            annotations=[dict(text=f"<b>{total}</b>", x=0.5, y=0.5, font=dict(size=20, color="#E2E8F0"), showarrow=False)])
        return self._to_html(fig)

    def category_bar(self, by_category: dict) -> str:
        items = sorted(by_category.items(), key=lambda x: x[1], reverse=True)
        fig = go.Figure(data=[go.Bar(
            x=[v for _, v in items], y=[k.capitalize() for k, _ in items],
            orientation="h", marker=dict(color=[self.palette.get(k, "#64748B") for k, _ in items], cornerradius=6),
            text=[str(v) for _, v in items], textposition="outside", textfont=dict(size=11, color="#CBD5E1"),
            hovertemplate="<b>%{y}</b>: %{x}<extra></extra>",
        )])
        fig.update_layout(**self.base, title=dict(text="Kategori", font=dict(size=12, color="#64748B"), x=0.5),
            height=200, xaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
            yaxis=dict(showgrid=False, autorange="reversed", tickfont=dict(color="#94A3B8", size=10)), bargap=0.3)
        return self._to_html(fig)

    def sentiment_gauge(self, by_sentiment: dict) -> str:
        total = sum(by_sentiment.values())
        if total == 0: return ""
        score = ((by_sentiment.get("positive", 0) - by_sentiment.get("negative", 0)) / total) * 100
        color = "#34D399" if score > 30 else "#FBBF24" if score > -30 else "#F87171"
        fig = go.Figure(go.Indicator(mode="gauge+number", value=score,
            number=dict(suffix="%", font=dict(size=22, color="#E2E8F0")),
            gauge=dict(axis=dict(range=[-100, 100], tickvals=[-100,0,100], ticktext=["Negatif","Nötr","Pozitif"],
                tickfont=dict(size=9, color="#475569"), tickcolor="#1E293B"),
                bar=dict(color=color, thickness=0.7), bgcolor="#1E293B", borderwidth=0,
                steps=[dict(range=[-100,-30], color="rgba(248,113,113,0.06)"),
                    dict(range=[-30,30], color="rgba(251,191,36,0.06)"),
                    dict(range=[30,100], color="rgba(52,211,153,0.06)")])))
        fig.update_layout(**self.base, title=dict(text="Duygu Skoru", font=dict(size=12, color="#64748B"), x=0.5), height=180)
        return self._to_html(fig)

    def sentiment_breakdown(self, by_sentiment: dict) -> str:
        emojis = {"positive": "😊", "negative": "😟", "neutral": "😐", "urgent": "🔥"}
        order = [k for k in ["positive", "neutral", "negative", "urgent"] if k in by_sentiment]
        order += [k for k in by_sentiment if k not in order]
        fig = go.Figure(data=[go.Bar(
            x=[k.capitalize() for k in order], y=[by_sentiment[k] for k in order],
            marker=dict(color=[self.palette.get(k, "#64748B") for k in order], cornerradius=8),
            text=[f"{emojis.get(k,'')} {by_sentiment[k]}" for k in order],
            textposition="outside", textfont=dict(size=11, color="#CBD5E1"),
            hovertemplate="<b>%{x}</b>: %{y}<extra></extra>",
        )])
        fig.update_layout(**self.base, title=dict(text="Duygular", font=dict(size=12, color="#64748B"), x=0.5),
            height=200, xaxis=dict(showgrid=False, tickfont=dict(color="#94A3B8", size=10)),
            yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.03)", zeroline=False, tickfont=dict(color="#475569")), bargap=0.4)
        return self._to_html(fig)

    def priority_donut(self, results: list) -> str:
        counts = {}
        for r in results:
            p = getattr(r, "priority", "normal")
            counts[p] = counts.get(p, 0) + 1
        if not counts: return ""
        order = [k for k in ["critical","normal","low"] if k in counts]
        order += [k for k in counts if k not in order]
        fig = go.Figure(data=[go.Pie(
            labels=[k.capitalize() for k in order], values=[counts[k] for k in order],
            hole=0.65, marker=dict(colors=[self.palette.get(k,"#64748B") for k in order], line=dict(color="#0F172A", width=2)),
            textinfo="label+value", textfont=dict(size=10, color="#CBD5E1"),
        )])
        fig.update_layout(**self.base, title=dict(text="Öncelik", font=dict(size=12, color="#64748B"), x=0.5),
            height=200, showlegend=False)
        return self._to_html(fig)

    def threat_summary(self, results: list) -> str:
        threats = len([r for r in results if getattr(r, "is_threat", False)])
        safe = len(results) - threats
        icon, color = ("✓", "#34D399") if threats == 0 else ("⚠", "#F87171")
        fig = go.Figure(data=[go.Pie(
            labels=["Güvenli", "Tehdit"], values=[safe, threats], hole=0.7, sort=False,
            marker=dict(colors=["#34D399","#F87171"] if threats else ["#34D399","rgba(0,0,0,0)"],
                line=dict(color="#0F172A", width=2)),
            textinfo="label+value", textfont=dict(size=10, color="#CBD5E1"),
        )])
        fig.update_layout(**self.base, title=dict(text="Güvenlik", font=dict(size=12, color="#64748B"), x=0.5),
            height=200, showlegend=False,
            annotations=[dict(text=icon, x=0.5, y=0.5, font=dict(size=32, color=color), showarrow=False)])
        return self._to_html(fig)