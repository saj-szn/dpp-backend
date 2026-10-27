# Unified player research providers

DPP exposes a single search endpoint that fans out to configured sources and returns each result with its source and status:

`GET /api/player/research?sport=football&q=Erling%20Haaland`

Optional provider IDs:
- `pitch_player_id`: PitchAPI player ID (PitchAPI IDs are not the same as ESPN or TheSportsDB IDs).
- `espn_player_id`: ESPN athlete ID for the ESPN game-log endpoint.
- `count`: number of saved-history/game-log records to return (1-20).

Provider readiness:
- DPP local history: reads records already imported into the backend's SQLite database.
- TheSportsDB: public test-key player lookup.
- SportScore: public search endpoint; DPP must show visible attribution, **Powered by SportScore**, as required by its free API terms.
- PitchAPI: requires the free key in the server-side `PITCHAPI_API_KEY` environment variable. Its player-profile endpoint requires a PitchAPI player ID; IDs must not be guessed or mixed with IDs from other sources.
- ParlayAPI: requires the free account key in the server-side `PARLAY_API_KEY` environment variable. Its free tier is quota-limited; check the provider's current free-tier rules and actual response coverage. No paid plan is required by this code path.
- ESPN game log: requires an ESPN athlete ID; public endpoints are unofficial and coverage can vary.

The API returns partial results if one source fails. It never fabricates sportsbook lines. If no provider returns an actual line, the frontend should label any calculated result as a DPP estimate, not a bookmaker offer.

## Important safety/deployment notes

This feature is on the `feature/unified-player-research` branch only. It has not been merged or deployed to Render. The current live service is intentionally untouched.

Before merging/deploying:
1. Run Python syntax/import checks and API tests.
2. Test each provider with real sample responses and confirm free-tier coverage.
3. Check duplicate-player identity matching and source attribution in the Flet UI.
4. Verify API keys are only in Render environment variables, never in the app or repository.
5. Run the full DPP checklist, including ESPN runtime behavior and verifying scoreboard results are not misrepresented as sportsbook prop lines.
