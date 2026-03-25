import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.utils.garmin import get_garmin_client
from datetime import date
import json

def debug_sync_today():
    email = "sergi.marquez.brugal@gmail.com"
    password = "peluchE-1978.3*"
    today_str = "2026-03-25"
    
    print(f"DEBUG: Syncing for {today_str}...")
    client = get_garmin_client(email, password)
    if not client:
        print("❌ Login failed")
        return
    
    try:
        stats = client.get_stats(today_str)
        sleep = client.get_sleep_data(today_str)
        rhr = client.get_rhr_day(today_str)
        hrv = client.get_hrv_data(today_str) # This might only work for completed days
        
        print(f"Stats raw keys: {list(stats.keys()) if stats else 'None'}")
        print(f"Steps: {stats.get('totalSteps')}")
        print(f"Sleep available: {bool(sleep)}")
        print(f"RHR: {rhr}")
        print(f"HRV Summary: {hrv.get('hrvSummary') if hrv else 'None'}")
        
    except Exception as e:
        print(f"❌ Error during sync: {e}")

if __name__ == "__main__":
    debug_sync_today()
