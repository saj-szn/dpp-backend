# DPP Web Preview

This directory contains a responsive browser interface for D Players Props.

## Run it
Open `index.html` in a browser or publish the `web/` directory using a static hosting service. By default, it calls the current API at `https://dpp-backend-n7qo.onrender.com`. To point it elsewhere, set `window.DPP_API_BASE` before the app script runs.

## Important data integrity notes
- The interface displays data returned by the backend; it does not create or imply real sportsbook prop lines.
- Backend responses may contain demo or manually imported data. Verify source, freshness, and coverage before relying on results.
- CSV upload works only if the deployed API's import route accepts the selected file format.
- Do not put provider API keys or other secrets in this static frontend.
- This is a preview UI. It does not change the Render production service or its database.
