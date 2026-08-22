# Changelog

All notable changes to GASSI will be documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.1] - Unreleased

### Added
- Theme system: all visual constants extracted to `Theme` model (dark, midnight, forest presets)
- Collapsible overlay: toolbar-only strip mode via ▼/▲ button, auto-expands when results arrive
- Markdown bold rendering: `**text**` in Gemini responses renders as bold in the overlay
- Auto-hide during capture: overlay withdraws before screenshot to avoid capturing itself
- Theme selection via `GASSI_THEME_NAME` env var
- Cooldown timer in footer bar

### Changed
- Toolbar is now compact (22px) with icon-only buttons
- Footer reduced to 18px with abbreviated hotkey hints
- All captures (F1 screenshot, F2 placement) now use full-screen grab
- Single-shot query model: no auto-polling, each hotkey press = one API call
- PlacementPromptDialog now themed consistently with overlay

See [TODO.md](TODO.md) for the full roadmap.

## [0.1.0] - Unreleased

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
