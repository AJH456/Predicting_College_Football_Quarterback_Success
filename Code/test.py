from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import json
import time

BASE_URL = "https://247sports.com"
RANKINGS_URL = "https://247sports.com/season/2019-football/RecruitRankings/?InstitutionGroup=highschool&PositionGroup=QB"


def get_player_urls(page):
    """Scrape all player profile URLs from the rankings pages."""
    all_players = []
    page_num = 1

    while True:
        if page_num == 1:
            url = RANKINGS_URL
        else:
            url = f"{BASE_URL}/season/2019-football/RecruitRankings/?InstitutionGroup=highschool&PositionGroup=QB/?ViewPath=~%2FViews%2FSkyNet%2FPlayerSportRanking%2F_SimpleSetForSeason.ascx&Page={page_num}"

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
            player["rating"] = rating_el.get_text(strip=True) if rating_el else None

            # Star rating
            stars_el = row.select_one(".rating .stars")
            player["stars"] = stars_el.get_text(strip=True) if stars_el else None

            # State (from the school/location text)
            school_el = row.select_one(".recruit .meta")
            if school_el:
                meta_text = school_el.get_text(strip=True)
                player["school_info"] = meta_text  # e.g. "Mater Dei (Santa Ana, CA)"
            else:
                player["school_info"] = None

            # Committed school
            commit_el = row.select_one(".school img")
            player["committed_to"] = commit_el.get("alt") if commit_el else None

            all_players.append(player)
            print(f"  Found: {player['name']}")

        # Check for next page
        load_more = soup.select_one("a[href*='Page=']")
        if not load_more:
            print("No more pages.")
            break

        page_num += 1
        time.sleep(2)

    return all_players


def get_player_details(page, profile_url):
    """Scrape detailed info from individual player profile page."""
    details = {
        "scouting_report": None,
        "draft_projection": None,
        "reminds_of": None,
        "evaluated_date": None,
        "analyst": None,
        "state": None,
        "athletic_background": None,
    }

    try:
        page.goto(profile_url, wait_until="domcontentloaded", timeout=20000)
        page.wait_for_timeout(4000)

        html = page.content()
        soup = BeautifulSoup(html, "html.parser")

        # --- Scouting Report ---
        evaluation = soup.find("section", class_="evaluation")
        if evaluation:
            paragraphs = [p.get_text(strip=True) for p in evaluation.find_all("p") if p.get_text(strip=True)]
            details["scouting_report"] = " ".join(paragraphs) if paragraphs else None

        # --- Highlights section (projection, reminds of, evaluated date, analyst) ---
        highlights = soup.find("section", class_="highlights")
        if highlights:
            # Evaluated date
            eval_date = highlights.select_one("h4")
            if eval_date:
                details["evaluated_date"] = eval_date.get_text(strip=True).replace("Evaluated", "").strip()

            # Analyst name
            analyst_el = highlights.select_one("b.text")
            if analyst_el:
                details["analyst"] = analyst_el.get_text(strip=True)

            # Draft projection
            projection_div = highlights.select_one("div.projection")
            if projection_div:
                proj_parts = [el.get_text(strip=True) for el in projection_div.find_all(["b", "span"]) if el.get_text(strip=True)]
                details["draft_projection"] = " - ".join(proj_parts)

            # Reminds of
            reminds_divs = highlights.find_all("div")
            for div in reminds_divs:
                h4 = div.find("h4")
                if h4 and "Reminds" in h4.get_text():
                    link = div.find("a")
                    team = div.find("span")
                    reminds_name = link.get_text(strip=True) if link else ""
                    reminds_team = team.get_text(strip=True) if team else ""
                    details["reminds_of"] = f"{reminds_name} ({reminds_team})"

        # --- Skills section ---
        skills_section = soup.find("div", class_="skills-list")
        if not skills_section:
            skills_section = soup.find("section", class_="skills")
        if skills_section:
            skill_rows = skills_section.select("li, .skill-row, tr")
            for skill in skill_rows:
                # Each skill has a name and a number rating
                name_el = skill.select_one(".skill-name, td:first-child, span.name")
                score_el = skill.select_one(".skill-score, td:last-child, span.score, b")
                if name_el and score_el:
                    skill_name = name_el.get_text(strip=True).lower().replace(" ", "_")
                    skill_score = score_el.get_text(strip=True)
                    details[f"skill_{skill_name}"] = skill_score

        # --- Athletic Background ---
        bg_section = soup.find("div", class_="background-and-skills")
        if bg_section:
            bg_p = bg_section.find("p")
            if bg_p:
                details["athletic_background"] = bg_p.get_text(strip=True)

        # --- State from profile header ---
        location_el = soup.select_one(".player-bio .location, .recruit-bio .location")
        if location_el:
            details["state"] = location_el.get_text(strip=True)

    except Exception as e:
        details["scouting_report"] = f"Error: {e}"

    return details


with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()

    # Step 1: Get all player URLs from rankings
    print("=== STEP 1: Collecting player URLs ===")
    players = get_player_urls(page)
    print(f"\nFound {len(players)} players total.\n")

    with open("player_urls.json", "w", encoding="utf-8") as f:
        json.dump(players, f, indent=2)

    # Step 2: Visit each profile and grab all details
    print("=== STEP 2: Scraping player profiles ===")
    for i, player in enumerate(players):
        print(f"[{i+1}/{len(players)}] Scraping {player['name']}...")
        details = get_player_details(page, player["url"])
        player.update(details)
        print(f"  Report: {str(player.get('scouting_report', ''))[:80]}...")
        print(f"  Projection: {player.get('draft_projection')}")
        print(f"  Skills: { {k:v for k,v in player.items() if k.startswith('skill_')} }")

        # Save progress every 10 players
        if (i + 1) % 10 == 0:
            with open("reports_progress.json", "w", encoding="utf-8") as f:
                json.dump(players, f, indent=2, ensure_ascii=False)
            print(f"  [Progress saved at {i+1} players]")

        time.sleep(2)

    # Step 3: Save final output
    with open("scouting_reports_full.json", "w", encoding="utf-8") as f:
        json.dump(players, f, indent=2, ensure_ascii=False)
    print(f"\nDone! Saved {len(players)} players to scouting_reports_full.json")

    browser.close()