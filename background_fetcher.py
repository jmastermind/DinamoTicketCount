import json
from datetime import datetime
from DinamoTicketCount import fetch_seat_data  # reuse your function

email = "jakov.mandic.27@gmail.com"
password = "cfgdqverkt"

def main():
    results = fetch_seat_data(email, password)
    out = {
        "last_checked": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "results": results
    }
    with open("results.json", "w") as f:
        json.dump(out, f)

if __name__ == "__main__":
    main()
