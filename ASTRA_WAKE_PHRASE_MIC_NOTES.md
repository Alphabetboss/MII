# Astra wake phrase + laptop mic ("responds to her name")

## What changed
- The **mic button** in the Astra Station UI now uses **browser speech recognition** (when available) for **laptop testing**.
- It **requires the wake word** (default: **Astra**) to be present in the spoken transcript before sending a command to the backend.
- If you speak without the wake word, Astra will prompt you to try again **with her name**.

## How to test on a laptop
1. Run the app in laptop mode and open the UI in your browser.
2. Click the **mic** button and **allow microphone access** when the browser asks.
3. Say a command that includes the wake word, for example:
   - “Astra, status report.”
   - “Astra, run zone 1 for 10 minutes.”
   - “Astra, stop all zones.”

## Notes / gotchas
- Best results in **Chrome** or **Edge** (they tend to support the Web Speech API more consistently).
- This is **laptop-only convenience STT**. On the Pi, fully offline microphone STT/wake-word is a future module (bookmark: local wake-word + offline STT).
- Typed commands already work everywhere (no mic needed): start your message with **Astra**.
