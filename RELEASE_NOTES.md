# GASSI v0.8.5-beta — Release Notes

**First public beta release.**

GASSI is a desktop overlay that gives you real-time AI strategy advice for PC games.
It captures your screen, analyzes it via Google Gemini AI, and displays advice as a
translucent overlay on top of your game. No mods, no memory reading — just screen
capture and AI.

---

## Supported Games

- **Timberborn** (v0.6) — resource management, water systems, drought cycles, building placement
- **Nebuchadnezzar** (v1.0) — housing evolution, bazaar distribution, production chains

## What You Need

- **Windows 10 or 11** (64-bit)
- A **Google Gemini API key** (free tier available — 1500 requests/day)
  - Get one at: https://aistudio.google.com/apikey

## Installation

1. Download `GASSI-v0.8.5-beta-win64.zip` from the release assets
2. Extract the zip to any folder (e.g. `C:\Games\GASSI\`)
3. Run `gassi.exe`
4. On first run, a Settings dialog opens automatically
5. Paste your **Gemini API key** into the "Gemini API key" field
6. Click **Save & Close**
7. Restart `gassi.exe` — you're ready to play

**No Python installation required. No terminal. No configuration files to edit.**

## How to Use

1. Start your game in **Borderless Windowed** mode (recommended) or Windowed mode
2. Run `gassi.exe` — the overlay appears on top of your game
3. Press **F1** for strategy advice (analyzes your current game state)
4. Press **F2** for placement advice (where to build something)
5. Drag the overlay to reposition, use **◀** to slide it offscreen when not needed

### Hotkeys

| Key | Action |
|-----|--------|
| F1 | Get strategy advice |
| Shift+F1 | Switch between OCR and Screenshot analysis |
| F2 | Placement advice (type your question, e.g. "where should I build a dam?") |
| F3 | Toggle click-through (overlay ignores mouse clicks) |
| F4 | Save debug screenshot |

All hotkeys can be rebound in Settings to avoid conflicts with your game.

## Optional: Claude AI Backend

If you also have an Anthropic Claude API key, you can enter it in Settings and
switch the AI Backend dropdown to "claude". Requires the Claude API key field
to be filled in.

## Known Limitations

- **Beta software** — expect rough edges. Console window stays open for debugging.
- **Fullscreen Exclusive mode not supported** — use Borderless Windowed or Windowed.
  Fullscreen bypasses the Windows compositor, hiding the overlay.
- **RAG knowledge base disabled** — the embedded game knowledge database is not
  included in the beta build. Advice quality is still good using the built-in
  game-specific prompts.
- **Anti-cheat games** — the overlay has not been tested with anti-cheat systems.
  Use at your own discretion. GASSI does NOT read game memory or inject code.
- **Windows only** — macOS and Linux support is planned for a future release.
- **No auto-updater** — check this page for new releases.

## Reporting Issues

If GASSI crashes, the console window will show an error traceback. Please include
that text when reporting issues on the GitHub Issues page.

Common fixes:
- **"No API key set"** — open Settings (⚙) and paste your Gemini API key
- **Overlay not visible** — make sure your game is in Borderless Windowed mode
- **Hotkey conflicts** — rebind hotkeys in Settings → Hotkeys tab

---

*Built with Python, tkinter, Google Gemini AI, and RapidOCR.*
