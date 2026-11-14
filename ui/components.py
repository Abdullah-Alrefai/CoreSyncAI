"""Reusable UI building blocks. Native Streamlit (plus Plotly for charts) only."""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st
from streamlit.delta_generator import DeltaGenerator

# Fixed colors per macro so they read the same on every page.
MACRO_COLORS = {"Protein": "#3B82F6", "Carbs": "#F59E0B", "Fat": "#A855F7"}
_TEXT_COLOR = "#E6E8EC"
_MUTED_COLOR = "#9AA3B2"


def section(title: str, caption: str | None = None, *, border: bool = True) -> DeltaGenerator:
    """A titled card. Use as `with section("Title"): ...`."""
    box = st.container(border=border)
    box.subheader(title)
    if caption:
        box.caption(caption)
    return box


def stat_card(label: str, value: str, *, delta: str | None = None,
              delta_color: str = "normal", help: str | None = None,
              caption: str | None = None) -> None:
    """A single number in a bordered card.

    delta_color: "normal" (up is green), "inverse" (down is green) or "off".
    """
    with st.container(border=True):
        st.metric(label, value, delta=delta, delta_color=delta_color, help=help)
        if caption:
            st.caption(caption)


def macro_ring(protein_g: float, carbs_g: float, fat_g: float, *,
               center_label: str | None = None, height: int = 220) -> None:
    """Donut of where the calories come from (protein/carbs 4 kcal/g, fat 9)."""
    kcal = {"Protein": protein_g * 4, "Carbs": carbs_g * 4, "Fat": fat_g * 9}
    grams = {"Protein": protein_g, "Carbs": carbs_g, "Fat": fat_g}
    if sum(kcal.values()) <= 0:
        empty_state("No macro targets yet.")
        return

    names = list(kcal)
    fig = go.Figure(go.Pie(
        labels=names,
        values=[kcal[n] for n in names],
        customdata=[grams[n] for n in names],
        hole=0.68,
        sort=False,
        direction="clockwise",
        marker={"colors": [MACRO_COLORS[n] for n in names], "line": {"width": 0}},
        texttemplate="%{percent:.0%}",
        textfont={"color": "#FFFFFF", "size": 12},
        hovertemplate="%{label}: %{customdata:.0f} g (%{value:.0f} kcal)<extra></extra>",
    ))
    fig.update_layout(
        height=height,
        margin={"t": 10, "b": 10, "l": 10, "r": 10},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"family": "Inter, sans-serif", "color": _TEXT_COLOR},
        legend={"orientation": "v", "x": 1.0, "y": 0.5, "font": {"color": _MUTED_COLOR}},
        annotations=[{"text": center_label, "showarrow": False,
                      "font": {"size": 16, "color": _TEXT_COLOR}}] if center_label else [],
    )
    st.plotly_chart(fig, config={"displayModeBar": False}, width="stretch")


def empty_state(message: str, *, hint: str | None = None,
                icon: str = ":material/inbox:") -> None:
    """A friendly placeholder for when there is nothing to show yet."""
    with st.container(border=True):
        st.markdown(f"{icon} **{message}**")
        if hint:
            st.caption(hint)


def entry_row(title: str, *, key: str, subtitle: str | None = None,
              value: str | None = None, deletable: bool = True) -> bool:
    """One line in a list (e.g. a weigh-in). Returns True if its delete button was clicked."""
    with st.container(border=True):
        text, amount, action = st.columns([5, 3, 1], vertical_alignment="center")
        text.markdown(f"**{title}**")
        if subtitle:
            text.caption(subtitle)
        if value:
            amount.markdown(value)
        if deletable:
            return action.button(":material/delete:", key=key, help="Delete", type="tertiary")
    return False
