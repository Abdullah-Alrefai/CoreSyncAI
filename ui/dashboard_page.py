"""Dashboard (Phase 1 version): weight trend and daily targets.

The full dashboard (food rings, workouts, streak) comes after workouts are built.
"""

from __future__ import annotations

import datetime as dt

import pandas as pd
import streamlit as st
from streamlit.navigation.page import StreamlitPage

from core import constants as C
from core.db import session_scope
from core.services import profile as P
from ui.components import empty_state, macro_ring, section, stat_card

# Is a weight drop good news? Depends on the goal.
_DELTA_COLOR = {"cut": "inverse", "bulk": "normal", "maintain": "off"}
_RANGES = {"30 days": 30, "90 days": 90, "All": None}


def _load(user_id: int):
    with session_scope() as s:
        profile = P.get_profile(s, user_id)
        weights = P.list_weights(s, user_id)
    return profile, weights


def _fmt_change(change: float | None) -> str:
    return "—" if change is None else f"{change:+.1f} lb"


def _days_ago(day: dt.date, today: dt.date) -> str:
    n = (today - day).days
    return {0: "Today", 1: "Yesterday"}.get(n, f"{n} days ago")


def _stat_row(profile, weights, today: dt.date) -> None:
    color = _DELTA_COLOR.get(profile.goal, "off")
    latest = weights[-1] if weights else None
    week = P.weight_change(weights, 7, today)
    month = P.weight_change(weights, 30, today)

    cols = st.columns(4)
    with cols[0]:
        stat_card("Current weight", f"{latest.weight_lb:.1f} lb" if latest else "—",
                  delta=_fmt_change(week) + " this week" if week is not None else None,
                  delta_color=color)
    with cols[1]:
        stat_card("30-day change", _fmt_change(month),
                  caption="First vs. latest weigh-in this month")
    with cols[2]:
        stat_card("Last weigh-in", _days_ago(latest.date, today) if latest else "—",
                  caption=f"{latest.date:%b %d}" if latest else "No weigh-ins yet")
    with cols[3]:
        kcal = profile.calorie_target
        stat_card("Daily calories", f"{kcal:,}" if kcal else "—",
                  caption=f"kcal target · {C.GOALS.get(profile.goal, 'No goal')}")


def _weight_trend(weights, today: dt.date, profile_page: StreamlitPage) -> None:
    with section("Weight trend"):
        if not weights:
            empty_state("No weigh-ins yet.", hint="Log your weight to start your trend.",
                        icon=":material/monitor_weight:")
            st.page_link(profile_page, label="Log a weigh-in", icon=":material/add:")
            return

        choice = st.segmented_control("Range", list(_RANGES), default="30 days",
                                      label_visibility="collapsed") or "30 days"
        days = _RANGES[choice]
        shown = [w for w in weights
                 if days is None or w.date >= today - dt.timedelta(days=days)]
        if len(shown) < 2:
            empty_state("Not enough weigh-ins in this range yet.",
                        hint="Your trend line appears after two weigh-ins.",
                        icon=":material/show_chart:")
            return
        df = pd.DataFrame({"Date": [w.date for w in shown],
                           "Weight (lb)": [w.weight_lb for w in shown]})
        st.line_chart(df, x="Date", y="Weight (lb)", color="#3B82F6", height=320)


def _targets(profile, profile_page: StreamlitPage) -> None:
    with section("Daily targets"):
        protein, carbs, fat = (profile.protein_target_g, profile.carbs_target_g,
                               profile.fat_target_g)
        if not (protein or carbs or fat):
            empty_state("No targets set yet.",
                        hint="Fill in your body stats and weight to get suggested targets.",
                        icon=":material/flag:")
        else:
            label = f"{profile.calorie_target:,}<br>kcal" if profile.calorie_target else None
            macro_ring(protein or 0, carbs or 0, fat or 0, center_label=label)
            st.caption(f"{protein or 0:.0f} g protein · {carbs or 0:.0f} g carbs · "
                       f"{fat or 0:.0f} g fat")
        st.page_link(profile_page, label="Edit profile & targets", icon=":material/edit:")


def render_dashboard(profile_page: StreamlitPage) -> None:
    today = dt.date.today()
    st.title("Dashboard")
    st.caption(f"Welcome back, {st.session_state.username}. {today:%A, %B %d}")

    profile, weights = _load(st.session_state.user_id)
    _stat_row(profile, weights, today)

    left, right = st.columns([3, 2], gap="large")
    with left:
        _weight_trend(weights, today, profile_page)
    with right:
        _targets(profile, profile_page)
