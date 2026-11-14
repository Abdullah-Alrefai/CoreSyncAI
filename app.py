"""CoreSync AI - entry point.

Run with:  .venv\\Scripts\\python -m streamlit run app.py
"""

import streamlit as st

from core.db import init_db
from ui.auth_page import render_auth_page
from ui.dashboard_page import render_dashboard
from ui.placeholder import placeholder_page
from ui.profile_page import render_profile_page

st.set_page_config(page_title="CoreSync AI", page_icon="💪", layout="wide")


@st.cache_resource
def _startup() -> bool:
    """Runs once per server start: migrate the database and seed data."""
    init_db()
    return True


_startup()

if st.session_state.get("user_id") is None:
    # Replace the menu with a single hidden login page, so the signed-in
    # menu doesn't linger in the sidebar after logging out.
    st.navigation([st.Page(render_auth_page, title="Log in", icon=":material/login:")],
                  position="hidden").run()
    st.stop()


profile_page = st.Page(render_profile_page, title="Profile & Goals", icon=":material/person:",
                       url_path="profile")
pages = [
    st.Page(lambda: render_dashboard(profile_page), title="Dashboard",
            icon=":material/dashboard:", url_path="dashboard", default=True),
    profile_page,
    st.Page(placeholder_page("Nutrition", "food search, meal diary and nutrition analytics."),
            title="Nutrition", icon=":material/restaurant:", url_path="nutrition"),
    st.Page(placeholder_page("Workouts", "workout logging, templates and cardio."),
            title="Workouts", icon=":material/fitness_center:", url_path="workouts"),
    st.Page(placeholder_page("Progress", "strength charts, personal records and the body map."),
            title="Progress", icon=":material/trending_up:", url_path="progress"),
    st.Page(placeholder_page("AI Coach", "chat with an AI coach that knows your data."),
            title="AI Coach", icon=":material/smart_toy:", url_path="coach"),
]

with st.sidebar:
    st.caption(f"Signed in as **{st.session_state.username}**")
    if st.button("Log out", width="stretch"):
        st.session_state.clear()
        st.rerun()

st.navigation(pages).run()
