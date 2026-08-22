# Changelog

All notable changes to GASSI will be documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

See [TODO.md](TODO.md) for the full roadmap.

## [0.1.1] - 2026-08-22

### Added
- Theme system: all visual constants extracted to `Theme` model with 3 presets (dark, midnight, forest)
- Theme selection via `GASSI_THEME_NAME` env var
- Collapsible overlay: ▲/▼ button toggles toolbar-only strip; auto-expands when results arrive
- Slide-off-screen: ◀ button hides overlay entirely, leaving a small ▶ pull-tab at the left edge to restore
- Custom frameless window (overrideredirect) — no native titlebar, fully custom toolbar
- Custom toolbar: ◀ slide | ▲ collapse | GASSI status | 🔓 lock | ✕ close
- Markdown bold rendering: `**text**` in Gemini responses renders as actual bold
- Auto-hide during capture: overlay withdraws before screenshot to avoid capturing itself
- Cooldown timer in footer bar with visible countdown after each API call
- Footer hotkey hints in accent green: `F1 Advisor │ F2 Placement │ F3 Lock`
- F3 hotkey for click-through lock toggle
- PlacementPromptDialog: themed modal for typing placement questions (F2)
- Close button with proper cleanup handler (replaces native window close)

### Changed
- Toolbar compact (22px) with icon-only buttons, smaller dimmer title
- Footer guaranteed visible (packed before canvas in layout order)
- All captures (F1 screenshot fallback, F2 placement) now use full-screen grab
- Single-shot query model: no auto-polling, each hotkey press = one API call + cooldown
- Combined all HUD regions into single API call per advisor query (was 3 separate calls)
- Default Gemini model: gemini-3.6-flash (2.5-flash unavailable for new accounts)
- Default cooldown: 15 seconds between queries (rate limit protection)
- Migrated from Poetry to uv (pyproject.toml converted to PEP 621 standard)

### Fixed
- Overlay no longer captures itself in screenshots (withdraw/deiconify pattern)
- Advisor results no longer overwrite each other (single combined call)
- Rate limiting: was hitting 429 RESOURCE_EXHAUSTED at 36 req/min, now ~4 req/min max
- Click-through was always-on at startup making window unmovable
- Slide-off-screen now uses withdraw/deiconify (negative coordinates were unreliable on Windows)

## [0.1.0] - 2026-08-22

### Added
- Project scaffold: MVVM architecture with Protocol-based abstractions
- Advisor mode with two input sources (OCR via RapidOCR, Screenshot)
- Placement mode with free-text spatial advice (no grid)
- Gemini AI backend (google-genai SDK)
- Screen capture via mss
- Overlay-anchored capture region (manual window positioning)
- Layered OverlayCanvas (text/highlights/arrows/overlays layers scaffolded)
- Async-to-tkinter bridge (thread + queue pattern)
- Global hotkey manager via pynput (F1, Shift+F1, F2)
- Per-OS overlay transparency and click-through (Windows/macOS/Linux)
- Game pack system: folder convention + manifest.yaml + prompt files
- Timberborn game pack (v0.6) with 3 HUD regions and 3 system prompts
- API key storage via OS keyring
- AppSettings via pydantic-settings with env var override
- OCR confidence-gated fallback to screenshot
- API error backoff and cooldown
