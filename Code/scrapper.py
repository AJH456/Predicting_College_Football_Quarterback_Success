from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import json

profile_url = "https://247sports.com/player/bryce-young-93127/"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    page.goto(profile_url, wait_until="domcontentloaded", timeout=20000)
    page.wait_for_timeout(5000)
    
    html = page.content()
    soup = BeautifulSoup(html, "html.parser")
    
    # Find the evaluation section
    evaluation = soup.find("section", class_="evaluation")
    
    if evaluation:
        # Get all <p> tags and filter out empty ones
        paragraphs = [p.get_text(strip=True) for p in evaluation.find_all("p") if p.get_text(strip=True)]
        report_text = " ".join(paragraphs)
        print("--- SCOUTING REPORT ---")
        print(report_text)
    else:
        report_text = "Not found"
        print("section.evaluation not found in parsed HTML")
    
    with open("report.json", "w", encoding="utf-8") as f:
        json.dump({"report": report_text}, f)
    
    browser.close()