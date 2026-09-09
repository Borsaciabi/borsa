import pandas as pd
import streamlit as st


def signed_value_style(value):
    """Return a readable semantic style for positive and negative values."""
    try:
        numeric = float(str(value).replace("%", "").replace(",", "").strip())
    except (TypeError, ValueError):
        return ""
    if numeric > 0:
        return "color: #7ef2b5; background-color: rgba(22, 163, 74, .16); font-weight: 600"
    if numeric < 0:
        return "color: #ff9aa8; background-color: rgba(220, 38, 38, .16); font-weight: 600"
    return "color: #b5c2d0"


def render_signed_dataframe(frame: pd.DataFrame, columns, **kwargs):
    """Render a dataframe with green/red styling for signed numeric columns."""
    available = [column for column in columns if column in frame.columns]
    styled = frame.style.map(signed_value_style, subset=available) if available else frame
    st.dataframe(styled, **kwargs)
