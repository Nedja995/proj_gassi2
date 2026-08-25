# GASSI — New Session Handoff Document

Read this before starting any work. It captures everything needed to continue
development without going through previous chat history.

---

## What GASSI Is

A Windows desktop overlay (Python/tkinter) that provides real-time AI strategy advice
for PC games via screen capture + Gemini API. No game memory reading — pure CV + overlay.

**Current state:** v0.5.16, production-tested on Timberborn and Nebuchadnezzar.
F1 (Advisor), F2 (Placement + grid overlay + cell highlight), Settings, Calibration all working.

**Repo:** `F:\__STORAGE\__PROJECTS_F\proj-gassi\proj_gassi2`
**Stack:** Python 3.12, tkinter/ttk, pydantic-settings, mss, RapidOCR (ONNX), google-genai,
pynput, opencv-python-headless, pywin32, uv package manager

---

## Key Docs — Read On Demand, Not Upfront

**Read all these at session start**
This handoff doc is designed to be self-contained for starting work.

- `TODO.md` — only if planning the next milestone or checking roadmap ordering
- `CHANGELOG.md` — only if debugging a regression or checking what changed in a specific version
- `docs/architecture.md` — only if making a non-obvious design decision (check if an AD already covers it)
- `docs/adding_game_pack.md` — only when adding a new game pack
- `docs/v1_scope.md` — only when updating the known limitations or scope

**Source files:** read only the specific files the task touches. Never edit from memory.

---

## Architecture — Quick Summary

**Pattern:** MVVM. Models (Pydantic) → ViewModel (`assistant_viewmodel.py`) → Views (tkinter).
ViewModel owns the mode FSM (IDLE/ADVISOR/PLACEMENT), all AI call dispatch, cooldown, debug.

**Protocol abstractions** (in `core/ai/protocol.py`, `core/capture/protocol.py`):
- `AiBackend` — currently `GeminiBackend`. Swap in Claude/Ollama without touching ViewModel.
- `CaptureBackend` — currently `MssCaptureBackend`.
- `CaptureRegionProvider` — currently overlay-anchored. Future: native window detection.

**Async bridge:** dedicated asyncio thread + `queue.Queue` → tkinter `after()` at 50ms.
AI calls never block the UI thread. Pattern is in `core/async_bridge.py`.

**Game packs:** folder convention `game_packs/<game_id>/manifest.yaml` + `prompts/`.
No plugin system. Adding a game = adding a folder. See `docs/adding_game_pack.md`.

---

## Platform-Specific Code Pattern

All platform-specific code uses `platform.system()` + `try/except ImportError` fail-open.
This pattern is used everywhere — never break it.

```python
if platform.system() == "Windows":
    try:
        import win32gui
        # windows-specific code
    except ImportError:
        logger.debug("pywin32 not available — skipping")
elif platform.system() == "Darwin":
    try:
        from AppKit import NSApp
        # macos-specific code
    except ImportError:
        logger.debug("pyobjc not available — skipping")
# Linux: silently no-op or alpha fallback
```

**Critical Windows lessons learned (document in every relevant file):**
- `WS_EX_LAYERED` + `SetLayeredWindowAttributes(LWA_COLORKEY)` + tkinter Canvas
  (GDI child window) = DOES NOT WORK on Windows 10/11 DWM. Causes solid black overlay.
  Use `SetWindowRgn` instead (AD-24).
- `win32gui` does NOT have `CreateRectRgn` — that is a GDI32 function.
  Use `ctypes.windll.gdi32.CreateRectRgn` directly.
- `winfo_id()` on a Toplevel returns the correct HWND directly.
  Do NOT use `GetAncestor(GA_ROOT)` — for tkinter Toplevels that returns the
  main Tk window HWND, not the Toplevel's HWND.
- `withdraw()` / `deiconify()` on `overrideredirect(True)` Toplevels recreates the HWND
  on Windows, losing all WS_EX_* style bits. Use geometry() to move off-screen instead.
- Call `top.update()` (not `update_idletasks()`) before any win32 calls — ensures
  the Win32 window is fully mapped and sized before region/style operations.

---

## Naming Conventions

- Python: PEP8, `snake_case`. Private: `_underscore_prefix`. Names should be informative.
- Prefer `ttk` over `tk` widgets. Prefer subclassing.
- Variable names: low case snake, slightly longer descriptive names preferred.
- No hardcoded version strings anywhere except `pyproject.toml`.
- Never remove markdown from prompts. Never simplify documentation without instruction.

---

## Version and Commit Discipline

**Every feature is split into discrete sub-versions** (e.g. v0.4.1, v0.4.2, v0.4.3).
Each sub-version gets its own commit. Docs (CHANGELOG, TODO, pyproject.toml) are committed
separately as a final commit per batch.

**Commit structure per sub-version:**
```bash
# Code commit — only files changed for that specific sub-version
git add <specific files only>
git commit -m "v0.X.Y: short description of what changed"

# Docs commit — after all sub-versions in a batch are done
git add CHANGELOG.md TODO.md pyproject.toml
git commit -m "docs: changelog, todo, pyproject for v0.X.Y-v0.X.Z"
```

**Never** `git add .` — always add specific files so each commit is clean and revertable.

**pyproject.toml version** must be bumped with every sub-version.

---

## Mandatory Doc Updates Per Task

Every task must update ALL of these:
1. `CHANGELOG.md` — add `## [X.Y.Z] - YYYY-MM-DD` section with Added/Fixed/Changed
2. `TODO.md` — mark completed items `[x]`, add new sub-version to Completed section
3. `pyproject.toml` — bump `version = "X.Y.Z"`
4. `docs/architecture.md` — add ADR if a non-obvious design decision was made
5. `README.md` — update Features section version number and feature list if visible behaviour changed

---

## Current Roadmap Summary

```
v0.4.7  ✅ Complete — Nebuchadnezzar + Timberborn live testing
v0.5.x  ✅ Complete (v0.5.1–v0.5.18) — GamePackManifest fields, atomic settings,
           calibration fixes, hotkey fixes, placement highlight (SetWindowRgn),
           Nebuchadnezzar advisor tuning, prompt fixes, status messages
v0.6.0  ✅ Complete (v0.6.1–v0.6.7) — RAG pipeline (Chroma + ONNXMiniLM,
           ingestion CLI, Timberborn + Nebuchadnezzar knowledge bases,
           ViewModel injection, version filtering, docs)
v0.7.0  🔜 Next — Multi-backend (ClaudeBackend, building footprints)
v0.7.1  — Local SLM (Ollama, Qwen2.5-VL)
v0.8.0  — Platform (Wayland, native window detection, macOS, SteamOS)
v0.8.1  — Anti-cheat posture (SetWindowDisplayAffinity)
v0.8.2  — Distribution (PyInstaller, installer, TTS)
v0.9.0  — UX polish (floating advice/placement windows, accessibility)
```

---

## Active Game Packs

### Timberborn (v0.6) — Primary, fully tested
- HUD regions: `top_resource_bar`, `population_panel`, `cycle_time_panel`
- `hud_regions_user.yaml` exists and working (5 regions)
- `cycle_time_panel` manually added — Gemini consistently misses it in auto-calibration
- Advisor source: OCR (default) + Screenshot fallback

### Nebuchadnezzar (v1.0) — Secondary, live-tested
- HUD regions: `resource_bar`, `date_time_panel`, `objectives_panel`
- `objectives_panel` manually corrected to x=0.838 (calibration keeps placing it at x=0.43)
- `preferred_advisor_source: screenshot` — OCR unreliable until regions stabilise
- `hud_regions_user.yaml` exists and working (3 regions)
- No Borderless Windowed mode — test in Windowed mode only

---

## Key Technical Decisions Already Made

| Decision | What was chosen | Why / Don't reverse without reading AD |
|---|---|---|
| Transparency for overlay highlight | `SetWindowRgn` | AD-24. WS_EX_LAYERED+LWA_COLORKEY fails on DWM |
| Win32 API calls | `ctypes` directly | `win32gui` lacks GDI32 functions like CreateRectRgn |
| HWND for Toplevel | `winfo_id()` directly | GetAncestor(GA_ROOT) returns wrong window for tkinter |
| Hide/show Toplevel | Move off-screen via geometry() | withdraw() recreates HWND, loses style bits |
| OCR engine | RapidOCR (ONNX) | AD-06. EasyOCR needs PyTorch, Tesseract needs binary |
| Game pack format | YAML folder convention | AD-08. No plugin system until 2+ packs existed |
| Region coordinates | Fractional 0.0–1.0 | AD-09. Survives resolution changes |
| Async bridge | Thread + queue | AD-10. tkinter not thread-safe |
| Settings storage | JSON in app data | AD-17. pydantic-settings is read-only |
| Window chrome | overrideredirect(True) | AD-18. Native titlebar irrelevant for overlay |

---

## Calibration Service — Known Quirks

Gemini returns coordinates in three inconsistent scales:
- `0.0–1.0` fractions (correct)
- `0–100` percentages (divide by 100)
- pixel coordinates (divide by img_w/img_h)

Scale is auto-detected by `max(x, y, w, h)` value:
- `> 100` → pixel coords
- `> 1.0` → percentages
- `≤ 1.0` → already correct

Gemini also invents different label names each run (`top_bar_resources`, `resource_bar_top`,
`top_resource_bar` for the same region). The calibration prompt lists canonical names to steer
it, but manual correction of `hud_regions_user.yaml` may still be needed.

Region labels in `hud_regions_user.yaml` must match `LABEL_CONFIGS` in `preprocessor.py`
for the correct OCR preprocessing config to be applied. Check after any calibration run.

---

## Placement Highlight — How It Works (AD-24)

`PlacementHighlightWindow` in `views/placement_highlight.py`:
1. F2 placement query → Gemini returns `{"cell": "H5", "advice": "..."}` JSON
2. `cell_to_screen_pixels()` converts cell ref to `(x, y, w, h)` screen rect
3. `PlacementHighlightWindow.show()` is called with the pixel rect
4. A `tk.Toplevel` with `overrideredirect(True)` is positioned at the cell
5. `ctypes.windll.gdi32.CreateRectRgn` + `CombineRgn` creates hollow frame region
6. `ctypes.windll.user32.SetWindowRgn` clips the window to just the outline + label
7. `WS_EX_TRANSPARENT` (no WS_EX_LAYERED) makes the outline strip click-through
8. Window moves off-screen (not withdrawn) when cleared — preserves HWND and styles
9. Auto-dismisses after `placement_highlight_seconds` (default 8s)

---

## Prompts — Key Rules

Every `advisor_ocr.txt` and `advisor_screenshot.txt` must include:
> `NEVER ask the player for more information. If a region is missing or unclear,
> give your best advice based on whatever data is available.`

Every `placement.txt` must include:
> `IMPORTANT: The grid covers the ENTIRE screenshot including UI panels and non-game areas.
> Only reference cells that fall within the visible game map area.
> Describe the cell using visible in-game landmarks so the player can find it even
> if the cell highlight appears in the wrong screen position.`

Placement response format (JSON, enforced via `response_schema`):
```json
{"cell": "H5", "advice": "## Cell H5 — description\n- bullet 1\n- bullet 2"}
```

---

## Hotkey Format (pynput)

After v0.5.7 fix — correct pynput hotkey string format:
- Single printable char: `a`, `8`, `0` (NO angle brackets)
- Special keys: `<f1>`, `<f2>`, `<space>`, `<escape>`
- Combos: `<alt>+8`, `<ctrl>+<f1>`, `<shift>+a`

Old broken format (`<alt>+<8>`) would cause `<alt>` alone to trigger via pynput.
If a user reports "hotkey fires on modifier alone", check their `settings.json` for
`<X>+<Y>` where Y is a printable char — they need to rebind in Settings.

`HotkeyManager.register()` rejects modifier-only strings (e.g. `<alt>`) with a warning.

---

## macOS / Linux Status

Platform-specific code follows fail-open pattern. Current state:
- **Click-through:** Windows only (pywin32). macOS: pyobjc stub. Linux: no-op.
- **PlacementHighlightWindow:** Windows: SetWindowRgn (working). Others: alpha=0.75 fallback.
- **Focus check:** Windows only (pywin32 GetForegroundWindow). Others: always returns True.
- **Improvement path:** v0.7.0 milestone — NSWindow APIs (macOS), XShapeCombineRectangles (X11).

Developer works remotely on MacBook but GASSI runs and is tested on Windows PC.

---

## Session Start Protocol

**Paste this into the new chat to begin:**

> Read these files in order before we start:
> 1. `F:\__STORAGE\__PROJECTS_F\proj-gassi\proj_gassi2\docs\session_handoff.md`
> 2. `F:\__STORAGE\__PROJECTS_F\proj-gassi\proj_gassi2\TODO.md`
> 3. `F:\__STORAGE\__PROJECTS_F\proj-gassi\proj_gassi2\CHANGELOG.md`
> 4. `F:\__STORAGE\__PROJECTS_F\proj-gassi\proj_gassi2\docs\architecture.md`
> Then tell me what's missing before we start.

**Read on demand only (not at session start):**
- `docs/adding_game_pack.md` — only when adding a new game pack
- `docs/v1_scope.md` — only when updating known limitations or scope
- **Source files** — read only the specific files the task touches. Never edit from memory.

**Keep this file updated** as the project evolves:
- After any major architectural decision (new AD added) — summarise it here
- After a milestone is complete — update the roadmap summary section
- After a new "lesson learned" — add it to the relevant section
- After a new game pack reaches tested status — update the game packs section

No version bump needed — this is a living doc, not a changelog entry.
