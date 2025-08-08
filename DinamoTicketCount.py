import streamlit as st
import pandas as pd
import json
import os

st.set_page_config(page_title="Dinamo Seat Checker", layout="wide")
st.title("💺 Dinamo Ticket Seat Checker")
st.write("Automatically checks available and taken seats for upcoming matches on the official GNK Dinamo ticketing website.")

# Load latest results
if os.path.exists("results.json"):
    with open("results.json") as f:
        data = json.load(f)
    results = data.get("results", [])
    last_checked = data.get("last_checked", "")
else:
    results = []
    last_checked = ""

def style_table(df):
    def color_available(val, total):
        if total == 0:
            return "background-color: lightgray"
        elif val == 0:
            return "background-color: #ff4b4b"
        elif val / total < 0.3:
            return "background-color: #ffd166"
        else:
            return "background-color: #06d6a0"

    styled_df = df.style
    if "Available" in df.columns and "Total" in df.columns:
        styled_df = styled_df.apply(
            lambda row: [
                color_available(row["Available"], row["Total"]) if col == "Available" else ""
                for col in df.columns
            ],
            axis=1
        )
    styled_df = styled_df.set_table_styles(
        [{
            'selector': 'th',
            'props': [('background-color', '#118ab2'), ('color', 'white')]
        }]
    )
    return styled_df

if results:
    st.success(f"✅ Found seat data for {len(results)} sector(s). (Last checked: {last_checked})")
    df = pd.DataFrame(results)
    st.write("Results table:")
    st.dataframe(style_table(df), use_container_width=True)
else:
    st.warning("⚠️ No results found.")

st.write("This page auto-updates every 2 minutes. Data is fetched in the background.")
