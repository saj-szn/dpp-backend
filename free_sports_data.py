"""Optional free historical-data adapters for DPP.

These libraries are optional at runtime: provider failures never break the API.
No provider response is treated as sportsbook odds.
"""
from __future__ import annotations

import importlib.util
from typing import Any

PROVIDERS = {
    "basketball": [
        {"name": "Sportsipy", "package": "sportsipy", "purpose": "historical basketball stats", "note": "Sports-Reference scraping; may break when site structure changes."},
        {"name": "ESPN public data", "package": None, "purpose": "fixtures, rosters and some game logs", "note": "Unofficial public endpoints; coverage varies."},
    ],
    "american_football": [
        {"name": "nfl_data_py", "package": "nfl_data_py", "purpose": "historical NFL play-by-play and player stats", "note": "Data availability depends on season and package compatibility."},
        {"name": "Sportsipy", "package": "sportsipy", "purpose": "historical NFL stats", "note": "Sports-Reference scraping; may break."},
    ],
    "baseball": [
        {"name": "pybaseball", "package": "pybaseball", "purpose": "historical MLB stats and Statcast data", "note": "Public-source rate limits and upstream changes may apply."},
        {"name": "Sportsipy", "package": "sportsipy", "purpose": "historical MLB stats", "note": "Sports-Reference scraping; may break."},
    ],
    "hockey": [
        {"name": "hockey_scraper", "package": "hockey_scraper", "purpose": "historical NHL game data", "note": "Scraping support can change with source websites."},
        {"name": "Sportsipy", "package": "sportsipy", "purpose": "historical NHL stats", "note": "Sports-Reference scraping; may break."},
    ],
    "football": [
        {"name": "ESPN public data", "package": None, "purpose": "soccer fixtures and available player stats", "note": "League coverage varies."},
        {"name": "Sportsipy", "package": "sportsipy", "purpose": "historical soccer stats where supported", "note": "Coverage is not comprehensive."},
    ],
    "tennis": [
        {"name": "Public tennis datasets", "package": None, "purpose": "historical match results", "note": "A reliable live player-stat source is not guaranteed."},
    ],
    # The app's other two sports are not yet identified in backend SPORTS.
    "sport_7": [{"name": "Provider pending", "package": None, "purpose": "awaiting sport confirmation", "note": "No data will be fabricated."}],
    "sport_8": [{"name": "Provider pending", "package": None, "purpose": "awaiting sport confirmation", "note": "No data will be fabricated."}],
}

def provider_status() -> dict[str, Any]:
    result = []
    for sport, providers in PROVIDERS.items():
        for provider in providers:
            package = provider["package"]
            result.append({
                "sport": sport,
                "provider": provider["name"],
                "purpose": provider["purpose"],
                "package": package,
                "installed": bool(importlib.util.find_spec(package)) if package else None,
                "status": "package_check_only" if package else "public_source_candidate",
                "note": provider["note"],
                "free": True,
            })
    return {"providers": result, "sports_listed": 8, "note": "Free-source candidates only; availability must be tested before displaying stats."}
