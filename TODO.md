# TODO — GASSI Roadmap

---

## v0.3.0 — Input Improvements

Small UX improvements to the placement and advisor flow. Code-only, no gameplay needed.

- [ ] Inline text entry in the overlay body (replace popup dialog for F2)
- [ ] Prompt history: last 5 placement queries stored, selectable via dropdown
- [ ] Predefined quick-prompts per game pack defined in manifest.yaml
      (e.g. "Where to build next?", "Water strategy?", "Dam placement?")

---

## v0.3.1 — Grid Overlay (Spatial Placement v2)

Adds a coordinate grid to screenshots sent for placement advice, enabling
Gemini to return cell references that GASSI can render as bounding boxes.

- [ ] Draw A–Z / 1–N grid on captured screenshot before sending to Gemini
- [ ] Update placement prompt: instruct Gemini to return a cell reference (e.g. "D5")
      in a structured response field alongside the natural language advice
- [ ] Parse cell reference from response (response_schema JSON)
- [ ] Cell → screen pixel conversion using monitor_rect + grid dimensions
- [ ] Bounding box rendered on overlay canvas at target cell coordinates
- [ ] Grid overlay toggle: on/off setting in settings dialog

---

## v0.3.2 — Tutorial Overlays

Arrow and highlight system for guided in-game instructions.
Builds on the v2 canvas layers already scaffolded in OverlayCanvas.

- [ ] Arrow rendering: directional arrows pointing to game UI elements
- [ ] Highlight region rendering: dim background + lit bounding box
- [ ] Tutorial step system: sequence of steps, each with instruction text
- [ ] Tutorial sequences defined in game pack YAML (per-game)
- [ ] Step navigation: next/prev buttons in overlay footer

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
