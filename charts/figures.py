import plotly.express as px
import plotly.graph_objects as go


def palette(dark_mode):
    return {
        "template": "plotly_dark" if dark_mode else "plotly_white",
        "paper": "#0d1428" if dark_mode else "#ffffff",
        "plot": "#0b1022" if dark_mode else "#f7f4ff",
        "accent": "#a78bfa",
        "deep": "#5b21b6",
        "mid": "#7c3aed",
        "muted": "#312e81",
        "soft": "#ddd6fe",
        "text": "#f8fafc" if dark_mode else "#111827",
    }


def apply_layout(fig, dark_mode, height=360):
    colors = palette(dark_mode)
    fig.update_layout(
        template=colors["template"],
        height=height,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": colors["text"], "family": "Arial"},
        margin={"l": 20, "r": 20, "t": 56, "b": 28},
        transition={"duration": 450, "easing": "cubic-in-out"},
    )
    return fig


def risk_gauge(value, title, dark_mode):
    colors = palette(dark_mode)
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        number={"suffix": "/100"},
        title={"text": title},
        gauge={
            "axis": {"range": [0, 100]},
            "bar": {"color": colors["accent"]},
            "steps": [
                {"range": [0, 25], "color": "rgba(221,214,254,.18)"},
                {"range": [25, 50], "color": "rgba(167,139,250,.24)"},
                {"range": [50, 75], "color": "rgba(124,58,237,.32)"},
                {"range": [75, 100], "color": "rgba(91,33,182,.44)"},
            ],
        },
    ))
    return apply_layout(fig, dark_mode, 300)


def category_bar(risk_df, title, dark_mode):
    fig = px.bar(
        risk_df,
        x="category",
        y="score",
        color="score",
        color_continuous_scale=["#ddd6fe", "#a78bfa", "#5b21b6"],
        title=title,
        hover_data=["score"],
    )
    fig.update_traces(marker_line_width=0, texttemplate="%{y}", textposition="outside")
    return apply_layout(fig, dark_mode, 360)


def risk_heatmap(heatmap_df, title, labels, dark_mode):
    fig = px.scatter(
        heatmap_df,
        x="probability",
        y="impact",
        size="financial_impact",
        color="score",
        text="category",
        color_continuous_scale=["#ddd6fe", "#a78bfa", "#5b21b6"],
        title=title,
        labels={"probability": labels["probability"], "impact": labels["impact"], "financial_impact": labels["financial_impact"]},
        hover_data=["category", "score", "financial_impact"],
        size_max=60,
    )
    fig.update_xaxes(range=[0.5, 5.5], dtick=1)
    fig.update_yaxes(range=[0.5, 5.5], dtick=1)
    fig.update_traces(textposition="top center")
    return apply_layout(fig, dark_mode, 420)


def forecast_chart(forecast_df, title, dark_mode):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=forecast_df["period"], y=forecast_df["predicted_delay_days"], mode="lines+markers", name="Delay days"))
    fig.add_trace(go.Scatter(x=forecast_df["period"], y=forecast_df["budget_variance_pct"], mode="lines+markers", name="Budget variance %"))
    fig.add_trace(go.Scatter(x=forecast_df["period"], y=forecast_df["performance_index"], mode="lines+markers", name="Performance index"))
    fig.update_layout(title=title, xaxis_title="Period")
    return apply_layout(fig, dark_mode, 420)


def timeline_chart(timeline_df, title, dark_mode):
    color_map = {
        "Critical Path": "#a78bfa",
        "Delayed": "#7c3aed",
        "On Track": "#4c1d95",
        "المسار الحرج": "#a78bfa",
        "متأخر": "#7c3aed",
        "ضمن الخطة": "#4c1d95",
    }
    fig = px.timeline(
        timeline_df,
        x_start="start",
        x_end="finish",
        y="task",
        color="status",
        color_discrete_map=color_map,
        hover_data=["risk", "status"],
        title=title,
    )
    fig.update_yaxes(autorange="reversed")
    return apply_layout(fig, dark_mode, 420)


def resource_load_chart(timeline_df, title, dark_mode):
    df = timeline_df.copy()
    df["resource_load"] = (55 + df["risk"] * 0.55).clip(upper=100)
    fig = px.bar(
        df,
        x="task",
        y="resource_load",
        color="status",
        title=title,
        hover_data=["risk"],
        color_discrete_map={
            "Critical Path": "#a78bfa",
            "Delayed": "#7c3aed",
            "On Track": "#4c1d95",
            "المسار الحرج": "#a78bfa",
            "متأخر": "#7c3aed",
            "ضمن الخطة": "#4c1d95",
        },
    )
    fig.update_yaxes(range=[0, 100])
    return apply_layout(fig, dark_mode, 360)


def spi_cpi_trend(forecast_df, title, dark_mode):
    fig = go.Figure()
    spi = [round(max(0.55, 1 - v / 160), 2) for v in forecast_df["predicted_delay_days"]]
    cpi = [round(max(0.55, 1 - v / 130), 2) for v in forecast_df["budget_variance_pct"]]
    fig.add_trace(go.Scatter(x=forecast_df["period"], y=spi, mode="lines+markers", name="SPI", line={"color": "#a78bfa", "width": 3}))
    fig.add_trace(go.Scatter(x=forecast_df["period"], y=cpi, mode="lines+markers", name="CPI", line={"color": "#7c3aed", "width": 3}))
    fig.update_layout(title=title, yaxis_range=[0.5, 1.05], xaxis_title="Period")
    return apply_layout(fig, dark_mode, 320)


def budget_waterfall(metrics, title, dark_mode):
    variance = metrics.get("budget_variance", 0)
    fig = go.Figure(go.Waterfall(
        name="Budget",
        orientation="v",
        measure=["relative", "relative", "relative", "total"],
        x=["Baseline", "Procurement", "Scope", "Forecast"],
        y=[100, variance * 0.38, variance * 0.62, 0],
        connector={"line": {"color": "#a78bfa"}},
        increasing={"marker": {"color": "#7c3aed"}},
        decreasing={"marker": {"color": "#312e81"}},
        totals={"marker": {"color": "#a78bfa"}},
    ))
    fig.update_layout(title=title, yaxis_title="Budget exposure index")
    return apply_layout(fig, dark_mode, 320)


def resource_donut(timeline_df, title, dark_mode):
    df = timeline_df.copy()
    df["resource_load"] = (55 + df["risk"] * 0.55).clip(upper=100)
    fig = px.pie(
        df,
        names="task",
        values="resource_load",
        hole=0.58,
        title=title,
        color_discrete_sequence=["#ddd6fe", "#c4b5fd", "#a78bfa", "#8b5cf6", "#7c3aed", "#5b21b6"],
    )
    fig.update_traces(textposition="inside", textinfo="percent")
    return apply_layout(fig, dark_mode, 320)


def risk_radar(risk_df, title, dark_mode):
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=risk_df["score"],
        theta=risk_df["category"],
        fill="toself",
        name="Risk exposure",
        line={"color": "#a78bfa", "width": 3},
        fillcolor="rgba(124,58,237,.28)",
    ))
    fig.update_layout(title=title, polar={"radialaxis": {"visible": True, "range": [0, 100]}})
    return apply_layout(fig, dark_mode, 360)


def critical_task_ranking(timeline_df, title, dark_mode):
    df = timeline_df.sort_values("risk", ascending=True)
    fig = px.bar(
        df,
        x="risk",
        y="task",
        orientation="h",
        color="risk",
        color_continuous_scale=["#ddd6fe", "#a78bfa", "#5b21b6"],
        title=title,
        hover_data=["status"],
    )
    return apply_layout(fig, dark_mode, 340)


def milestone_tracking(timeline_df, title, dark_mode):
    df = timeline_df.copy()
    df["progress"] = (100 - df["risk"] * 0.55).clip(lower=35)
    fig = px.scatter(
        df,
        x="finish",
        y="progress",
        size="risk",
        color="status",
        text="task",
        title=title,
        color_discrete_map={
            "Critical Path": "#a78bfa",
            "Delayed": "#7c3aed",
            "On Track": "#4c1d95",
            "المسار الحرج": "#a78bfa",
            "متأخر": "#7c3aed",
            "ضمن الخطة": "#4c1d95",
        },
        hover_data=["risk"],
    )
    fig.update_traces(textposition="top center")
    fig.update_yaxes(range=[0, 105])
    return apply_layout(fig, dark_mode, 340)
