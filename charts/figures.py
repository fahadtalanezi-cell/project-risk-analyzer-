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


def evm_value_chart(evm_metrics, title, dark_mode):
    values = evm_metrics.get("values", {})
    labels = ["BAC", "PV", "EV", "AC"]
    raw_values = [values.get("bac"), values.get("pv"), values.get("ev"), values.get("ac")]
    chart_values = [value for value in raw_values if value is not None]
    chart_labels = [label for label, value in zip(labels, raw_values) if value is not None]
    if not chart_values:
        chart_labels, chart_values = ["No EVM source values"], [0]
    fig = px.bar(
        x=chart_labels,
        y=chart_values,
        text=[f"{value:,.0f}" for value in chart_values],
        color=chart_values,
        color_continuous_scale=["#ddd6fe", "#a78bfa", "#5b21b6"],
        title=title,
        labels={"x": "EVM Measure", "y": "Value"},
    )
    fig.update_traces(marker_line_width=0, textposition="outside")
    return apply_layout(fig, dark_mode, 340)


def evm_variance_chart(evm_metrics, title, dark_mode):
    values = evm_metrics.get("values", {})
    sv = values.get("sv")
    cv = values.get("cv")
    labels = ["SV", "CV"]
    raw_values = [sv, cv]
    chart_values = [value for value in raw_values if value is not None]
    chart_labels = [label for label, value in zip(labels, raw_values) if value is not None]
    if not chart_values:
        chart_labels, chart_values = ["No variance data"], [0]
    colors = ["#a78bfa" if value >= 0 else "#7c3aed" for value in chart_values]
    fig = go.Figure(go.Bar(
        x=chart_labels,
        y=chart_values,
        marker_color=colors,
        text=[f"{value:,.0f}" for value in chart_values],
        textposition="outside",
    ))
    fig.update_layout(title=title, yaxis_title="Variance")
    fig.add_hline(y=0, line_dash="dot", line_color="#ddd6fe")
    return apply_layout(fig, dark_mode, 320)


def evm_indices_chart(evm_metrics, title, dark_mode):
    values = evm_metrics.get("values", {})
    labels = ["SPI", "CPI", "TCPI"]
    raw_values = [values.get("spi"), values.get("cpi"), values.get("tcpi")]
    chart_values = [value for value in raw_values if value is not None]
    chart_labels = [label for label, value in zip(labels, raw_values) if value is not None]
    if not chart_values:
        chart_labels, chart_values = ["No index data"], [0]
    fig = go.Figure(go.Bar(
        x=chart_labels,
        y=chart_values,
        marker_color=["#a78bfa", "#7c3aed", "#5b21b6"][: len(chart_values)],
        text=[f"{value:.2f}" for value in chart_values],
        textposition="outside",
    ))
    fig.add_hline(y=1, line_dash="dash", line_color="#ddd6fe")
    fig.update_layout(title=title, yaxis_title="Performance Index", yaxis_range=[0, max(1.25, max(chart_values) + 0.2)])
    return apply_layout(fig, dark_mode, 320)


def evm_forecast_chart(evm_metrics, title, dark_mode):
    values = evm_metrics.get("values", {})
    labels = ["BAC", "EAC", "ETC", "VAC"]
    raw_values = [values.get("bac"), values.get("eac"), values.get("etc"), values.get("vac")]
    chart_values = [value for value in raw_values if value is not None]
    chart_labels = [label for label, value in zip(labels, raw_values) if value is not None]
    if not chart_values:
        chart_labels, chart_values = ["No forecast data"], [0]
    fig = go.Figure(go.Waterfall(
        name="EVM Forecast",
        orientation="v",
        measure=["absolute"] * len(chart_values),
        x=chart_labels,
        y=chart_values,
        connector={"line": {"color": "#a78bfa"}},
        increasing={"marker": {"color": "#7c3aed"}},
        decreasing={"marker": {"color": "#312e81"}},
        totals={"marker": {"color": "#a78bfa"}},
    ))
    fig.update_layout(title=title, yaxis_title="Forecast Value")
    return apply_layout(fig, dark_mode, 340)


def s_curve_chart(s_curve_df, title, dark_mode):
    fig = go.Figure()
    if s_curve_df is None or s_curve_df.empty:
        fig.add_annotation(text="Not enough schedule data", showarrow=False, x=0.5, y=0.5)
        fig.update_xaxes(visible=False)
        fig.update_yaxes(visible=False)
    else:
        fig.add_trace(go.Scatter(x=s_curve_df["period"], y=s_curve_df["PV"], mode="lines+markers", name="PV", line={"color": "#a78bfa", "width": 3}))
        fig.add_trace(go.Scatter(x=s_curve_df["period"], y=s_curve_df["EV"], mode="lines+markers", name="EV", line={"color": "#7c3aed", "width": 3}))
        fig.add_trace(go.Scatter(x=s_curve_df["period"], y=s_curve_df["AC"], mode="lines+markers", name="AC", line={"color": "#ddd6fe", "width": 3}))
        fig.update_layout(xaxis_title="Period", yaxis_title="Cumulative Value")
    fig.update_layout(title=title)
    return apply_layout(fig, dark_mode, 380)


def float_analysis_chart(float_df, title, dark_mode):
    if float_df is None or float_df.empty:
        fig = go.Figure()
        fig.add_annotation(text="Not enough schedule data", showarrow=False, x=0.5, y=0.5)
        fig.update_xaxes(visible=False)
        fig.update_yaxes(visible=False)
        fig.update_layout(title=title)
        return apply_layout(fig, dark_mode, 340)
    df = float_df.sort_values("total_float", ascending=True).head(15)
    fig = px.bar(
        df,
        x="total_float",
        y="activity",
        orientation="h",
        color="is_critical",
        color_discrete_map={True: "#ddd6fe", False: "#7c3aed"},
        title=title,
        hover_data=["ES", "EF", "LS", "LF"],
    )
    fig.update_layout(xaxis_title="Total Float", yaxis_title="")
    return apply_layout(fig, dark_mode, 360)


def milestone_slippage_chart(milestone_df, title, dark_mode):
    if milestone_df is None or milestone_df.empty:
        fig = go.Figure()
        fig.add_annotation(text="Not enough schedule data", showarrow=False, x=0.5, y=0.5)
        fig.update_xaxes(visible=False)
        fig.update_yaxes(visible=False)
        fig.update_layout(title=title)
        return apply_layout(fig, dark_mode, 340)
    df = milestone_df.sort_values("slippage_days", ascending=True)
    fig = px.bar(
        df,
        x="slippage_days",
        y="milestone",
        orientation="h",
        color="status",
        color_discrete_map={"On Time": "#a78bfa", "At Risk": "#7c3aed", "Delayed": "#4c1d95"},
        title=title,
        hover_data=["planned_date", "actual_or_forecast_date"],
    )
    fig.add_vline(x=0, line_dash="dot", line_color="#ddd6fe")
    fig.update_layout(xaxis_title="Slippage Days", yaxis_title="")
    return apply_layout(fig, dark_mode, 340)


def finish_forecast_chart(schedule_metrics, title, dark_mode):
    forecast = schedule_metrics.get("forecast", {})
    baseline = forecast.get("baseline_finish")
    projected = forecast.get("forecast_finish")
    fig = go.Figure()
    if not baseline or not projected:
        fig.add_annotation(text="Not enough schedule data", showarrow=False, x=0.5, y=0.5)
        fig.update_xaxes(visible=False)
        fig.update_yaxes(visible=False)
    else:
        fig.add_trace(go.Bar(x=["Baseline Finish", "Forecast Finish"], y=[1, 1], marker_color=["#a78bfa", "#7c3aed"], text=[str(baseline)[:10], str(projected)[:10]], textposition="inside"))
        fig.update_yaxes(visible=False)
        fig.update_layout(xaxis_title=f"Forecast delay: {forecast.get('forecast_delay_days')} days")
    fig.update_layout(title=title)
    return apply_layout(fig, dark_mode, 280)
