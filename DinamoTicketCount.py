import streamlit as st
import csv
import io
import os
import subprocess
from datetime import datetime
from playwright.sync_api import sync_playwright
import time

# ⬆️ Install Chromium browser if missing (for Streamlit Cloud)
if not os.path.exists("/home/appuser/.cache/ms-playwright"):
    try:
        subprocess.run(["playwright", "install", "chromium"], check=True)
    except Exception as e:
        print(f"Error installing Chromium: {e}")

st.set_page_config(page_title="Dinamo Seat Checker", layout="centered")
st.title("💺 Dinamo Ticket Seat Checker")
st.write("Automatically checks available and taken seats for upcoming matches on the official GNK Dinamo ticketing website every minute.")

# Hardcoded credentials
email = "your.email@example.com"
password = "yourpassword"

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

# Streamlit's auto-refresh using st.experimental_rerun every minute
if "last_run" not in st.session_state or "results" not in st.session_state or \
   (datetime.now() - st.session_state["last_run"]).seconds > 60:
    st.session_state["results"] = fetch_seat_data(email, password)
    st.session_state["last_run"] = datetime.now()
    st.experimental_rerun()

results = st.session_state.get("results", [])

if results:
    st.success(f"✅ Found seat data for {len(results)} sector(s). (Last checked: {results[0]['CheckedAt']})")
    st.write("Results table:")
    st.dataframe(results)
else:
    st.warning("⚠️ No results found.")

st.write("This page refreshes automatically every minute to show up-to-date seat information.")
