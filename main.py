
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="DPP Backend",
    description="D Players Props sports analytics API",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET"],
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


def response_status():
    return {
        "mode": "demo",
        "message": "Real sports data is not connected yet.",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/")
def home():
    return {
        "app": "D Players Props",
        "status": "online",
        **response_status(),
    }


@app.get("/health")
def health():
    return {"status": "healthy", **response_status()}


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
    sport_id = sport_id.lower()

    if sport_id not in SPORTS:
        raise HTTPException(
            status_code=404,
            detail="Sport not found.",
        )

    return {
        "id": sport_id,
        "name": SPORTS[sport_id],
        **response_status(),
    }


@app.get("/api/teams")
def list_teams(sport: str = Query(...)):
    sport_id = sport.lower()

    if sport_id not in SPORTS:
        raise HTTPException(
            status_code=404,
            detail="Sport not found.",
        )

    return {
        "sport": sport_id,
        "teams": [],
        **response_status(),
    }


@app.get("/api/players")
def list_players(sport: str = Query(...)):
    sport_id = sport.lower()

    if sport_id not in SPORTS:
        raise HTTPException(
            status_code=404,
            detail="Sport not found.",
        )

    return {
        "sport": sport_id,
        "players": [],
        **response_status(),
    }


@app.get("/api/matches")
def list_matches(
    sport: str = Query(...),
    limit: int = Query(default=10, ge=1, le=50),
):
    sport_id = sport.lower()

    if sport_id not in SPORTS:
        raise HTTPException(
            status_code=404,
            detail="Sport not found.",
        )

    return {
        "sport": sport_id,
        "limit": limit,
        "matches": [],
        **response_status(),
    }


@app.get("/api/history")
def get_history(
    sport: str = Query(...),
    entity_type: str = Query(...),
    entity_id: str = Query(..., min_length=1),
    count: int = Query(default=5, ge=1, le=20),
):
    sport_id = sport.lower()

    if sport_id not in SPORTS:
        raise HTTPException(
            status_code=404,
            detail="Sport not found.",
        )

    if entity_type not in ["player", "team"]:
        raise HTTPException(
            status_code=400,
            detail="entity_type must be player or team.",
        )

    return {
        "sport": sport_id,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "requested_matches": count,
        "records": [],
        **response_status(),
    }
