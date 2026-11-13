"""CoreSync AI - entry point.

Run with:  .venv\\Scripts\\python -m streamlit run app.py
"""

import streamlit as st

from core.db import init_db
from ui.auth_page import render_auth_page

st.set_page_config(page_title="CoreSync AI", page_icon="💪", layout="wide")


@st.cache_resource
def _startup() -> bool:
    """Runs once per server start: migrate the database and seed data."""
    init_db()
    return True


_startup()

if st.session_state.get("user_id") is None:
    render_auth_page()
    st.stop()


def home() -> None:
    st.title(f"Welcome, {st.session_state.username} 👋")
    st.info(
        "More features are on the way: dashboard, profile and goals are coming next."
    )


with st.sidebar:
    st.caption(f"Signed in as **{st.session_state.username}**")
    if st.button("Log out", width="stretch"):
        st.session_state.clear()
        st.rerun()

st.navigation([st.Page(home, title="Home", icon=":material/home:")]).run()
