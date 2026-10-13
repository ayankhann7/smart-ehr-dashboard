"""Plotly figure builders. Every function takes already-computed data and returns a figure.

Charts use titles, axis labels and hover text; colour is never the only cue (legends are labelled,
lines use different dash styles and grouped bars use patterns). Layouts are responsive.
"""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

TEAL, BLUE, TEXT, MUTED, BORDER = "#0F766E", "#2563EB", "#172B4D", "#64748B", "#E2E8F0"
PALETTE = [TEAL, BLUE, "#D97706", "#7C3AED", "#0891B2", "#DC2626", "#15803D", "#64748B"]
DASHES = ["solid", "dash", "dot", "dashdot", "longdash", "longdashdot"]
CHART_CONFIG = {"displaylogo": False, "responsive": True, "modeBarButtonsToRemove": ["lasso2d", "select2d"]}


def _short(text, n: int = 38) -> str:
    text = str(text)
    return text if len(text) <= n else text[: n - 1] + "…"


def _style(fig: go.Figure, title: str, x_title: str | None = None, y_title: str | None = None,
           height: int = 340, legend: bool = True) -> go.Figure:
    fig.update_layout(
        title=dict(text=title, x=0, xanchor="left", font=dict(size=15, color=TEXT)),
        font=dict(family="Inter, Segoe UI, Arial, sans-serif", color=TEXT, size=12),
        paper_bgcolor="white", plot_bgcolor="white", autosize=True, height=height,
        margin=dict(l=8, r=8, t=48, b=8), showlegend=legend,
        legend=dict(orientation="h", yanchor="top", y=-0.22, xanchor="left", x=0, font=dict(size=11)),
        hoverlabel=dict(font_size=12))
    fig.update_xaxes(title_text=x_title, gridcolor=BORDER, automargin=True, linecolor=BORDER)
    fig.update_yaxes(title_text=y_title, gridcolor=BORDER, automargin=True, linecolor=BORDER)
    return fig


def empty_figure(title: str, message: str = "No data for the current filters") -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(text=message, x=0.5, y=0.5, xref="paper", yref="paper", showarrow=False,
                       font=dict(size=14, color=MUTED))
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    return _style(fig, title, height=240, legend=False)


def age_histogram(ages: pd.Series, bin_size: int = 5) -> go.Figure:
    title = "Patient age distribution"
    ages = ages.dropna()
    if ages.empty:
        return empty_figure(title, "No valid ages for the current filters")
    fig = px.histogram(pd.DataFrame({"age": ages}), x="age")
    fig.update_traces(xbins=dict(start=0, size=bin_size), marker_color=TEAL, marker_line_color="white",
                      marker_line_width=1, hovertemplate="Age %{x} years<br>Patients: %{y:,}<extra></extra>")
    return _style(fig, title, "Age (years)", "Patients", legend=False)


def age_group_bar(df: pd.DataFrame) -> go.Figure:
    title = "Patients by age group"
    if df.empty or df["patients"].sum() == 0:
        return empty_figure(title)
    fig = go.Figure(go.Bar(x=df["age_group"], y=df["patients"], marker_color=TEAL, text=df["patients"],
                           textposition="outside", customdata=df["percent"],
                           hovertemplate="%{x}: %{y:,} patients (%{customdata}%)<extra></extra>"))
    return _style(fig, title, "Age group (years)", "Patients", legend=False)


def donut(df: pd.DataFrame, label_col: str, value_col: str, title: str, unit: str = "patients") -> go.Figure:
    if df.empty:
        return empty_figure(title)
    fig = go.Figure(go.Pie(labels=df[label_col].astype(str), values=df[value_col], hole=0.55, sort=False,
                           marker=dict(colors=PALETTE, line=dict(color="white", width=2)),
                           textinfo="label+percent", textposition="outside",
                           hovertemplate=f"%{{label}}: %{{value:,}} {unit} (%{{percent}})<extra></extra>"))
    return _style(fig, title, height=340)


def category_bar(df: pd.DataFrame, category: str, title: str, value_col: str = "patients",
                 y_title: str = "Patients") -> go.Figure:
    if df.empty:
        return empty_figure(title)
    fig = go.Figure(go.Bar(x=df[category].astype(str), y=df[value_col], marker_color=BLUE, text=df[value_col],
                           textposition="outside",
                           hovertemplate="%{x}: %{y:,}<extra></extra>"))
    return _style(fig, title, category.replace("_", " ").title(), y_title, legend=False)


def horizontal_bar(df: pd.DataFrame, label_col: str, value_col: str, title: str, x_title: str) -> go.Figure:
    if df.empty:
        return empty_figure(title)
    d = df.sort_values(value_col, ascending=True)
    fig = go.Figure(go.Bar(x=d[value_col], y=[_short(v) for v in d[label_col]], orientation="h",
                           marker_color=TEAL, text=d[value_col], textposition="outside", cliponaxis=False,
                           customdata=d[label_col],
                           hovertemplate="%{customdata}<br>" + x_title + ": %{x:,}<extra></extra>"))
    fig = _style(fig, title, x_title, None, height=max(300, 30 * len(d) + 110), legend=False)
    fig.update_layout(margin=dict(l=8, r=30, t=48, b=8))
    return fig


def time_series(df: pd.DataFrame, value_col: str, title: str, y_title: str, kind: str = "line") -> go.Figure:
    if df.empty:
        return empty_figure(title, "No dated records for the current filters")
    label = df["period_label"]
    if kind == "bar":
        fig = go.Figure(go.Bar(x=df["period"], y=df[value_col], marker_color=TEAL, customdata=label,
                               hovertemplate="%{customdata}: %{y:,}<extra></extra>"))
    else:
        mode = "lines+markers" if len(df) <= 60 else "lines"
        fig = go.Figure(go.Scatter(x=df["period"], y=df[value_col], mode=mode, line=dict(color=TEAL, width=2),
                                   customdata=label, fill="tozeroy", fillcolor="rgba(15,118,110,0.08)",
                                   hovertemplate="%{customdata}: %{y:,}<extra></extra>"))
    return _style(fig, title, "Period", y_title, legend=False)


def multi_line(df: pd.DataFrame, group_col: str, value_col: str, title: str, y_title: str) -> go.Figure:
    if df.empty:
        return empty_figure(title, "No dated records for the current filters")
    fig = go.Figure()
    for i, (name, part) in enumerate(df.groupby(group_col, sort=True)):
        fig.add_trace(go.Scatter(x=part["period"], y=part[value_col], mode="lines", name=_short(name, 30),
                                 line=dict(color=PALETTE[i % len(PALETTE)], dash=DASHES[i % len(DASHES)], width=2),
                                 customdata=part["period_label"],
                                 hovertemplate=f"{name}<br>%{{customdata}}: %{{y:,}}<extra></extra>"))
    return _style(fig, title, "Period", y_title)


def grouped_bar(df: pd.DataFrame, category: str, group: str, value_col: str, title: str, y_title: str) -> go.Figure:
    if df.empty:
        return empty_figure(title)
    d = df.copy()
    d["label"] = d[category].map(_short)
    fig = px.bar(d, x="label", y=value_col, color=group, pattern_shape=group, barmode="group",
                 color_discrete_sequence=PALETTE, hover_data={category: True, "label": False})
    return _style(fig, title, category.replace("_", " ").title(), y_title, height=380)


def observation_bar(df: pd.DataFrame, description: str) -> go.Figure:
    title = f"Average {description} by age group"
    if df.empty:
        return empty_figure(title, "No numeric values for this measurement")
    unit = df["units"].iloc[0]
    fig = go.Figure(go.Bar(x=df["age_group"], y=df["mean"], marker_color=BLUE, customdata=df[["n", "median"]],
                           text=df["mean"], textposition="outside",
                           hovertemplate="%{x}<br>Mean: %{y}<br>Median: %{customdata[1]}<br>Records: %{customdata[0]:,}<extra></extra>"))
    return _style(fig, title, "Age group (years)", f"Mean ({unit})" if unit else "Mean", legend=False)


def patient_measurement_line(df: pd.DataFrame, description: str) -> go.Figure:
    title = f"{description} over time (this patient)"
    d = df.dropna(subset=["date", "value_numeric"]).sort_values("date")
    if d.empty:
        return empty_figure(title, "No dated numeric values")
    unit = d["units"].dropna().iloc[0] if "units" in d and d["units"].notna().any() else ""
    fig = go.Figure(go.Scatter(x=d["date"], y=d["value_numeric"], mode="lines+markers", line=dict(color=TEAL),
                               hovertemplate="%{x|%Y-%m-%d}: %{y}<extra></extra>"))
    return _style(fig, title, "Date", f"Value ({unit})" if unit else "Value", legend=False)
