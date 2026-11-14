"""Placeholder pages for features that are not built yet."""

from __future__ import annotations

from collections.abc import Callable

import streamlit as st


def placeholder_page(title: str, description: str) -> Callable[[], None]:
    """Return a page function that shows a 'coming soon' message."""

    def render() -> None:
        st.title(title)
        st.info(f"Coming soon: {description}")

    return render
