"""Login / sign-up screen."""

from __future__ import annotations

import streamlit as st

from core.auth import AuthError, authenticate, create_user
from core.db import session_scope


def _sign_in(user_id: int, username: str) -> None:
    st.session_state.user_id = user_id
    st.session_state.username = username
    st.rerun()


def render_auth_page() -> None:
    _, center, _ = st.columns([1, 1.2, 1])
    with center:
        st.title("💪 CoreSync AI")
        st.caption("Training, nutrition and an AI coach in one place.")

        login_tab, signup_tab = st.tabs(["Log in", "Sign up"])

        with login_tab:
            with st.form("login_form"):
                username = st.text_input("Username")
                password = st.text_input("Password", type="password")
                submitted = st.form_submit_button("Log in", type="primary", width="stretch")
            if submitted:
                with session_scope() as session:
                    user = authenticate(session, username, password)
                    found = (user.id, user.username) if user else None
                if found:
                    _sign_in(*found)
                else:
                    st.error("Wrong username or password.")

        with signup_tab:
            with st.form("signup_form"):
                new_username = st.text_input("Choose a username")
                new_password = st.text_input("Choose a password", type="password",
                                             help="At least 8 characters.")
                confirm = st.text_input("Confirm password", type="password")
                created = st.form_submit_button("Create account", type="primary", width="stretch")
            if created:
                if new_password != confirm:
                    st.error("Passwords don't match.")
                else:
                    try:
                        with session_scope() as session:
                            user = create_user(session, new_username, new_password)
                            new = (user.id, user.username)
                    except AuthError as e:
                        st.error(str(e))
                    else:
                        _sign_in(*new)
