# Astra sketch UI update

This build remaps the dashboard to the homeowner sketch:

1. **Auto Astra watering**
   - zone selector chips
   - time / days / watering duration
   - zone health grade on the right
2. **Manual watering**
   - zone select
   - watering time
   - start / stop
3. **Astra's message**
   - clear homeowner-facing text output
4. **Homeowner input**
   - typed chat to Astra
5. **Sprinkler settings**
   - separate popup for normal sprinkler controls
6. **AI settings**
   - separate popup for Astra controls and limits
7. **Mic button**
   - click once to listen, click again to stop
   - voice commands must start with "Astra"
8. **Astra's logged zone history**
   - per-zone trend cards on the main page
9. **Advanced details**
   - deeper popup with zone trends, recent decisions, and alerts

## Main UX direction

- Technical language was reduced on the main page.
- Background automation is intentionally hidden from the homeowner unless they open settings or advanced details.
- Astra is placed in a dedicated right-side presence panel and visually leans into the interface.
- Chrome panels, shadows, and raised neon-green borders match the approved visual direction.

## Current scope

- The UI and settings flow are fully wired.
- The advanced detail popup reads from existing decision and incident endpoints when logs exist.
- The small trend charts are UI-level previews and become more meaningful as real logging builds up.
