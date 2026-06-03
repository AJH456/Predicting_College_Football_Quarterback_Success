from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import json
import time
import re

BASE_URL = "https://247sports.com"
RANKINGS_URL = "https://247sports.com/season/2023-football/RecruitRankings/?InstitutionGroup=highschool&PositionGroup=QB"


def calculate_stars(rating):
    """Convert numerical rating to star rating."""
    try:
        r = float(rating)
        if r >= 98:
            return 5
        elif (r >= 90) and (r < 98):
            return 4
        elif (r >= 80) and (r < 90):
            return 3
        elif (r >= 70) and (r < 80):
            return 2
        else:
            return 1
    except:
        return None


def extract_state(school_info):
    """Extract state abbreviation from 'School Name (City, ST)' format."""
    if not school_info:
        return None
    match = re.search(r'\(([^,]+),\s*([A-Z]{2})\)', school_info)
    return match.group(2) if match else None


def extract_city(school_info):
    """Extract city from 'School Name (City, ST)' format."""
    if not school_info:
        return None
    match = re.search(r'\(([^,]+),\s*([A-Z]{2})\)', school_info)
    return match.group(1).strip() if match else None


def get_committed_school(soup):
    """Extract committed school from the timelineJson script tag."""
    
    timeline_script = soup.find("script", {"id": "timelineJson"})
    if timeline_script:
        try:
            raw_data = json.loads(timeline_script.string)
            
            # Data is a list with one wrapper object
            # Events are inside "timeLineData" (capital L)
            if isinstance(raw_data, list) and len(raw_data) > 0:
                events = raw_data[0].get("timeLineData", [])
            elif isinstance(raw_data, dict):
                events = raw_data.get("timeLineData", raw_data.get("timelineData", []))
            else:
                events = []

            # First pass: look for "Enrolled" event type
            for entry in events:
                if entry.get("event", "").lower() == "enrolled":
                    body = entry.get("body", "") or ""
                    match = re.search(r'enrolls at (.+?)(?:\.|$)', body, re.IGNORECASE)
                    if match:
                        return match.group(1).strip()
                    # institution field is also available
                    institution = entry.get("institution")
                    if institution:
                        return institution

            # Second pass: "Signed" event as fallback
            for entry in events:
                if entry.get("event", "").lower() == "signed":
                    institution = entry.get("institution")
                    if institution:
                        return institution
                    body = entry.get("body", "") or ""
                    match = re.search(r'signs.+?(?:to|with) (.+?)(?:\.|$)', body, re.IGNORECASE)
                    if match:
                        return match.group(1).strip()

            # Third pass: "Commit" event as fallback
            for entry in events:
                if entry.get("event", "").lower() == "commit":
                    institution = entry.get("institution")
                    if institution:
                        return institution

        except json.JSONDecodeError as e:
            print(f"  Timeline JSON parse error: {e}")

    # Fallback: h4 tags in timeline section
    timeline = soup.find("section", class_="timeline")
    if timeline:
        for h4 in timeline.find_all("h4"):
            text = h4.get_text(strip=True)
            if "enrolls at" in text.lower():
                match = re.search(r'enrolls at (.+)', text, re.IGNORECASE)
                if match:
                    return match.group(1).strip()

    # Last resort: meta keywords
    meta = soup.find("meta", {"name": "keywords"})
    if meta:
        keywords = meta.get("content", "").split(",")
        if len(keywords) >= 2:
            return keywords[-1].strip()

    return None


def get_player_urls(page):
    """Scrape all player profile URLs from the rankings pages."""
    all_players = []
    page_num = 1

    while True:
        if page_num == 1:
            url = RANKINGS_URL
        else:
            url = (
                f"{BASE_URL}/season/2023-football/RecruitRankings/?InstitutionGroup=highschool&PositionGroup=QB/"
                f"?ViewPath=~%2FViews%2FSkyNet%2FPlayerSportRanking%2F_SimpleSetForSeason.ascx"
                f"&Page={page_num}"
            )

        print(f"Scraping rankings page {page_num}...")
        page.goto(url, wait_until="domcontentloaded", timeout=20000)
        page.wait_for_timeout(3000)

        html = page.content()
        soup = BeautifulSoup(html, "html.parser")

        rows = soup.select("li.rankings-page__list-item")
        if not rows:
            print(f"No players found on page {page_num}, stopping.")
            break

        for row in rows:
            player = {}

            # Name and profile URL
            name_el = row.select_one("a.rankings-page__name-link")
            if not name_el:
                name_el = row.select_one("a[href*='/player/']")
            if name_el:
                player["name"] = name_el.get_text(strip=True)
                href = name_el.get("href", "")
                player["url"] = BASE_URL + href if href.startswith("/") else href
            else:
                continue

            # Rank
            rank_el = row.select_one(".rank-column .primary")
            player["rank"] = rank_el.get_text(strip=True) if rank_el else None

            # Position
            pos_el = row.select_one(".position")
            player["position"] = pos_el.get_text(strip=True) if pos_el else None

            # Height / Weight
            metrics_el = row.select_one(".metrics")
            if metrics_el:
                metrics = metrics_el.get_text(strip=True)
                parts = metrics.split("/")
                player["height"] = parts[0].strip() if len(parts) > 0 else None
                player["weight"] = parts[1].strip() if len(parts) > 1 else None
            else:
                player["height"] = None
                player["weight"] = None

            # Composite rating
            rating_el = row.select_one(".rating .score")
            player["composite_rating"] = rating_el.get_text(strip=True) if rating_el else None

            # School info -> city and state
            school_el = row.select_one(".recruit .meta")
            if school_el:
                meta_text = school_el.get_text(strip=True)
                player["school_info"] = meta_text
                player["city"]  = extract_city(meta_text)
                player["state"] = extract_state(meta_text)
            else:
                player["school_info"] = None
                player["city"]  = None
                player["state"] = None

            all_players.append(player)
            print(f"  Found: {player['name']} | {player.get('city')}, {player.get('state')}")

        # Check for next page
        if not soup.select_one("a[href*='Page=']"):
            print("No more pages.")
            break

        page_num += 1
        time.sleep(2)

    return all_players


def get_player_details(page, player):
    """Scrape detailed info from an individual player profile page."""
    profile_url = player["url"]
    details = {
        "scouting_report":   None,
        "draft_projection":  None,
        "reminds_of":        None,
        "evaluated_date":    None,
        "analyst":           None,
        "athletic_background": None,
        "committed_school":  None,
        "numerical_rating":  None,
        "stars":             None,
    }

    try:
        page.goto(profile_url, wait_until="domcontentloaded", timeout=20000)
        page.wait_for_timeout(4000)

        html = page.content()
        soup = BeautifulSoup(html, "html.parser")

        # --- Committed School (from commit-banner) ---
        details["committed_school"] = get_committed_school(soup)

        # --- Numerical rating and stars ---
        rating_el = soup.select_one(".ranking-simpleblock .score, .player-rankings-block .score")
        if rating_el:
            numerical = rating_el.get_text(strip=True)
            details["numerical_rating"] = numerical
            details["stars"] = calculate_stars(numerical)
        else:
            composite = player.get("composite_rating")
            if composite:
                try:
                    c = float(composite)
                    approx = round(c * 100 - 0.5, 1)
                    details["numerical_rating"] = approx
                    details["stars"] = calculate_stars(c)
                except:
                    pass

        # --- Scouting Report ---
        evaluation = soup.find("section", class_="evaluation")
        if evaluation:
            paragraphs = [
                p.get_text(strip=True)
                for p in evaluation.find_all("p")
                if p.get_text(strip=True)
            ]
            details["scouting_report"] = " ".join(paragraphs) if paragraphs else None

        # --- Highlights (projection, reminds of, evaluated date, analyst) ---
        highlights = soup.find("section", class_="highlights")
        if highlights:
            # Evaluated date
            eval_date = highlights.select_one("h4")
            if eval_date:
                details["evaluated_date"] = (
                    eval_date.get_text(strip=True).replace("Evaluated", "").strip()
                )

            # Analyst
            analyst_el = highlights.select_one("b.text")
            if analyst_el:
                details["analyst"] = analyst_el.get_text(strip=True)

            # Draft projection
            projection_div = highlights.select_one("div.projection")
            if projection_div:
                proj_parts = [
                    el.get_text(strip=True)
                    for el in projection_div.find_all(["b", "span"])
                    if el.get_text(strip=True)
                ]
                details["draft_projection"] = " - ".join(proj_parts)

            # Reminds of
            for div in highlights.find_all("div"):
                h4 = div.find("h4")
                if h4 and "Reminds" in h4.get_text():
                    link = div.find("a")
                    team = div.find("span")
                    reminds_name = link.get_text(strip=True) if link else ""
                    reminds_team = team.get_text(strip=True) if team else ""
                    details["reminds_of"] = f"{reminds_name} ({reminds_team})"

        # --- Skills ---
        # HTML: <li class="rate9"><span class="text">Intangibles</span><b>9</b></li>
        skills_section = soup.find("section", class_="skills")
        if skills_section:
            for item in skills_section.select("li[class^='rate']"):
                name_el  = item.select_one("span.text")
                score_el = item.find("b")
                if name_el and score_el:
                    skill_key = (
                        "skill_"
                        + name_el.get_text(strip=True)
                        .lower()
                        .replace(" ", "_")
                    )
                    details[skill_key] = score_el.get_text(strip=True)

        # --- Athletic Background ---
        bg_section = soup.find("section", class_="athletic-background")
        if bg_section:
            details["athletic_background"] = bg_section.get_text(strip=True)

    except Exception as e:
        details["scouting_report"] = f"Error: {e}"
        print(f"  ERROR on {profile_url}: {e}")

    return details


# ── Main ─────────────────────────────────────────────────────────────────────

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()

    # Step 1: Collect all player URLs from rankings pages
    print("=== STEP 1: Collecting player URLs ===")
    players = get_player_urls(page)
    print(f"\nFound {len(players)} players total.\n")

    with open("player_urls.json", "w", encoding="utf-8") as f:
        json.dump(players, f, indent=2)
    print("Saved player_urls.json\n")

    # Step 2: Visit each profile and scrape details
    print("=== STEP 2: Scraping player profiles ===")
    for i, player in enumerate(players):
        print(f"[{i+1}/{len(players)}] {player['name']}...")
        details = get_player_details(page, player)
        player.update(details)

        skills = {k: v for k, v in player.items() if k.startswith("skill_")}
        print(f"  School : {player.get('committed_school')}")
        print(f"  Stars  : {player.get('stars')} | Rating: {player.get('numerical_rating')}")
        print(f"  Proj   : {player.get('draft_projection')}")
        print(f"  Skills : {skills}")

        # Save progress every 10 players
        if (i + 1) % 10 == 0:
            with open("reports_progress.json", "w", encoding="utf-8") as f:
                json.dump(players, f, indent=2, ensure_ascii=False)
            print(f"  [Progress saved at {i+1} players]")

        time.sleep(2)

    # Step 3: Final save
    with open("scouting_reports_2023.json", "w", encoding="utf-8") as f:
        json.dump(players, f, indent=2, ensure_ascii=False)
    print(f"\nDone! Saved {len(players)} players to scouting_reports_2023.json")

    browser.close()