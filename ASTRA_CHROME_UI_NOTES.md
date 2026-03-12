# Astra Chrome UI Upgrade

This package swaps in the approved Astra render as the default avatar and restyles the dashboard with a chrome panel system, raised neon-green borders, deeper shadows, and more color accents.

What changed:
- `static/astra-avatar.png` now uses the approved full-body render
- `static/app.css` was rebuilt around the chrome + raised neon style
- `templates/dashboard.html` title and hero copy were updated to match the new visual direction

Notes:
- This uses the exact approved render for Astra, so she matches the selected concept art.
- The avatar has whole-body motion/glow effects in CSS, but not fully rigged limb-by-limb animation. A true articulated body would require a Blender/GLB pipeline.
