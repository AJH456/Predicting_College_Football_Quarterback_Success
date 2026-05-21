from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import json

profile_url = "https://247sports.com/player/sam-howell-91707/"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    page.goto(profile_url, wait_until="domcontentloaded", timeout=20000)
    page.wait_for_timeout(4000)

    html = page.content()
    soup = BeautifulSoup(html, "html.parser")

    timeline_script = soup.find("script", {"id": "timelineJson"})
    if timeline_script:
        raw = timeline_script.string
        
        # Print the raw JSON so we can see the full structure
        print("RAW TIMELINE JSON:")
        print(raw[:5000])  # first 5000 chars
        print("\n...\n")
        
        data = json.loads(raw)
        print(f"Type: {type(data)}")
        
        if isinstance(data, dict):
            print(f"Keys: {data.keys()}")
            events = data.get("timelineData", [])
        else:
            events = data

        print(f"\nTotal events: {len(events)}")
        print("\nAll event types found:")
        for e in events:
            print(f"  event: {e.get('event')!r:20} | body: {str(e.get('body',''))[:80]}")
    else:
        print("No timelineJson script found")

    browser.close()