# TODO — GASSI Roadmap

---

## v0.3.0 — Input Improvements ✅ Complete

Small UX improvements to the placement and advisor flow. Code-only, no gameplay needed.

### Completed
- [x] Game window focus check: hotkeys ignored when game not in foreground (Windows via pywin32,
      fails open on non-Windows or missing pywin32). Uses `window_title_pattern` from manifest.
- [x] Inline placement input strip: F2 now toggles a `PlacementInputStrip` bar inside the overlay
      body — no popup dialog. Combobox with dropdown showing history + quick-prompts.
- [x] Placement strip auto-hides when overlay slides offscreen
- [x] Placement strip restores overlay if offscreen when F2 pressed
- [x] Placement strip expands overlay if collapsed when F2 pressed
- [x] Focus check moved to `trigger_advisor` only — placement submit no longer blocked when
      GASSI overlay has focus (user typing in strip)
- [x] Prompt history: last 5 placement queries persisted to `settings.json`, deduplicated,
      newest first. Loaded at startup, updated on every placement query.
- [x] Quick-prompts: `quick_prompts` list added to `GamePackManifest` and `manifest.yaml`.
      5 Timberborn-specific prompts added. Shown in dropdown after history items.
- [x] `get_prompt_suggestions()` on ViewModel: merges history + quick-prompts, deduplicates.
- [x] `save_prompt_history()` / `load_prompt_history()` added to `settings_manager.py`.

### Remaining
- (all items complete)

---

## v0.3.1 — Grid Overlay (Spatial Placement v2) ✅ Complete

Adds a coordinate grid to screenshots sent for placement advice, enabling
Gemini to return cell references alongside advice text.

### Completed
- [x] Draw A–Z / 1–N grid on captured screenshot before sending to Gemini
      (`core/grid_overlay.py`, `draw_grid_on_frame()`)
- [x] Update placement prompt: Gemini returns `{"cell": "D5", "advice": "..."}` JSON
- [x] Parse cell reference from response (`response_schema` + `_parse_placement_response()`)
- [x] Cell → screen pixel conversion (`cell_to_screen_pixels()`) — logs rect, ready for v0.3.2
- [x] Grid overlay toggle in Settings → General tab (persisted to settings.json)
- [x] `GeminiBackend.complete_with_image()` accepts optional `response_schema`
- [x] AD-23 added to architecture.md
- [x] Bounding box rendered over target cell — implemented in v0.3.2 via `PlacementHighlightWindow`
      (yellow outline box, `SetWindowRgn`, auto-dismiss)

---

## v0.3.2 — Placement Bounding Box ✅ Complete

Transparent always-on-top cell highlight window over the game screen.

### Completed
- [x] `PlacementHighlightWindow` — separate transparent `tk.Toplevel`, full monitor size
- [x] Dashed yellow bounding box + cell label rendered at Gemini’s returned cell position
- [x] Windows `-transparentcolor`, macOS `-transparent`, Linux `-alpha` fallback
- [x] Click-through via `WS_EX_TRANSPARENT` on highlight HWND (separate from main overlay)
- [x] Auto-dismiss after `placement_highlight_seconds` (default 8s)
- [x] Cleared on next F2 press before capture
- [x] `placement_highlight_seconds` in `AppSettings`
- [x] AD-24 added to architecture.md

### Deferred to v0.3.3 or later
- [ ] Arrow rendering (directional arrows pointing to game UI elements)
- [ ] Dim-background highlight region (tutorial step overlay)
- [ ] Tutorial step system (sequence of steps with next/prev navigation)
- [ ] Tutorial sequences defined in game pack YAML

---

## v0.4.0 — Second Game Pack

Real-world validation that the game pack architecture generalizes.
Auto-calibration is the first step for any new game.

- [ ] Pick second game (RimWorld or Factorio — Factorio preferred for clean UI)
- [ ] Run CalibrationService on it: first real test outside Timberborn
- [ ] Write manifest.yaml + 3 prompts (advisor_ocr, advisor_screenshot, placement)
- [ ] Define early/mid/late stages for the new game (same process as Timberborn)
- [ ] Identify what's truly game-specific vs. reusable in prompt templates
- [ ] Extract common prompt structure into a reusable base template

---

## v0.4.1 — RAG Pipeline

Local knowledge retrieval to replace static game knowledge in system prompts.
Allows deeper, formula-level advice without bloating prompt token count.

- [ ] Chroma + sentence-transformers for game knowledge retrieval
- [ ] Wiki/formula ingestion pipeline: chunking, embedding, persistence to disk
- [ ] Pre-baked Chroma collections shipped per game pack folder
- [ ] RAG-augmented prompts: retrieved chunks injected into system prompt at query time
- [ ] patch_version metadata filtering in Chroma queries
- [ ] Fallback: if no RAG collection found, use static prompt as before

---

## v0.5.0 — Multi-Backend (Cloud)

Protocol-based AI backend swap. ClaudeBackend as the second implementation,
validates that AiBackend Protocol is truly backend-agnostic.

- [ ] ClaudeBackend implementing AiBackend Protocol (Anthropic SDK)
- [ ] Backend selector dropdown in Settings → General
- [ ] Cost tracking: token usage display per session in overlay footer
- [ ] Per-backend model list in settings dropdown (reuse fetch pattern from Gemini)

---

## v0.5.1 — Local SLM Support

Freemium tier: local model for users with capable GPUs, no API key required.

- [ ] OllamaBackend implementing AiBackend Protocol
- [ ] Qwen2.5-VL / Llama 3.2 Vision support via Ollama
- [ ] GPU detection at startup: suggest local model if capable GPU found
- [ ] Freemium framing: local SLM free, cloud API paid
- [ ] Quality comparison guide: local vs cloud advice quality per game

---

## v0.6.0 — Platform Support

Expand beyond Windows + X11. Native window detection replaces manual positioning.

- [ ] Wayland capture backend (PipeWire/portal)
- [ ] NativeWindowRegionProvider: per-OS window handle lookup (pywin32/pyobjc/Xlib)
      replaces manual overlay positioning for game window detection
- [ ] SteamOS / Steam Deck testing
- [ ] macOS Screen Recording permission: first-run prompt and guidance

---

## v0.6.1 — Anti-Cheat Posture

For games with anti-cheat. Pure overlay approach already avoids memory reading;
this adds capture hiding and documentation.

- [ ] SetWindowDisplayAffinity (Windows): hide overlay from other screen captures
- [ ] Adjustable window class/enumeration behavior
- [ ] Per-game anti-cheat compatibility notes in game pack manifest

---

## v0.6.2 — Distribution

Packaging and installer for end-users who don't have Python/uv.

- [ ] PyInstaller packaging: single-folder build, test on clean Windows VM
- [ ] Auto-updater mechanism
- [ ] Installer for Windows (NSIS or MSI)
- [ ] TTS voice readout: edge-tts integration, toggle in settings (optional)
- [ ] First-run wizard: API key entry, model selection, first calibration

---

## v0.7.0 — UX Polish (post-first-release)

Refinements to the interaction model after the core product is stable and released.
All items here are low architectural risk — UI-only changes on top of existing infrastructure.

### Floating Advice Window
- [ ] When overlay is slid offscreen and F1 (Advisor) fires, show advice in a
      separate centered `tk.Toplevel` instead of restoring the full overlay.
      Topmost, semi-transparent, auto-dismisses after N seconds or on click.
      Position: upper-center of screen (not covering game HUD).
- [ ] Toggle in settings: "Show advice in floating window when overlay is hidden"
- [ ] Floating window respects current theme and markdown rendering

### Floating Placement Dialog
- [ ] When overlay is slid offscreen and F2 fires, show a centered `tk.Toplevel`
      dialog (larger than the inline strip) with the combobox + history + quick-prompts.
      Full keyboard focus, Escape dismisses, Enter submits.
- [ ] Same `PlacementInputStrip` data (history, quick-prompts) reused — only the
      container widget changes. No ViewModel changes needed.
- [ ] Toggle in settings: `placement_input_style: strip | dialog`
      (strip = current inline bar; dialog = centered Toplevel)

### General UX
- [ ] Advisor result auto-copy to clipboard option (settings toggle)
- [ ] Response font size setting (accessibility)
- [ ] Overlay opacity slider in toolbar (quick access without opening settings)

---

## Ongoing / Cross-Cutting

- [ ] Unit tests for new features (maintain test coverage)
- [x] Update README.md and docs/architecture.md with each version
- [ ] Performance profiling (memory, CPU during capture + OCR)
- [ ] Gemini API cost monitoring and optimization
- [ ] AFC warning: evaluate migrating to AsyncChat.send_message (low priority)
- [ ] Free tier quota: document model alternatives in README
      (gemini-2.0-flash: 1500 req/day free; paid tier removes cap)

---

## Completed

### v0.3.2 (2026-08-24)
- [x] `PlacementHighlightWindow` — yellow outline box + label over game screen
- [x] `SetWindowRgn` clips window to hollow frame: game fully visible inside cell
- [x] `WS_EX_TRANSPARENT` (no `WS_EX_LAYERED`) for click-through on outline
- [x] Non-Windows `-alpha 0.75` fallback
- [x] Auto-dismiss timer + clear on next query
- [x] `placement_highlight_seconds` setting
- [x] AD-24 updated (WS_EX_LAYERED/LWA_COLORKEY failure documented)
- [x] Fixed: `-transparentcolor` approach caused solid black screen on Windows 10/11 DWM

### v0.3.1 (2026-08-24)
- [x] Grid overlay drawn on placement screenshots before Gemini submission
- [x] Structured JSON response (`response_schema`) for placement mode
- [x] `cell_to_screen_pixels()` — pixel rect conversion, logged, ready for v0.3.2 canvas
- [x] `parse_cell_reference()` — validates Gemini cell strings
- [x] `PlacementResult.cell_reference` field
- [x] `grid_overlay_enabled` setting + Settings dialog toggle
- [x] `GeminiBackend` and `AiBackend` Protocol updated for optional `response_schema`
- [x] Timberborn placement.txt rewritten for grid + JSON response format
- [x] AD-23 documenting canvas deferral decision

### v0.2.0 (2026-08-23)
- [x] CalibrationService: Gemini multimodal + response_schema + OCR validation
- [x] hud_regions_user.yaml override: per-game user calibration, never overwrites defaults
- [x] GamePackLoader: user calibration priority, manifest fallback, logs source at startup
- [x] CalibrationDialog: background thread, progress bar, ✓/✗ per-region results
- [x] "Calibrate HUD" button in Settings → General (only shown when service wired)
- [x] OCR preprocessor: upscale 3×, grayscale, adaptive threshold, sharpen, padding
- [x] Per-region preprocessing configs (DEFAULT, POPULATION, CYCLE_TIME)
- [x] opencv-python-headless added to dependencies
- [x] OCR region bug fixed: monitor rect used instead of overlay rect (was 0.00 confidence)
- [x] OCR flicker fixed: single withdraw/deiconify wraps all region captures
- [x] Model dropdown: live Gemini API fetch, flash-first, fallback list
- [x] Default model: gemini-2.0-flash (1500 req/day free tier)
- [x] 429 handling: readable message with retry delay, string-based detection
- [x] AFC warning suppressed on all calls
- [x] Logging: model + source + size on every API call
- [x] Version from importlib.metadata (pyproject.toml single source of truth)
- [x] get_monitor_rect() added to OverlayAnchoredRegionProvider
- [x] Timberborn prompts: full rewrite based on 6 real gameplay screenshots
      (Cycle 2–11), 3 real stages, floodgate/badwater/battery mechanics

### v0.1.3 (2026-08-23)
- [x] Window resizable: ◢ grip in bottom-right, drag to resize, min size enforced
- [x] Footer cooldown label: fixed width=12 reserved space, hints text shortened
- [x] _can_trigger: removed show_advice() call (stale cooldown text bug fixed)
- [x] "Ready" indicator: cooldown label flashes green ✓ Ready for 1.5s when cooldown expires
- [x] update_cooldown() accepts optional fg colour; delegates through OverlayCanvas
- [x] _ready_colour resolved from canvas theme at ViewModel init (theme-aware)
- [x] manifest.yaml: recalibrated regions (resource_bar, population_panel, cycle_and_time)
      measured from real gameplay screenshots at 1456×816
- [x] advisor_ocr.txt: updated region label documentation in prompt preamble
- [x] docs/adding_game_pack.md: complete new game tutorial (calibration, prompts, stage design)
- [x] README.md rewritten to v0.1.3: full hotkey table, all features, project structure
- [x] Debug frame save: F4 hotkey saves last captured frame as timestamped PNG
- [x] DebugManager: frame storage, disk save, auto-prune (50 frames), debug dir
- [x] OverlayLogHandler: in-memory logging.Handler feeding log panel
- [x] LogPanel: collapsible scrollable log viewer, per-level colour, CLR button
- [x] Log panel toggle (⌨) in toolbar
- [x] hotkey_debug_save_frame added to AppSettings (default F4)
- [x] debug_log_max_lines added to AppSettings (default 200)
- [x] Advisor prompts rewritten: ~40% fewer tokens, no duplicate knowledge block
- [x] Early-game context recognition clause (Day 1–15) in both advisor prompts
- [x] Markdown rendering expanded: ## headings, - bullets, **bold** rendered natively
- [x] Prompts updated to use markdown structure for readability
- [x] Prompt iteration CLI: tests/prompt_iteration.py

### v0.1.2 (2026-08-23)
- [x] Settings dialog with two tabs (Hotkeys, General)
- [x] Configurable hotkeys via key-capture widget
- [x] Theme picker dropdown (dark/midnight/forest)
- [x] Cooldown interval slider (5–60 seconds)
- [x] AI model selector text field
- [x] Default advisor input source selector (ocr/screenshot)
- [x] Gear icon (⚙) in toolbar opens settings
- [x] Persistent settings: JSON config file in OS app data directory
- [x] Window position/size remembered across sessions
- [x] Settings loaded at startup, merged with defaults

### v0.1.1 (2026-08-22)
- [x] Theme system extracted (Theme model + 3 presets)
- [x] Collapsible overlay (▲/▼ toggle)
- [x] Slide-off-screen (◀ hide + ▶ pull-tab)
- [x] Custom frameless window (no native titlebar)
- [x] Compact toolbar with icon buttons
- [x] Markdown bold rendering in responses
- [x] Auto-hide overlay during capture
- [x] Full-screen capture for F2 placement and F1 screenshot fallback
- [x] Single-shot query model (no auto-polling)
- [x] Combined HUD regions into single API call
- [x] Cooldown timer with visible countdown
- [x] Footer hotkey hints in accent color
- [x] F3 lock hotkey
- [x] Themed placement dialog
- [x] Migrated Poetry → uv
- [x] Fixed rate limiting (36 req/min → 4 req/min)
- [x] Fixed overlay self-capture in screenshots
- [x] Fixed slide-off-screen reliability (withdraw/deiconify)

### v0.1.0 (2026-08-22)
- [x] MVVM project scaffold with Protocol abstractions
- [x] Advisor mode (OCR + Screenshot sources)
- [x] Placement mode (free-text spatial advice)
- [x] Gemini backend (google-genai SDK)
- [x] mss screen capture
- [x] Overlay-anchored region provider
- [x] Layered OverlayCanvas (v2 layers scaffolded)
- [x] Async-to-tkinter bridge
- [x] pynput global hotkeys
- [x] Per-OS click-through (Windows/macOS/Linux)
- [x] Game pack system (folder + manifest.yaml + prompts)
- [x] Timberborn pack (v0.6)
- [x] OS keyring API key storage
- [x] pydantic-settings config
- [x] OCR confidence fallback
- [x] API error backoff

---
