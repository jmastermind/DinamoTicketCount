import streamlit as st
import csv
import io
import os
import subprocess
from datetime import datetime
from playwright.sync_api import sync_playwright
import time
import pandas as pd
import plotly.graph_objects as go  # <-- NEW

# ⬆️ Install Chromium browser if missing (for Streamlit Cloud)
if not os.path.exists("/home/appuser/.cache/ms-playwright"):
    try:
        subprocess.run(["playwright", "install", "chromium"], check=True)
    except Exception as e:
        print(f"Error installing Chromium: {e}")

st.set_page_config(page_title="Dinamo Seat Checker", layout="wide")  # <-- CHANGED to 'wide'
st.title("💺 Dinamo Ticket Seat Checker")
st.write("Automatically checks available and taken seats for upcoming matches on the official GNK Dinamo ticketing website.")

# Hardcoded credentials
email = "jakov.mandic.27@gmail.com"
password = "cfgdqverkt"

def fetch_seat_data(email, password):
    results = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto("https://tickets.gnkdinamo.hr/")

            # Login
            page.click("button:has-text('Prijava')")
            page.wait_for_selector("input[formcontrolname='username']")
            page.fill("input[formcontrolname='username']", email)
            page.fill("input[formcontrolname='password']", password)
            page.click("div.modal-container button:has-text('Prijava')")
            page.wait_for_timeout(3000)

            try:
                page.wait_for_selector("button.game", timeout=5000)
            except:
                browser.close()
                return []

            games = page.query_selector_all("button.game")
            if not games:
                browser.close()
                return []

            for index, game in enumerate(games):
                page.wait_for_selector("button.game")
                games = page.query_selector_all("button.game")
                current_game = games[index]

                date = current_game.query_selector(".date").inner_text() if current_game.query_selector(".date") else "N/A"
                time_ev = current_game.query_selector(".time").inner_text() if current_game.query_selector(".time") else "N/A"
                teams = " vs ".join([
                    t.inner_text() for t in current_game.query_selector_all(".team")
                ]) or "Unknown teams"

                current_game.click()
                page.wait_for_timeout(3000)

                headers = page.query_selector_all(".acc-header")
                for header in headers:
                    try:
                        header.click()
                        page.wait_for_timeout(500)
                    except:
                        pass

                sectors = page.query_selector_all("button.sector-button")
                if not sectors:
                    page.go_back()
                    page.wait_for_timeout(2000)
                    continue

                for i in range(len(sectors)):
                    sectors = page.query_selector_all("button.sector-button")
                    sector_button = sectors[i]

                    sector_name_el = sector_button.query_selector("p")
                    sector_name = sector_name_el.inner_text().strip() if sector_name_el else f"Sector {i+1}"

                    try:
                        sector_button.click()

                        for _ in range(16):
                            rects = page.query_selector_all("rect")
                            if len(rects) > 10:
                                break
                            page.wait_for_timeout(500)
                        else:
                            continue

                        taken = len([r for r in rects if 'occupied' in (r.get_attribute('class') or '')])
                        total = len(rects)
                        available = total - taken

                        if available == 0 and total > 0:
                            page.wait_for_timeout(1500)
                            rects = page.query_selector_all("rect")
                            taken = len([r for r in rects if 'occupied' in (r.get_attribute('class') or '')])
                            total = len(rects)
                            available = total - taken

                        results.append({
                            "Event": teams,
                            "Date": date,
                            "Time": time_ev,
                            "Sector": sector_name,
                            "Available": available,
                            "Taken": taken,
                            "Total": total,
                            "CheckedAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        })

                    except:
                        continue

                page.go_back()
                page.wait_for_timeout(2000)

            browser.close()
    except Exception as e:
        st.error(f"❌ Something went wrong: {e}")
        return []
    return results

# Remove auto refresh, add Refresh button
if "results" not in st.session_state:
    st.session_state["results"] = []
if "last_checked" not in st.session_state:
    st.session_state["last_checked"] = None

if st.button("🔄 Refresh"):
    st.session_state["results"] = fetch_seat_data(email, password)
    st.session_state["last_checked"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

results = st.session_state.get("results", [])

def colored_table(df):
    # Color map logic: green if available>0, red if available==0, orange if <30% available
    available_colors = []
    for v, total in zip(df["Available"], df["Total"]):
        if total == 0:
            available_colors.append("lightgray")
        elif v == 0:
            available_colors.append("#ff4b4b")
        elif v / total < 0.3:
            available_colors.append("#ffd166")
        else:
            available_colors.append("#06d6a0")
    # Default colors for other columns
    cell_colors = [
        ["darkslategrey"] * len(df) for _ in df.columns
    ]
    # Color just the 'Available' column
    avail_idx = df.columns.get_loc("Available")
    for i, col in enumerate(available_colors):
        cell_colors[avail_idx][i] = col

    fig = go.Figure(data=[go.Table(
        header=dict(values=list(df.columns),
                    fill_color='#118ab2', font=dict(color='white',size=14), align='center'),
        cells=dict(values=[df[col] for col in df.columns],
                   fill_color=cell_colors,
                   align='center',
                   font=dict(size=13))
    )])
    fig.update_layout(
        autosize=True,
        margin=dict(l=0, r=0, t=10, b=0),
        height=55 + 35 * len(df)  # <-- ADDED: dynamic height based on number of rows
    )
    return fig

if results:
    last_checked = st.session_state.get("last_checked", results[0]['CheckedAt'] if results else "")
    st.success(f"✅ Found seat data for {len(results)} sector(s). (Last checked: {last_checked})")
    df = pd.DataFrame(results)
    st.write("Results table:")
    fig = colored_table(df)
    st.plotly_chart(fig, use_container_width=True, height=fig.layout.height)  # <-- ADDED height
else:
    st.warning("⚠️ No results found.")

st.write("Click 'Refresh' to update seat information.")
