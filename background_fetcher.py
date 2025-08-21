import json
from datetime import datetime
import streamlit as st
import csv
import io
import os
import subprocess
from datetime import datetime
from playwright.sync_api import sync_playwright
import time
import pandas as pd

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

def main():
    results = fetch_seat_data(email, password)
    # Calculate the total available and taken values
    total_available = sum(r.get("Available", 0) for r in results)
    total_taken = sum(r.get("Taken", 0) for r in results)
    total_total = sum(r.get("Total", 0) for r in results)
    
    # Add the summary row
    summary_row = {
        "Event": "TOTAL",
        "Date": "",
        "Time": "",
        "Sector": "",
        "Available": total_available,
        "Taken": total_taken,
        "Total": total_total,
        "CheckedAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    results.append(summary_row)
    
    # Aggregate by stand -- use first three words of a sector name
    stands = {}
    for r in results:
        sector = r.get("Sector", "")
        if sector and r["Event"] != "TOTAL":
            words = sector.split()
            if len(words) >= 3:
                stand = " ".join(words[:3])
            elif words:
                stand = " ".join(words)
            else:
                stand = "Unknown"
            if stand not in stands:
                stands[stand] = {"Available": 0, "Taken": 0, "Total": 0}
            stands[stand]["Available"] += r.get("Available", 0)
            stands[stand]["Taken"] += r.get("Taken", 0)
            stands[stand]["Total"] += r.get("Total", 0)
    
    # Add stand summary rows
    checked_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for stand, vals in stands.items():
        stand_row = {
            "Event": f"SUM {stand}",
            "Date": "",
            "Time": "",
            "Sector": stand,
            "Available": vals["Available"],
            "Taken": vals["Taken"],
            "Total": vals["Total"],
            "CheckedAt": checked_at
        }
        results.append(stand_row)
    
    out = {
        "last_checked": checked_at,
        "results": results
    }
    with open("DinamoTicketCount/results.json", "w") as f:
        json.dump(out, f)

if __name__ == "__main__":
    main()
