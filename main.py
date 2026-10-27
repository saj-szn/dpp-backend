

import csv
import io
import json
import os
import sqlite3
from datetime import datetime, timezone

from fastapi import (
    FastAPI,
    HTTPException,
    Query,
    UploadFile,
    File,
)
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="DPP Backend",
    description="D Players Props sports analytics API",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

SPORTS = {
    "basketball": "Basketball",
    "football": "Football / Soccer",
    "american_football": "American Football",
    "tennis": "Tennis",
    "hockey": "Ice Hockey",
    "baseball": "Baseball",
}

# Local database for initial testing.
# Use persistent PostgreSQL for production deployment.
DATABASE_PATH = os.getenv("DPP_DATABASE_PATH", "dpp_data.db")

REQUIRED_COLUMNS = {
    "sport",
    "entity_type",
    "entity_name",
    "match_date",
    "opponent",
    "stat_name",
    "stat_value",
}


def now_utc():
    return datetime.now(timezone.utc).isoformat()


def response_status():
    return {
        "mode": "demo",
        "message": (
            "Using imported or manually supplied data. "
            "Live sports feeds are not connected."
        ),
        "generated_at": now_utc(),
    }


def connect_db():
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    with connect_db() as db:
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sport TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                entity_name TEXT NOT NULL,
                match_date TEXT NOT NULL,
                opponent TEXT NOT NULL DEFAULT '',
                stat_name TEXT NOT NULL,
                stat_value REAL NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )

        db.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_stats_lookup
            ON stats (
                sport,
                entity_type,
                entity_name,
                stat_name,
                match_date
            )
            """
        )


init_db()


def validate_sport(sport):
    sport_id = sport.strip().lower()

    if sport_id not in SPORTS:
        raise HTTPException(
            status_code=404,
            detail="Sport not found.",
        )

    return sport_id


def validate_entity_type(entity_type):
    entity_type = entity_type.strip().lower()

    if entity_type not in ("player", "team"):
        raise HTTPException(
            status_code=400,
            detail="entity_type must be player or team.",
        )

    return entity_type


@app.get("/")
def home():
    return {
        "app": "D Players Props",
        "status": "online",
        **response_status(),
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
        **response_status(),
    }


@app.get("/api/sports")
def list_sports():
    return {
        "sports": [
            {"id": sport_id, "name": name}
            for sport_id, name in SPORTS.items()
        ],
        **response_status(),
    }


@app.get("/api/sports/{sport_id}")
def get_sport(sport_id: str):
    sport_id = validate_sport(sport_id)

    return {
        "id": sport_id,
        "name": SPORTS[sport_id],
        **response_status(),
    }


@app.get("/api/teams")
def list_teams(
    sport: str = Query(...),
    q: str = Query(default=""),
):
    sport_id = validate_sport(sport)

    with connect_db() as db:
        rows = db.execute(
            """
            SELECT DISTINCT entity_name
            FROM stats
            WHERE sport = ?
              AND entity_type = 'team'
              AND entity_name LIKE ?
            ORDER BY entity_name
            LIMIT 100
            """,
            (sport_id, "%" + q.strip() + "%"),
        ).fetchall()

    return {
        "sport": sport_id,
        "teams": [
            {"id": row["entity_name"], "name": row["entity_name"]}
            for row in rows
        ],
        **response_status(),
    }


@app.get("/api/players")
def list_players(
    sport: str = Query(...),
    q: str = Query(default=""),
):
    sport_id = validate_sport(sport)

    with connect_db() as db:
        rows = db.execute(
            """
            SELECT DISTINCT entity_name
            FROM stats
            WHERE sport = ?
              AND entity_type = 'player'
              AND entity_name LIKE ?
            ORDER BY entity_name
            LIMIT 100
            """,
            (sport_id, "%" + q.strip() + "%"),
        ).fetchall()

    return {
        "sport": sport_id,
        "players": [
            {"id": row["entity_name"], "name": row["entity_name"]}
            for row in rows
        ],
        **response_status(),
    }


@app.get("/api/matches")
def list_matches(
    sport: str = Query(...),
    limit: int = Query(default=10, ge=1, le=50),
):
    sport_id = validate_sport(sport)

    with connect_db() as db:
        rows = db.execute(
            """
            SELECT DISTINCT match_date, opponent
            FROM stats
            WHERE sport = ?
            ORDER BY match_date DESC
            LIMIT ?
            """,
            (sport_id, limit),
        ).fetchall()

    matches = [
        {
            "date": row["match_date"],
            "opponent": row["opponent"],
        }
        for row in rows
    ]

    return {
        "sport": sport_id,
        "limit": limit,
        "matches": matches,
        **response_status(),
    }


@app.get("/api/history")
def get_history(
    sport: str = Query(...),
    entity_type: str = Query(...),
    entity_id: str = Query(..., min_length=1),
    count: int = Query(default=5, ge=1, le=20),
    stat_name: str = Query(default=""),
):
    sport_id = validate_sport(sport)
    entity_type = validate_entity_type(entity_type)
    entity_id = entity_id.strip()

    sql = """
        SELECT match_date, opponent, stat_name, stat_value
        FROM stats
        WHERE sport = ?
          AND entity_type = ?
          AND entity_name = ?
    """
    params = [sport_id, entity_type, entity_id]

    if stat_name.strip():
        sql += " AND stat_name = ?"
        params.append(stat_name.strip())

    sql += " ORDER BY match_date DESC, id DESC LIMIT ?"
    params.append(count)

    with connect_db() as db:
        rows = db.execute(sql, params).fetchall()

    records = [
        {
            "date": row["match_date"],
            "opponent": row["opponent"],
            "stat_name": row["stat_name"],
            "stat_value": row["stat_value"],
        }
        for row in rows
    ]

    return {
        "sport": sport_id,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "requested_matches": count,
        "records": records,
        **response_status(),
    }


@app.post("/api/import/csv")
async def import_csv(file: UploadFile = File(...)):
    filename = (file.filename or "").lower()

    if not filename.endswith(".csv"):
        raise HTTPException(
            status_code=400,
            detail="Please upload a .csv file.",
        )

    raw = await file.read(5 * 1024 * 1024 + 1)

    if len(raw) > 5 * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail="CSV file must be 5 MB or smaller.",
        )

    try:
        content = raw.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(content))
        headers = {
            (header or "").strip().lower()
            for header in (reader.fieldnames or [])
        }

        missing = REQUIRED_COLUMNS - headers

        if missing:
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "CSV is missing required columns.",
                    "missing_columns": sorted(missing),
                    "required_columns": sorted(REQUIRED_COLUMNS),
                },
            )

        inserted = 0
        skipped = 0
        batch = []

        for line_number, source in enumerate(reader, start=2):
            row = {
                (key or "").strip().lower(): (value or "").strip()
                for key, value in source.items()
            }

            sport = row.get("sport", "").lower()
            entity_type = row.get("entity_type", "").lower()
            entity_name = row.get("entity_name", "")
            match_date = row.get("match_date", "")
            opponent = row.get("opponent", "")
            stat_name = row.get("stat_name", "")
            raw_value = row.get("stat_value", "")

            if (
                sport not in SPORTS
                or entity_type not in ("player", "team")
                or not entity_name
                or not stat_name
                or not match_date
            ):
                skipped += 1
                continue

            try:
                value = float(raw_value)

                if not (-1e12 < value < 1e12):
                    skipped += 1
                    continue
            except (ValueError, TypeError):
                skipped += 1
                continue

            batch.append(
                (
                    sport,
                    entity_type,
                    entity_name,
                    match_date,
                    opponent,
                    stat_name,
                    value,
                    now_utc(),
                )
            )

        if not batch:
            return {
                "message": "No valid records were found.",
                "imported": 0,
                "skipped": skipped,
                **response_status(),
            }

        with connect_db() as db:
            db.executemany(
                """
                INSERT INTO stats (
                    sport, entity_type, entity_name,
                    match_date, opponent, stat_name,
                    stat_value, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                batch,
            )
            inserted = len(batch)

    except HTTPException:
        raise
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=400,
            detail="CSV must use UTF-8 text encoding.",
        )
    except csv.Error:
        raise HTTPException(
            status_code=400,
            detail="Could not read the CSV file.",
        )
    finally:
        await file.close()

    return {
        "message": "CSV import completed.",
        "imported": inserted,
        "skipped": skipped,
        **response_status(),
    }


@app.get("/api/analysis")
def analyse_stats(
    sport: str = Query(...),
    entity_type: str = Query(...),
    entity_id: str = Query(..., min_length=1),
    stat_name: str = Query(..., min_length=1),
    line: float = Query(...),
    count: int = Query(default=5, ge=1, le=20),
):
    sport_id = validate_sport(sport)
    entity_type = validate_entity_type(entity_type)
    entity_id = entity_id.strip()
    stat_name = stat_name.strip()

    with connect_db() as db:
        rows = db.execute(
            """
            SELECT match_date, opponent, stat_value
            FROM stats
            WHERE sport = ?
              AND entity_type = ?
              AND entity_name = ?
              AND stat_name = ?
            ORDER BY match_date DESC, id DESC
            LIMIT ?
            """,
            (
                sport_id,
                entity_type,
                entity_id,
                stat_name,
                count,
            ),
        ).fetchall()

    values = [row["stat_value"] for row in rows]

    if not values:
        return {
            "sport": sport_id,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "stat_name": stat_name,
            "line": line,
            "games_analyzed": 0,
            "average": None,
            "over_hits": 0,
            "under_hits": 0,
            "pushes": 0,
            "over_hit_rate": None,
            "under_hit_rate": None,
            "records": [],
            "message": "No imported history found for this selection.",
            **response_status(),
        }

    over_hits = sum(value > line for value in values)
    under_hits = sum(value < line for value in values)
    pushes = sum(value == line for value in values)
    total = len(values)

    records = [
        {
            "date": row["match_date"],
            "opponent": row["opponent"],
            "value": row["stat_value"],
        }
        for row in rows
    ]

    return {
        "sport": sport_id,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "stat_name": stat_name,
        "line": line,
        "games_analyzed": total,
        "average": round(sum(values) / total, 2),
        "over_hits": over_hits,
        "under_hits": under_hits,
        "pushes": pushes,
        "over_hit_rate": round(over_hits / total * 100, 2),
        "under_hit_rate": round(under_hits / total * 100, 2),
        "records": records,
        "message": (
            "Historical statistics only. "
            "Hit rates are not guarantees of future outcomes."
        ),
        **response_status(),
    }


@app.get("/api/stats/summary")
def stats_summary():
    with connect_db() as db:
        total = db.execute(
            "SELECT COUNT(*) AS total FROM stats"
        ).fetchone()["total"]

        by_sport = db.execute(
            """
            SELECT sport, COUNT(*) AS total
            FROM stats
            GROUP BY sport
            ORDER BY sport
            """
        ).fetchall()

    return {
        "total_stat_records": total,
        "by_sport": [
            {"sport": row["sport"], "records": row["total"]}
            for row in by_sport
        ],
        **response_status(),
    }


# Public-provider integrations. Provider responses are returned as sourced data;
# no generated/demo records are presented as live results.
import urllib.parse
import urllib.request
import urllib.error

PROVIDER_SPORTS = {
    "basketball": ("basketball", "nba"),
    "football": ("soccer", "eng.1"),
    "american_football": ("football", "nfl"),
    "hockey": ("hockey", "nhl"),
    "baseball": ("baseball", "mlb"),
    "tennis": ("tennis", ""),
}

def provider_json(url, timeout=8):
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "PlayasProps/1.0 (sports research app)", "Accept": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))

@app.get("/api/providers/status")
def providers_status():
    return {
        "providers": [
            {"name": "ESPN public scoreboard", "purpose": "fixtures and scores", "authentication": "none", "status": "configured_unverified"},
            {"name": "TheSportsDB public test key", "purpose": "player and team directory search", "authentication": "public test key", "status": "configured_unverified"},
        ],
        "important": "Provider availability and coverage vary. Sportsbook player prop lines are not supplied by scoreboard endpoints.",
        "generated_at": now_utc(),
    }

@app.get("/api/live/players")
def live_players(sport: str = Query(...), q: str = Query(..., min_length=2)):
    sport_id = validate_sport(sport)
    query = urllib.parse.urlencode({"p": q.strip()})
    url = "https://www.thesportsdb.com/api/v1/json/123/searchplayers.php?" + query
    try:
        data = provider_json(url)
        raw = data.get("player") or []
        results = [{
            "id": str(p.get("idPlayer") or ""),
            "name": p.get("strPlayer") or "",
            "team": p.get("strTeam") or "",
            "sport": p.get("strSport") or SPORTS[sport_id],
            "nationality": p.get("strNationality") or "",
            "position": p.get("strPosition") or "",
            "date_of_birth": p.get("dateBorn") or "",
            "source": "TheSportsDB",
            "source_url": "https://www.thesportsdb.com/",
        } for p in raw if p.get("strPlayer")]
        return {"sport": sport_id, "query": q, "players": results, "source": "TheSportsDB", "mode": "live_provider", "count": len(results), "generated_at": now_utc()}
    except Exception as exc:
        return {"sport": sport_id, "query": q, "players": [], "source": "TheSportsDB", "mode": "provider_unavailable", "count": 0, "message": "Live player search could not reach the provider. Try again later.", "error_type": type(exc).__name__, "generated_at": now_utc()}

@app.get("/api/live/teams")
def live_teams(sport: str = Query(...), q: str = Query(..., min_length=2)):
    sport_id = validate_sport(sport)
    query = urllib.parse.urlencode({"t": q.strip()})
    url = "https://www.thesportsdb.com/api/v1/json/123/searchteams.php?" + query
    try:
        data = provider_json(url)
        raw = data.get("teams") or []
        results = [{
            "id": str(t.get("idTeam") or ""),
            "name": t.get("strTeam") or "",
            "sport": t.get("strSport") or SPORTS[sport_id],
            "league": t.get("strLeague") or "",
            "country": t.get("strCountry") or "",
            "source": "TheSportsDB",
        } for t in raw if t.get("strTeam")]
        return {"sport": sport_id, "query": q, "teams": results, "source": "TheSportsDB", "mode": "live_provider", "count": len(results), "generated_at": now_utc()}
    except Exception as exc:
        return {"sport": sport_id, "query": q, "teams": [], "source": "TheSportsDB", "mode": "provider_unavailable", "count": 0, "message": "Live team search could not reach the provider. Try again later.", "error_type": type(exc).__name__, "generated_at": now_utc()}

@app.get("/api/live/matches")
def live_matches(sport: str = Query(...), date: str = Query(default="")):
    sport_id = validate_sport(sport)
    category, league = PROVIDER_SPORTS[sport_id]
    if not league:
        return {"sport": sport_id, "matches": [], "source": "ESPN", "mode": "unsupported_provider_sport", "message": "The current scoreboard adapter does not provide tennis fixtures.", "generated_at": now_utc()}
    params = urllib.parse.urlencode({"dates": date} if date else {})
    url = f"https://site.api.espn.com/apis/site/v2/sports/{category}/{league}/scoreboard"
    if params:
        url += "?" + params
    try:
        data = provider_json(url)
        events = data.get("events") or []
        results = []
        for event in events:
            competitions = event.get("competitions") or []
            comp = competitions[0] if competitions else {}
            competitors = comp.get("competitors") or []
            home = next((x for x in competitors if x.get("homeAway") == "home"), {})
            away = next((x for x in competitors if x.get("homeAway") == "away"), {})
            results.append({
                "id": event.get("id"),
                "name": event.get("name") or event.get("shortName") or "",
                "date": event.get("date") or "",
                "status": ((event.get("status") or {}).get("type") or {}).get("description", ""),
                "home_team": (home.get("team") or {}).get("displayName", ""),
                "away_team": (away.get("team") or {}).get("displayName", ""),
                "home_score": home.get("score"),
                "away_score": away.get("score"),
                "sport": sport_id,
                "source": "ESPN public scoreboard",
            })
        return {"sport": sport_id, "matches": results, "source": "ESPN public scoreboard", "mode": "live_provider", "count": len(results), "generated_at": now_utc()}
    except Exception as exc:
        return {"sport": sport_id, "matches": [], "source": "ESPN public scoreboard", "mode": "provider_unavailable", "count": 0, "message": "The scoreboard provider could not be reached. Try again later.", "error_type": type(exc).__name__, "generated_at": now_utc()}


@app.get("/api/live/roster")
def live_roster(sport: str = Query(...), team_id: str = Query(..., min_length=1)):
    sport_id = validate_sport(sport)
    category, league = PROVIDER_SPORTS[sport_id]
    if not league:
        return {"sport": sport_id, "players": [], "mode": "unsupported_provider_sport"}
    url = f"https://site.api.espn.com/apis/site/v2/sports/{category}/{league}/teams/{urllib.parse.quote(team_id)}/roster"
    try:
        data = provider_json(url)
        athletes = data.get("athletes") or []
        if athletes and isinstance(athletes[0], dict) and "items" in athletes[0]:
            athletes = [p for group in athletes for p in (group.get("items") or [])]
        players = []
        for p in athletes:
            if not (p.get("fullName") or p.get("displayName")):
                continue
            position = p.get("position") or {}
            headshot = p.get("headshot") or {}
            players.append({"id": str(p.get("id") or ""), "name": p.get("fullName") or p.get("displayName"), "position": position.get("abbreviation", "") if isinstance(position, dict) else str(position), "jersey": p.get("jersey") or "", "headshot": headshot.get("href", "") if isinstance(headshot, dict) else "", "source": "ESPN roster"})
        return {"sport": sport_id, "team_id": team_id, "players": players, "count": len(players), "source": "ESPN roster", "mode": "live_provider"}
    except Exception as exc:
        return {"sport": sport_id, "team_id": team_id, "players": [], "count": 0, "mode": "provider_unavailable", "message": "Team roster could not be loaded.", "error_type": type(exc).__name__}
