Astra UI refresh

- Restores a cleaner, image-matched chrome layout with less technical jargon.
- Pushes most automation into the background so the main screen focuses on what the homeowner cares about.
- Adds Sprinkler settings and AI settings panels.
- AI settings now include:
  * People Avoidance
  * Animal Deterrent (time window + distance)
  * Astra Intelligent Override (bounded watering-time adjustment limit)

These settings are persisted in data/ui_settings.json and are available through:
- GET /api/settings
- POST /api/settings/sprinkler
- POST /api/settings/ai
