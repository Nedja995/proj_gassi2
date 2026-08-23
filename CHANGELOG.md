# Changelog

All notable changes to GASSI will be documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

See [TODO.md](TODO.md) for the full roadmap.

## [0.2.0] - 2026-08-23

### Fixed
- **OCR advisor capturing wrong screen area** — HUD region fractions were being
  resolved against the overlay window rect instead of the primary monitor dimensions.
  All OCR regions returned confidence 0.00 and fell back to screenshot every time.
  Fixed: `_process_ocr_advisor` now calls `region_provider.get_monitor_rect()` for
  region resolution; `get_monitor_rect()` added to `OverlayAnchoredRegionProvider`.
- **Overlay flickering during OCR** — overlay was withdrawn/deiconified once per
  HUD region (N times). Fixed: single withdraw before the capture loop, restore in
  `finally` block. All region crops happen in one hidden window cycle.
- **Stale `capture_rect` parameter** — `_process_ocr_advisor` and
  `_process_screenshot_advisor` both had an unused `capture_rect` param from v1
  design. Removed; callers simplified.

### Added
- **`CalibrationService`** (`core/calibration_service.py`): one-shot Gemini multimodal call with
  `response_schema` that returns HUD region bounding boxes as fractions. Each region immediately
  validated by RapidOCR — rejected if confidence below threshold or geometry is invalid.
- **`hud_regions_user.yaml`** override: calibration result saved per game pack, never overwrites
  `manifest.yaml` developer defaults. Delete to revert to defaults.
- **`GamePackLoader`** updated: checks `hud_regions_user.yaml` first, falls back to `manifest.yaml`.
  Logs which source is active at startup.
- **`CalibrationDialog`** (`views/calibration_dialog.py`): modal dialog with indeterminate progress
  bar, per-region ✓/✗ result list with confidence scores, "Clear User Calibration" button.
  Runs calibration in a background thread — UI stays responsive.
- **"Calibrate HUD" button** in Settings → General tab. Separator + description text. Only rendered
  when `CalibrationService` is wired (graceful degradation if not available).
- `MainOverlay.set_calibration_service()` setter — same pattern as `set_close_handler`.
- AD-22 added to `docs/architecture.md`.

## [0.1.3] - 2026-08-23

### Added
- **Window resizable:** `◢` grip in bottom-right corner, drag to resize. Respects `window_min_width`/`window_min_height` from theme. Uses `x_root`/`y_root` for stable delta tracking.
- **Footer cooldown label:** fixed `width=12, anchor="e"` so it always has reserved space; hints text shortened to prevent clipping.
- **`docs/adding_game_pack.md`:** complete guide for new game packs — folder convention, manifest
  calibration walkthrough (F4 → measure → fractions), prompt templates for all 3 modes,
  early/mid/late stage design process (signal identification, stage clause format, synthetic HUD testing),
  and a go/no-go checklist.
- **README.md** rewritten to v0.1.3: full hotkey table, all current features, updated project
  structure tree, prompt iteration usage, link to adding_game_pack.md.
- `update_cooldown(text, fg)` accepts an optional foreground colour; propagates through `OverlayCanvas` delegate to `MainOverlay`. Countdown stays amber (`fg_warning`); ready flash uses `fg_accent` (theme-aware).
- **Debug frame save (F4):** saves last captured frame (advisor or placement) as timestamped PNG to
  `<config_dir>/debug_frames/`. Auto-prunes to 50 frames. Confirmation shown in overlay.
- **DebugManager** (`core/debug_manager.py`): frame storage, save-to-disk, auto-prune, debug dir resolution.
- **OverlayLogHandler** (`core/log_handler.py`): in-memory `logging.Handler` that buffers last N
  formatted records in a `deque`; feeds the overlay log panel without any file I/O.
- **LogPanel** (`views/log_panel.py`): collapsible scrollable log viewer panel inside the overlay.
  Auto-refreshes at 500ms intervals when visible. Per-level colour coding (DEBUG/INFO/WARNING/ERROR).
  Clear button. Horizontal scroll for long lines.
- **Log panel toggle (⌨ button)** in toolbar — button only visible when log handler is wired in.
- `hotkey_debug_save_frame` setting (default `<f4>`) added to `AppSettings`.
- `debug_log_max_lines` setting (default 200) added to `AppSettings`.
- Footer hint updated: `F4 DbgSave` added.
- Startup log now includes debug frames directory path.
- **Prompt rewrite — all three Timberborn prompts tightened:**
  - Removed duplicate GAME KNOWLEDGE blocks (same block was in both advisor prompts verbatim).
  - Eliminated numbered task lists and "RESPONSE FORMAT" headers; replaced with a single RULES line.
  - Removed example quotes from advisor prompts; kept one spatially-specific example in placement prompt.
  - Added explicit early-game detection clause (Day 1–15 → beginner focus) in both advisor prompts.
  - Hard output constraint: "plain sentences only — no markdown, no bullet points, no headers. Max 4 lines."
  - Token reduction: ~40% fewer prompt tokens per advisor call vs. previous version.
- **Prompt iteration tool** (`tests/prompt_iteration.py`): standalone CLI for testing prompts against
  saved screenshots or OCR text without running the full app. Reads prompts live from disk.

### Changed
- `AssistantViewModel.__init__` accepts `debug_manager: DebugManager` parameter.
- `MainOverlay.__init__` accepts optional `log_handler: OverlayLogHandler` parameter.
- Every `_capture_without_overlay` call in the ViewModel now stores the frame in `DebugManager`.
- `main.py` logging setup: `OverlayLogHandler` attached to root logger before `basicConfig`
  so all records (including startup) are captured.
- `main.py` logger moved inside `main()` to ensure handler is attached first.

## [0.1.2] - 2026-08-23

### Added
- Settings dialog accessible via ⚙ gear icon in toolbar
- Hotkeys tab: rebindable key capture for all 4 hotkeys (advisor, source switch, placement, lock)
- General tab: theme picker, cooldown slider, AI model field, default input source
- Persistent settings: saved to JSON in OS app data dir (`%LOCALAPPDATA%\gassi\settings.json` on Windows)
- Window position/size saved on close and restored on next launch
- Settings loaded at startup and merged with env var / pydantic defaults
- Settings manager module (`core/settings_manager.py`)

### Changed
- Toolbar now includes ⚙ gear button between lock and close
- Startup reads saved settings.json before constructing components
- Cooldown changes from settings dialog apply immediately without restart

## [0.1.1] - 2026-08-22

### Added
- Theme system: all visual constants extracted to `Theme` model with 3 presets (dark, midnight, forest)
- Theme selection via `GASSI_THEME_NAME` env var
- Collapsible overlay: ▲/▼ button toggles toolbar-only strip; auto-expands when results arrive
- Slide-off-screen: ◀ button hides overlay entirely, leaving a small ▶ pull-tab to restore
- Custom frameless window (overrideredirect) — no native titlebar, fully custom toolbar
- Custom toolbar layout: ◀ slide | ▲ collapse | GASSI status | ⚙ settings | 🔓 lock | ✕ close
- Markdown bold rendering: `**text**` in Gemini responses renders as actual bold
- Auto-hide during capture: overlay withdraws before screenshot to avoid capturing itself
- Cooldown timer in footer bar with visible countdown after each API call
- Footer hotkey hints in accent green
- F3 hotkey for click-through lock toggle
- PlacementPromptDialog: themed modal for typing placement questions
- Close button with proper cleanup handler

### Changed
- Toolbar compact (22px) with icon-only buttons
- Footer guaranteed visible (packed before canvas in layout order)
- All captures (F1 screenshot fallback, F2 placement) now use full-screen grab
- Single-shot query model: no auto-polling, each hotkey press = one API call + cooldown
- Combined all HUD regions into single API call per advisor query
- Default Gemini model: gemini-3.6-flash
- Default cooldown: 15 seconds
- Migrated from Poetry to uv (PEP 621 pyproject.toml)

### Fixed
- Overlay no longer captures itself in screenshots (withdraw/deiconify pattern)
- Advisor results no longer overwrite each other (single combined call)
- Rate limiting: reduced from 36 req/min to ~4 req/min max
- Click-through was always-on at startup making window unmovable
- Slide-off-screen uses withdraw/deiconify (negative coordinates were unreliable)
- Footer visibility guaranteed regardless of window size

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
