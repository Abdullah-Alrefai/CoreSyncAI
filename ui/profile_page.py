"""Profile & goals: body stats, daily targets and weigh-ins."""

from __future__ import annotations

import datetime as dt

import pandas as pd
import streamlit as st

from core import constants as C
from core.db import session_scope
from core.services import profile as P
from ui.components import empty_state, entry_row, macro_ring, section, stat_card

_FLASH_KEY = "_profile_flash"
_RECENT_WEIGH_INS = 10


def _flash(message: str) -> None:
    """Show a success message after the next rerun."""
    st.session_state[_FLASH_KEY] = message
    st.rerun()


def _load(user_id: int):
    with session_scope() as s:
        profile = P.get_profile(s, user_id)
        weight = P.latest_weight(s, user_id)
        weights = P.list_weights(s, user_id)
    return profile, weight, weights


def _index(options: list[str], value: str | None) -> int | None:
    return options.index(value) if value in options else None


def _body_stats_form(user_id: int, profile) -> None:
    sexes = list(C.SEXES)
    levels = list(C.ACTIVITY_LEVELS)
    goals = list(C.GOALS)
    feet, inches = (divmod(round(profile.height_in), 12) if profile.height_in else (None, None))
    today = dt.date.today()

    with section("Body stats", "Used to estimate how many calories you burn."):
        with st.form("body_stats", border=False):
            c1, c2 = st.columns(2)
            sex = c1.selectbox("Sex", sexes, index=_index(sexes, profile.sex),
                               format_func=C.SEXES.get, placeholder="Choose...")
            birth_date = c2.date_input("Birth date", value=profile.birth_date,
                                       min_value=dt.date(1920, 1, 1), max_value=today)
            c3, c4 = st.columns(2)
            ft = c3.number_input("Height (ft)", min_value=3, max_value=8, value=feet, step=1)
            inch = c4.number_input("Height (in)", min_value=0, max_value=11, value=inches, step=1)
            activity = st.selectbox("Activity level", levels,
                                    index=_index(levels, profile.activity_level),
                                    format_func=lambda k: C.ACTIVITY_LEVELS[k][0],
                                    placeholder="Choose...")
            goal = st.selectbox("Goal", goals, index=_index(goals, profile.goal) or 0,
                                format_func=C.GOALS.get)
            saved = st.form_submit_button("Save body stats", type="primary")

    if saved:
        height = ft * 12 + (inch or 0) if ft else None
        with session_scope() as s:
            P.update_profile(s, user_id, sex=sex, birth_date=birth_date, height_in=height,
                             activity_level=activity, goal=goal)
        _flash("Body stats saved.")


def _numbers(plan: P.Plan) -> None:
    if not plan.ok:
        empty_state("We need a bit more info to calculate your numbers.",
                    hint="Missing: " + ", ".join(plan.missing)
                    + ". Weight comes from your latest weigh-in.",
                    icon=":material/calculate:")
        return
    cols = st.columns(3)
    with cols[0]:
        stat_card("At rest (BMR)", f"{plan.bmr:,.0f}", caption="kcal / day")
    with cols[1]:
        stat_card("Daily burn (TDEE)", f"{plan.tdee:,.0f}", caption="kcal / day")
    with cols[2]:
        stat_card("Suggested", f"{plan.targets.kcal:,}", caption="kcal / day for your goal")


def _targets_form(user_id: int, profile, plan: P.Plan) -> None:
    suggested = plan.targets

    def default(saved, attr):
        if saved is not None:
            return float(saved)
        return float(getattr(suggested, attr)) if suggested else None

    with section("Daily targets", "Edit them freely, or reset to the suggestion."):
        with st.form("targets", border=False):
            cols = st.columns(4)
            kcal = cols[0].number_input("Calories", min_value=0.0, step=50.0, format="%.0f",
                                        value=default(profile.calorie_target, "kcal"))
            protein = cols[1].number_input("Protein (g)", min_value=0.0, step=5.0, format="%.0f",
                                           value=default(profile.protein_target_g, "protein_g"))
            carbs = cols[2].number_input("Carbs (g)", min_value=0.0, step=5.0, format="%.0f",
                                         value=default(profile.carbs_target_g, "carbs_g"))
            fat = cols[3].number_input("Fat (g)", min_value=0.0, step=5.0, format="%.0f",
                                       value=default(profile.fat_target_g, "fat_g"))
            b1, b2 = st.columns(2)
            save = b1.form_submit_button("Save targets", type="primary", width="stretch")
            use_suggested = b2.form_submit_button("Use suggested", disabled=suggested is None,
                                                  width="stretch")

        if profile.protein_target_g or profile.carbs_target_g or profile.fat_target_g:
            label = f"{profile.calorie_target:,}<br>kcal" if profile.calorie_target else None
            macro_ring(profile.protein_target_g or 0, profile.carbs_target_g or 0,
                       profile.fat_target_g or 0, center_label=label)

    if save:
        with session_scope() as s:
            P.update_profile(s, user_id,
                             calorie_target=round(kcal) if kcal is not None else None,
                             protein_target_g=protein, carbs_target_g=carbs, fat_target_g=fat)
        _flash("Targets saved.")
    if use_suggested:
        with session_scope() as s:
            P.apply_suggested_targets(s, user_id)
        _flash("Suggested targets applied.")


def _log_weight_form(user_id: int) -> None:
    with st.form("weigh_in", clear_on_submit=True, border=False):
        c1, c2, c3 = st.columns(3)
        day = c1.date_input("Date", value=dt.date.today(), max_value=dt.date.today())
        weight = c2.number_input("Weight (lb)", min_value=50.0, max_value=700.0,
                                 value=None, step=0.1, format="%.1f")
        body_fat = c3.number_input("Body fat % (optional)", min_value=1.0, max_value=70.0,
                                   value=None, step=0.1, format="%.1f")
        logged = st.form_submit_button("Log weight", type="primary")

    if logged:
        if weight is None:
            st.error("Enter your weight.")
        else:
            with session_scope() as s:
                P.log_weight(s, user_id, day, weight, body_fat)
            _flash(f"Logged {weight:.1f} lb for {day:%b %d}.")


def _weigh_ins(user_id: int, weights) -> None:
    with section("Weigh-ins", "One per day; logging the same day again replaces it."):
        _log_weight_form(user_id)

        if not weights:
            empty_state("No weigh-ins yet.", hint="Log your first weight above.",
                        icon=":material/monitor_weight:")
            return

        chart_col, list_col = st.columns([3, 2], gap="large")
        with chart_col:
            if len(weights) > 1:
                df = pd.DataFrame({"Date": [w.date for w in weights],
                                   "Weight (lb)": [w.weight_lb for w in weights]})
                st.line_chart(df, x="Date", y="Weight (lb)", height=300)
            else:
                empty_state("Your trend appears after two weigh-ins.",
                            icon=":material/show_chart:")
        with list_col:
            st.caption(f"Recent (last {_RECENT_WEIGH_INS})")
            for w in reversed(weights[-_RECENT_WEIGH_INS:]):
                fat = f" · {w.body_fat_pct:.1f}% fat" if w.body_fat_pct else ""
                if entry_row(f"{w.date:%a, %b %d %Y}", key=f"del_weight_{w.id}",
                             value=f"**{w.weight_lb:.1f}** lb{fat}"):
                    with session_scope() as s:
                        P.delete_weight(s, user_id, w.id)
                    _flash("Weigh-in deleted.")


def render_profile_page() -> None:
    st.title("Profile & Goals")
    if message := st.session_state.pop(_FLASH_KEY, None):
        st.toast(message, icon=":material/check_circle:")

    user_id = st.session_state.user_id
    profile, weight, weights = _load(user_id)
    plan = P.compute_plan(profile, weight, dt.date.today())

    # Full width so the numbers have room (they get cut off in a half column).
    _numbers(plan)
    left, right = st.columns(2, gap="large")
    with left:
        _body_stats_form(user_id, profile)
    with right:
        _targets_form(user_id, profile, plan)
    _weigh_ins(user_id, weights)
