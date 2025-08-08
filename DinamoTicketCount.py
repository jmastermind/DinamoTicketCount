import streamlit as st
import csv
import io
import os
import subprocess
from datetime import datetime
from playwright.sync_api import sync_playwright

# ⬆️ Install Chromium browser if missing (for Streamlit Cloud)
if not os.path.exists("/home/appuser/.cache/ms-playwright"):
    try:
        subprocess.run(["playwright", "install", "chromium"], check=True)
    except Exception as e:
        print(f"Error installing Chromium: {e}")

st.set_page_config(page_title="Dinamo Seat Checker", layout="centered")
st.title("💺 Dinamo Ticket Seat Checker")
st.write("Check available and taken seats for upcoming matches on the official GNK Dinamo ticketing website.")

email = st.text_input("Email", type="default", placeholder="your.email@example.com")
password = st.text_input("Password", type="password")

start_check = st.button("🎟 Check Seats")

if start_check and email and password:
    with st.spinner("Logging in and checking events... Please wait."):
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
                    st.warning("⚠️ No games found.")
                    browser.close()
                    st.stop()

                games = page.query_selector_all("button.game")
                if not games:
                    st.warning("⚠️ No games currently available.")
                    browser.close()
                    st.stop()

                for index, game in enumerate(games):
                    page.wait_for_selector("button.game")
                    games = page.query_selector_all("button.game")
                    current_game = games[index]

                    date = current_game.query_selector(".date").inner_text() if current_game.query_selector(".date") else "N/A"
                    time = current_game.query_selector(".time").inner_text() if current_game.query_selector(".time") else "N/A"
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
                                "Time": time,
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
            st.stop()

    if results:
        st.success(f"✅ Found seat data for {len(results)} sector(s).")
        st.write("You can now download the CSV file.")

        csv_buffer = io.StringIO()
        writer = csv.DictWriter(csv_buffer, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)
        csv_data = csv_buffer.getvalue()

        timestamp = datetime.now().strftime("%d%m%Y_%H%M%S")
        st.download_button(
            label="⬇️ Download CSV",
            data=csv_data,
            file_name=f"DinamoChecker_{timestamp}.csv",
            mime="text/csv"
        )
    else:
        st.warning("⚠️ No results found.")
