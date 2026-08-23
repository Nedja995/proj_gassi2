# TODO — GASSI Roadmap

## v0.1.3 — Debugging & Prompt Polish ✅ Complete (pending prompt iteration gameplay session)

### Debug Tools ✅ Done
- [x] Debug capture viewer: hotkey (F4) saves last captured frame as PNG to disk
- [x] Show what was sent to Gemini (frame stored per capture source, saved on F4)
- [x] Log viewer panel in overlay (collapsible ⌨ button, shows last N log lines)

### Prompt Quality ✅ Done
- [x] Tighten advisor prompts: max 4 lines output, RULES clause
- [x] Removed duplicate GAME KNOWLEDGE block (was identical in both advisor prompts)
- [x] Add early-game context recognition (Day 1–15 = beginner focus) in both advisor prompts
- [x] Prompt iteration tool: `tests/prompt_iteration.py` CLI for testing against saved screenshots
- [x] Markdown rendering expanded: ## headings, - bullets, **bold** rendered natively in OverlayCanvas
- [x] Prompts use markdown structure (heading + bullets + bold) for readability

### Prompt Iteration (requires gameplay session — not a code task) ⏸ SKIPPED
- [ ] Play Timberborn to early/mid/late game states, save frames with F4
- [ ] Run prompt_iteration.py against each saved frame (all 3 modes)
- [ ] Check: ## heading matches situation, bullets are actionable, early-game clause fires on Day 1–10
- [ ] Check: placement references actual visible landmarks, not generic directions
- [ ] Edit prompts on failures, re-run immediately (tool reads from disk, no restart)
- [ ] Sign off when all 3 modes produce consistent, correct output across game stages

### Window Behavior ✅ Done
- [x] "Ready" indicator in green after cooldown expires (before clearing)
- [x] Window resizable: ◢ grip in bottom-right, drag to resize, min size enforced

### HUD Calibration ✅ Done (manual, from screenshots)
- [x] manifest.yaml updated: resource_bar, population_panel, cycle_and_time regions
- [x] Regions measured from 1456×816 gameplay screenshots
- [x] advisor_ocr.txt updated to document region labels and their contents

---

## v0.2.0 — OCR & Auto-Calibration

**Goal:** make OCR advisor actually reliable. Auto-calibration is the prerequisite —
without correct regions, OCR accuracy is undefined. Build calibration first, then tune OCR.

### Auto-Calibration ✅ Done
- [x] `CalibrationService`: one-shot Gemini call with `response_schema` for deterministic JSON
- [x] Validation: OCR run on each returned region, reject if confidence < threshold or geometry invalid
- [x] Persist accepted regions to `game_packs/<id>/hud_regions_user.yaml`
- [x] `GamePackLoader`: checks `hud_regions_user.yaml` first, falls back to manifest.yaml defaults
- [x] `CalibrationDialog`: progress indicator, per-region accept/reject results with confidence scores
- [x] "Calibrate HUD" button in Settings → General tab (only shown when service is wired)
- [x] "Clear User Calibration" button in dialog reverts to manifest.yaml defaults
- [x] AD-22 added to architecture.md

### OCR Pipeline (after calibration)
- [ ] OCR preprocessing: contrast boost, binarization, upscaling crops before OCR
- [ ] Per-game font tuning profiles in game pack manifest
- [ ] Test RapidOCR against Timberborn's actual font with preprocessed images
- [ ] Fallback chain: OCR → screenshot only when OCR actually fails for the region
- [ ] docs/adding_game_pack.md: update calibration section to describe auto-calibration workflow

### Input Improvements
- [ ] Inline text entry in the overlay body (replace popup dialog for F2)
- [ ] Prompt history (last 5 placement queries, selectable)
- [ ] Predefined quick-prompts per game pack (e.g. "Where to build next?", "Water strategy?")

---

## v0.3.0 — Spatial & Visual Feedback

### Grid Overlay (v2 placement)
- [ ] Draw A-Z / 1-N grid on captured screenshot before sending to Gemini
- [ ] Parse Gemini's cell references (e.g. "D5") from structured response
- [ ] Cell → screen pixel conversion using capture_rect + scale_factor
- [ ] Bounding box rendering on overlay at target coordinates

### Tutorial Overlays
- [ ] Arrow rendering: directional arrows pointing to game UI elements
- [ ] Tutorial step system: "click here" highlights with instruction text
- [ ] Tutorial sequences defined in game pack YAML (per-game tutorials)
- [ ] Dim background + highlighted region for focused guidance

---

## v0.4.0 — Multi-Game & RAG

### Second Game Pack
- [ ] Pick second game (RimWorld or Factorio)
- [ ] Run auto-calibration on it as first real-world test of CalibrationService
- [ ] Validate pack structure generalizes (manifest, prompts, HUD regions)
- [ ] Identify what's truly game-specific vs. core engine
- [ ] Extract common prompt patterns into reusable templates

### RAG Pipeline
- [ ] Chroma + sentence-transformers for game knowledge retrieval
- [ ] Wiki/formula ingestion pipeline (chunking, embedding, persistence)
- [ ] Pre-baked Chroma collections shipped per game pack
- [ ] RAG-augmented prompts replacing static system prompt knowledge
- [ ] patch_version metadata filtering in Chroma queries

---

## v0.5.0 — Multi-Backend & Local Models

### AI Backend Expansion
- [ ] Claude API backend (ClaudeBackend implementing AiBackend Protocol)
- [ ] Backend selector in settings UI
- [ ] Cost tracking / token usage display per session

### Local SLM Support
- [ ] Ollama backend (OllamaBackend implementing AiBackend Protocol)
- [ ] Qwen2.5-VL / Llama 3.2 Vision support
- [ ] Freemium model: local SLM free, cloud paid
- [ ] GPU detection and model recommendation

---

## v0.6.0 — Platform & Distribution

### Platform Support
- [ ] Wayland capture backend (PipeWire/portal)
- [ ] Native window detection: per-OS window handle lookup (NativeWindowRegionProvider)
- [ ] SteamOS / Steam Deck testing
- [ ] macOS Screen Recording permission first-run prompt

### Anti-Cheat Posture
- [ ] SetWindowDisplayAffinity (Windows — hide overlay from screen captures)
- [ ] Document per-game anti-cheat compatibility

### Distribution
- [ ] PyInstaller packaging and testing
- [ ] Auto-updater mechanism
- [ ] Installer for Windows (MSI or NSIS)
- [ ] TTS voice readout (edge-tts integration, optional)

---

## Ongoing / Cross-Cutting

- [ ] Unit tests for new features (maintain test coverage)
- [x] Update README.md and docs/architecture.md with each version
- [ ] Performance profiling (memory, CPU during capture + OCR)
- [ ] Gemini API cost monitoring and optimization

---

## Completed

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
