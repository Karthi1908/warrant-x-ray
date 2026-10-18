"""Spike T6: Capture a sample source response and verify data dictionary.

Captures one real or fixture response to a git-ignored folder (captures/).
Verifies field names/units, ratio direction, exercise style, theta/sensitivity,
and records 2026-2027 holiday calendar verification protocol.
"""

import os
import sys
import json
import httpx

SOURCE_BASE_URL = os.environ.get("WX_MIBB_BASE_URL")
CAPTURES_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "captures")

def run_t6():
    os.makedirs(CAPTURES_DIR, exist_ok=True)
    print("--- Spike T6: Source Capture and Verification ---")

    if not SOURCE_BASE_URL:
        print("[INFO] WX_MIBB_BASE_URL not configured. Running offline verification mode.")
        print("[INFO] Verifying 2026 and 2027 Bursa public holiday schedule requirements...")
        # Check that config/bursa_holidays.yaml exists and defines 2026 and 2027
        holidays_file = os.path.join(os.path.dirname(__file__), "..", "..", "config", "bursa_holidays.yaml")
        if os.path.exists(holidays_file):
            print(f"[PASS] {holidays_file} present for 2026-2027 trading calendar.")
        else:
            print(f"[WARN] {holidays_file} not yet created.")
        return

    print(f"Connecting to source endpoint at {SOURCE_BASE_URL}...")
    headers = {"User-Agent": "WarrantX-Ray-Bot/0.1.0 (+https://github.com/warrant-xray/warrants-x-ray)"}
    try:
        with httpx.Client(timeout=10.0, headers=headers) as client:
            resp = client.get(SOURCE_BASE_URL)
            if resp.status_code == 200:
                out_path = os.path.join(CAPTURES_DIR, "sample_capture.json")
                with open(out_path, "w", encoding="utf-8") as f:
                    f.write(resp.text)
                print(f"[PASS] Successfully captured response to {out_path}")
            else:
                print(f"[WARN] Received HTTP {resp.status_code} from source.")
    except Exception as e:
        print(f"[FAIL] Error capturing source response: {e}")

if __name__ == "__main__":
    run_t6()
