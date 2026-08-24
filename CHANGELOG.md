# Changelog

All notable changes to GASSI will be documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased] — v0.4.0 Nebuchadnezzar Pack (in progress)

### Added
- `game_packs/nebuchadnezzar/` — second game pack, isometric city-builder (ancient Mesopotamia).
- `manifest.yaml`: 3 HUD regions estimated from reference screenshots — `resource_bar`
  (top-center resource counts), `status_bar` (treasury/month/approval/population),
  `objectives` (top-right mission targets). Requires CalibrationService run to finalize fractions.
- `prompts/advisor_ocr.txt`: full domain knowledge — resources, housing evolution chain,
  bazaar walker system, wells, labor pool, approval delta priority, prestige, 3 game stages.
- `prompts/advisor_screenshot.txt`: screenshot variant with spatial building context.
- `prompts/placement.txt`: grid overlay + JSON response format, Nebuchadnezzar spatial rules.
- 5 quick_prompts in manifest.

See [TODO.md](TODO.md) for remaining items (calibration, OCR validation, prompt iteration).

## [0.4.4] - 2026-08-24

### Added
- **Game switch restart notice**: `_on_settings_saved` in `main.py` detects when
  `active_game_id` changes and immediately shows a markdown notice in the overlay canvas:
  `## Restart required / Active game changed to **<name>** / Save settings and restart GASSI`.
- **Startup log** now includes pack display name: `GASSI v0.4.4 started — game: Nebuchadnezzar (nebuchadnezzar)`.

## [0.4.3] - 2026-08-24

### Fixed
- `SettingsDialog._HEIGHT` increased from 420 to 470px to accommodate the new Active game
  selector row. Previously the Calibrate HUD button clipped or was hidden on standard
  display scaling.

## [0.4.2] - 2026-08-24

### Added
- **Nebuchadnezzar OCR preprocessor configs** (`core/ocr/preprocessor.py`):
  - `NEBU_RESOURCE_BAR_CONFIG`: 4× upscale (digits ~10px), block=11, C=6 — most aggressive,
    targets small white digits on dark decorative icon strip.
  - `NEBU_STATUS_BAR_CONFIG`: 3× upscale, block=13, C=8 — medium white text on dark band.
  - `NEBU_OBJECTIVES_CONFIG`: 2.5× upscale, no denoise, block=15 — clean white text on solid
    dark panel, minimal preprocessing needed.
- All three configs registered in `LABEL_CONFIGS` by region label (`resource_bar`, `status_bar`,
  `objectives`) — automatically picked up by `config_for_label()` at runtime.

## [0.4.1] - 2026-08-24

### Added
- **Active game selector** in Settings → General: `ttk.Combobox` listing all installed game
  packs by display name. Populated at dialog open via `GamePackLoader.list_available_packs()`.
  Selection saved as `active_game_id` in `settings.json` and applied on next GASSI start.
- **`GamePackLoader.list_available_packs()`**: scans `game_packs/` directory, reads each
  `manifest.yaml`, returns `list[tuple[game_id, display_name]]` sorted by display name.
  Skips directories without `manifest.yaml` with a warning log.
- **`MainOverlay.set_pack_loader()`**: setter wiring `GamePackLoader` for the settings dialog.
  Same pattern as `set_calibration_service()`. Called in `main.py` during startup wiring.
- `SettingsDialog` accepts optional `pack_loader: GamePackLoader` parameter. Falls back to
  showing only the current game_id if loader not provided (graceful degradation).

## [0.3.2] - 2026-08-24

### Added
- **`PlacementHighlightWindow`** (`views/placement_highlight.py`): always-on-top Toplevel
  that draws a yellow solid outline + cell label over the game screen at the Gemini-returned
  cell location. Auto-dismisses after `placement_highlight_seconds` (default 8s). Cleared
  immediately on next F2 press.
- **`SetWindowRgn` transparency** (Windows): window region clipped to hollow frame
  (outer rect − inner rect) + label rect. Cell interior is outside the window region —
  game fully visible through it. No layered window tricks.
- **`WS_EX_TRANSPARENT`** (without `WS_EX_LAYERED`): click-through on outline strip.
- **Non-Windows fallback**: `wm_attributes("-alpha", 0.75)` semi-transparent window.
- **`placement_highlight_seconds`** setting added to `AppSettings` (default 8, range 2–30).
- `MainOverlay.show_placement_highlight()` and `clear_placement_highlight()` public API.
- `PlacementHighlightWindow.destroy()` called in `MainOverlay._on_close_click()`.
- AD-24 updated in `docs/architecture.md`.

### Fixed
- `WS_EX_LAYERED` + `SetLayeredWindowAttributes(LWA_COLORKEY)` approach discarded —
  GDI child windows (tkinter Canvas) do not composite correctly with DWM color keying
  on Windows 10/11, causing solid black full-screen overlay. `SetWindowRgn` used instead.

## [0.3.1] - 2026-08-24

### Added
- **Grid overlay** (`core/grid_overlay.py`): OpenCV-based coordinate grid drawn on placement
  screenshots before submission to Gemini. Columns A–Z (left→right), rows 1–N (top→bottom).
  Yellow labels with dark outline for readability. Configurable via `grid_cols` / `grid_rows`
  settings (defaults: 12×8).
- **Structured placement response** (`response_schema`): when grid is enabled, Gemini returns
  `{"cell": "D5", "advice": "## ..."}`. `_build_placement_schema()` constructs the
  `types.Schema`; `_parse_placement_response()` validates and falls back gracefully on
  malformed JSON.
- **`cell_to_screen_pixels()`** in `grid_overlay.py`: converts a validated cell reference to
  absolute screen pixel rect `(x, y, w, h)` using `get_monitor_rect()`. Ready for v0.3.2
  canvas rendering without changes.
- **`parse_cell_reference()`** in `grid_overlay.py`: validates raw cell strings from Gemini
  into `(col_idx, row_idx)` or `None`. Single-letter columns only (A–Z, v0.3.1).
- **`PlacementResult.cell_reference`** field added (`models/results.py`).
- **`grid_overlay_enabled`** setting added to `AppSettings` (default `True`). Also `grid_cols`
  (default 12) and `grid_rows` (default 8).
- **Grid overlay toggle** in Settings → General tab: `ttk.Checkbutton` persists to
  `settings.json`.
- **`GeminiBackend.complete_with_image()`** accepts optional `response_schema` parameter.
  When provided, sets `response_mime_type="application/json"` on the SDK config.
  `AiBackend` Protocol updated to match.
- **`_on_placement_result()`** on `AssistantViewModel`: separate placement callback that parses
  the structured response, logs the resolved pixel rect, and appends the cell reference to the
  displayed advice text. Non-grid path falls back to plain text display unchanged.
- AD-23 added to `docs/architecture.md` (grid overlay design + canvas deferral rationale).
- Timberborn `placement.txt` rewritten: instructs Gemini to use the grid, return JSON with
  `cell` + `advice` fields. Previous plain-text format retained as fallback when grid is off.

### Changed
- F4 debug save stores the **grid-annotated frame** when grid overlay is enabled, so saved
  PNGs show exactly what Gemini received.
- `trigger_placement()` logs grid state: `grid=on (12x8)` or `grid=off`.

## [0.3.0] - 2026-08-23

### Added
- **Inline placement strip** (`views/placement_strip.py`): F2 toggles a `PlacementInputStrip`
  bar inside the overlay body. `ttk.Combobox` (editable) with dropdown showing history +
  quick-prompts. Dismiss with ✕ or Escape, submit with Enter or Ask button.
  Auto-hides when overlay slides offscreen. Restores overlay if offscreen/collapsed when F2 pressed.
- **Prompt history**: last 5 placement queries persisted to `settings.json`, deduplicated
  (newest first). Loaded at startup, saved on every submit.
- **Quick-prompts**: `quick_prompts: list[str]` added to `GamePackManifest` and `manifest.yaml`.
  5 Timberborn-specific prompts. Shown in dropdown below history items.
- `get_prompt_suggestions()` on `AssistantViewModel`: merges history + quick-prompts, deduplicates.
- `save_prompt_history()` / `load_prompt_history()` added to `settings_manager.py`.
- **Game window focus check** in `trigger_advisor` only: hotkeys ignored when game not in foreground.
  Windows-only via `win32gui`. Fails open on non-Windows or missing pywin32. Does NOT block
  placement submit (user is deliberately interacting with GASSI overlay).
- **OCR elapse fix**: `elapse` from RapidOCR is a list — fixed `TypeError` by using `sum(elapse)`.
- **OCR confidence logging** promoted from DEBUG to INFO.

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
- **Model dropdown in Settings**: replaces text entry. Fetches live model list from
  Gemini API in background thread on dialog open. Shows ⟳ Fetching... status, updates
  to ✓ N models available or ⚠ fallback on error. Flash models sorted first (cheaper).
  Fallback list shown if API key missing or fetch fails.
- **Default model changed** to `gemini-2.0-flash` (1500 req/day free tier vs 20 on gemini-3.6-flash).
- **429 handling** in `GeminiBackend`: catches quota errors by string matching (no external
  dependency), parses `retryDelay`, surfaces readable message e.g. "API quota exceeded — retry in 19s".
- **AFC warning suppressed**: `AutomaticFunctionCallingConfig(disable=True)` passed on
  every call — GASSI never uses function calling tools.
- **OCR preprocessing pipeline** (`core/ocr/preprocessor.py`): upscale 3× (12px→36px),
  grayscale, Gaussian denoise, adaptive threshold, unsharp mask sharpening, white padding.
  Grounded in Timberborn HUD analysis: small white text, icon/progress-bar noise,
  dark gradient backgrounds.
- **Per-region preprocessing configs**: `DEFAULT_CONFIG`, `POPULATION_CONFIG` (larger
  adaptive block for green wellness bar background), `CYCLE_TIME_CONFIG` (lighter denoise
  for cleaner background). `LABEL_CONFIGS` registry lookups by region label.
- **`opencv-python-headless`** added to dependencies.
- F4 debug save now stores the **preprocessed crop** (binary thresholded) so you can
  visually verify what RapidOCR actually receives.
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
