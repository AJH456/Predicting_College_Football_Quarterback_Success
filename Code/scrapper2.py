from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import json
import time

BASE_URL = "https://247sports.com"
RANKINGS_URL = "https://247sports.com/Sport/Football/AllTimeRecruitRankings/"

def get_player_urls(page):
    """Scrape all player profile URLs from the rankings pages."""
    all_urls = []
    page_num = 1

    while True:
        if page_num == 1:
            url = RANKINGS_URL
        else:
            url = f"{BASE_URL}/season/2028-football/alltimerecruitrankings/?ViewPath=~%2FViews%2FSkyNet%2FPlayerSportRanking%2F_SimpleSetForSeason.ascx&Page={page_num}"

        print(f"Scraping rankings page {page_num}...")
        page.goto(url, wait_until="domcontentloaded", timeout=20000)
        page.wait_for_timeout(3000)

        html = page.content()
        soup = BeautifulSoup(html, "html.parser")

        # Find all player profile links
        links = soup.select("ul.rankings-page__list a.rankings-page__name-link")
        
        # Fallback selector if above doesn't work
        if not links:
            links = soup.select(".player a[href*='/player/']")

        if not links:
            print(f"No players found on page {page_num}, stopping.")
            break

        for link in links:
            href = link.get("href")
            if href:
                full_url = BASE_URL + href if href.startswith("/") else href
                name = link.get_text(strip=True)
                all_urls.append({"name": name, "url": full_url})
                print(f"  Found: {name} -> {full_url}")

        # Check if there's a next page
        load_more = soup.select_one("a[href*='Page=']")
        if not load_more:
            print("No more pages found.")
            break

        page_num += 1
        time.sleep(2)

    return all_urls


def get_scouting_report(page, profile_url):
    """Scrape the scouting report from a player's profile page."""
    try:
        page.goto(profile_url, wait_until="domcontentloaded", timeout=20000)
        page.wait_for_timeout(4000)

        html = page.content()
        soup = BeautifulSoup(html, "html.parser")

        evaluation = soup.find("section", class_="evaluation")
        if evaluation:
            paragraphs = [p.get_text(strip=True) for p in evaluation.find_all("p") if p.get_text(strip=True)]
            return " ".join(paragraphs) if paragraphs else "No report text"
        else:
            return "No evaluation section found"

    except Exception as e:
        return f"Error: {e}"


with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()

    # Step 1: Get all player URLs from rankings
    print("=== STEP 1: Collecting player URLs ===")
    players = get_player_urls(page)
    print(f"\nFound {len(players)} players total.\n")

    # Save URLs in case script crashes mid-run
    with open("player_urls.json", "w", encoding="utf-8") as f:
        json.dump(players, f, indent=2)

    # Step 2: Visit each profile and grab scouting report
    print("=== STEP 2: Scraping scouting reports ===")
    for i, player in enumerate(players):
        print(f"[{i+1}/{len(players)}] Scraping {player['name']}...")
        player["scouting_report"] = get_scouting_report(page, player["url"])
        print(f"  -> {player['scouting_report'][:80]}...")  # preview first 80 chars

        # Save progress after every 10 players in case of crash
        if (i + 1) % 10 == 0:
            with open("reports_progress.json", "w", encoding="utf-8") as f:
                json.dump(players, f, indent=2, ensure_ascii=False)
            print(f"  [Progress saved at {i+1} players]")

        time.sleep(2)  # be polite

    # Step 3: Save final output
    with open("scouting_reports.json", "w", encoding="utf-8") as f:
        json.dump(players, f, indent=2, ensure_ascii=False)
    print(f"\nDone! Saved {len(players)} scouting reports to scouting_reports.json")

    browser.close()