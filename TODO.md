# TODO — GASSI Roadmap

Progress is tracked via checkboxes inline with each version.
Completed items stay in their version section — no separate completed list.

---

## v0.9.10 — Architecture milestone

Next planned milestone. Scope TBD.

---

## vFuture — Post-beta backlog

- [ ] Advisor result auto-copy to clipboard (settings toggle, default off)
- [ ] Response font size setting (accessibility)
- [ ] Overlay opacity quick-slider in toolbar
- [ ] placement_input_style: strip | dialog setting (default strip)
- [ ] TTS voice readout: edge-tts integration, toggle in Settings
- [ ] Windows installer (NSIS or MSI) — zip bundle sufficient for beta
- [ ] GPU detection at startup (nvidia-smi or GPUtil) — surface best local model
      recommendation. Deferred in favour of live Ollama /api/tags fetch (AD-29).
      Requires evaluation of GPUtil maintenance status and cross-vendor GPU support
      (AMD ROCm, Intel Arc) before implementing.
- [ ] HuggingFace local inference via transformers — blocked by AD-06 (no PyTorch).
      Requires a new AD allowing PyTorch as optional dep. Candidate trigger: Ollama
      proves insufficient for a target model family.
- [ ] Wayland capture backend — PipeWire / xdg-desktop-portal D-Bus API. Requires
      dbus-python + GStreamer Python bindings (large dep surface). mss via XWayland
      covers Proton/Steam games. Implement only if confirmed user demand.
- [ ] macOS native window detection — NativeWindowRegionProvider._find_window_macos()
      via NSWorkspace / CGWindowListCopyWindowInfo (pyobjc). Implement after macOS
      game testing confirms overlay anchoring is inadequate.
- [ ] SteamOS / Steam Deck — run test procedure in docs/platform_support.md and file
      issues for actual failures. No code changes until failures are identified.

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

## v0.9.7 ✅ — Platform support

- [x] NativeWindowRegionProvider: Windows FindWindow/EnumWindows + GetClientRect/ClientToScreen
      via ctypes; macOS stub (fails open to overlay rect); use_native_window_detection setting
      (opt-in, default False); Settings UI checkbutton; main.py factory wiring (AD-30)
- [x] MssCaptureBackend.grab(): catch mss.exception.ScreenShotError on macOS, re-raise as
      readable RuntimeError with Screen Recording permission instructions
- [x] docs/platform_support.md: support matrix, macOS permission guide, Steam Deck test
      procedure, Wayland known limitation + vFuture rationale

---

## v0.9.0 ✅ — Local SLM + extra cloud providers

Architecture: all OpenAI-compatible providers share OpenAiCompatBackend base class
and [providers] dep group (openai>=1.50). Gemini and Claude keep their native SDKs (AD-29).

- [x] AiProvider enum: OLLAMA, GROQ, TOGETHER, HUGGINGFACE; convenience class methods
- [x] AppSettings: ollama_model, groq_model, together_model, huggingface_model, ollama_base_url
- [x] OpenAiCompatBackend base class: text + vision paths, error handling, usage extraction
- [x] OllamaBackend: /v1 append, fetch_ollama_models() via stdlib urllib, VRAM annotations
- [x] GroqBackend, TogetherBackend, HuggingFaceBackend (Inference API cloud only — AD-06)
- [x] Settings UI: all six providers with tier labels, dynamic credential/model section,
      Ollama URL field, per-provider model persistence, VRAM hint
- [x] docs/local_models.md: hardware tiers, VRAM table, quality comparison, free-tier guide
- [x] README updated to v0.9.5: provider table, six keyring commands, project structure
- [x] AD-29 in architecture.md

---

## v0.8.2 ✅ — Anti-cheat posture

- [x] core/capture_affinity.py: SetWindowDisplayAffinity(WDA_EXCLUDEFROMCAPTURE) via ctypes
- [x] Applied to all overlay windows; lazily-built Toplevels apply on _build()
- [x] AppSettings.hide_from_capture: bool = True; Settings toggle applies immediately
- [x] anticheat_note from manifest → Settings read-only label
- [x] docs/adding_game_pack.md Section 8: risk table, WDA explanation
- [x] AD-28 in architecture.md

---

## v0.8.1 ✅ — Distribution (beta release)

- [x] API key entry in Settings: masked ttk.Entry, keyring read/write, Gemini + Claude
- [x] main.py: returns "" on missing key (no sys.exit); shows canvas message + auto-opens Settings
- [x] AppSettings: extra="ignore"; startup try/except fallback on corrupt settings.json
- [x] gassi.spec: PyInstaller --onedir, bundles game_packs/, hidden imports
- [x] core/paths.py: get_base_dir() — sys._MEIPASS in frozen mode
- [x] _get_version() fallback for PackageNotFoundError in frozen builds
- [x] RELEASE_NOTES.md, docs/build_release.md, end-user README section

---

## v0.8.0 ✅ — UX polish (pre-release)

- [x] FloatingAdviceWindow: centered semi-transparent Toplevel shown when overlay offscreen
      and F1 result arrives; auto-dismiss; themed; Settings toggle
- [x] FloatingPlacementDialog: centered Toplevel for F2 when overlay offscreen; keyboard
      focus; hides before on_submit so absent from placement screenshot
- [x] placement_input_style deferred to vFuture

---

## v0.7.0 ✅ — Multi-backend cloud AI

- [x] ClaudeBackend implementing AiBackend Protocol (anthropic SDK); optional [claude] dep
- [x] AiProvider enum, active_ai_provider in AppSettings, backend factory
- [x] Backend selector ttk.Combobox in Settings; model picker switches per provider
- [x] preferred_backend manifest hint: logged only, Settings always wins (AD-26)
- [x] AiBackend Protocol: both methods return tuple[str, UsageStats] (breaking, atomic)
- [x] UsageStats model, estimate_cost() rate table, session accumulators, token footer label
- [x] building_footprints dict in GamePackManifest; _lookup_footprint() keyword scan
- [x] cell_to_screen_pixels() extended with footprint param; multi-cell highlight label suffix
- [x] Timberborn: 13 footprint entries; Nebuchadnezzar: 11 footprint entries
- [x] AD-26, AD-27 in architecture.md

---

## v0.6.0 ✅ — RAG pipeline

- [x] RagService Protocol, ChromaRagService, NullRagService, RagServiceFactory (AD-25)
- [x] Optional [rag] dep group: chromadb>=0.6 only (no PyTorch — AD-06)
- [x] tools/ingest_knowledge.py: paragraph-split chunking, idempotent, --reset flag
- [x] Timberborn knowledge base: 6 markdown files, collection ingested
- [x] Nebuchadnezzar knowledge base: 6 markdown files, collection ingested
- [x] RAG injection on OCR advisor path; skipped on screenshot path (no text query)
- [x] game_version metadata as float; $gte filter in ChromaRagService.query()
- [x] docs: adding_game_pack.md Section 5 (RAG guide), architecture.md AD-25,
      v1_scope.md Feature 6, README.md

---

## v0.5.3–v0.5.18 ✅ — Calibration fixes + hotkey fixes + status messages

- [x] v0.5.3: CalibrationService auto-normalise 0–100 coords; CRITICAL prompt warning
- [x] v0.5.4: clamp coords to [0.0, 1.0] instead of rejecting
- [x] v0.5.5: scale detection via max(x,y,w,h) — handles mixed Gemini coord formats
- [x] v0.5.6: diagnostic logger.info reverted to logger.debug
- [x] v0.5.7: hotkey capture fix — printable chars not wrapped in <>; Alt detection; bare
      modifier presses no longer terminate capture; display label width 16→22
- [x] v0.5.8: advisor_ocr.txt (both games): NEVER ask for more data rule added
- [x] v0.5.9: HotkeyManager rejects modifier-only strings; _is_game_focused() logs title
- [x] v0.5.10: objectives_panel in hud_regions_user.yaml corrected to x=0.838
- [x] v0.5.11: placement prompts: IMPORTANT landmark note for windowed mode grid offset
- [x] v0.5.12: GamePackManifest.preferred_advisor_source field + ViewModel wiring
- [x] v0.5.13: PlacementHighlightWindow: GetAncestor(GA_ROOT) to resolve root HWND
- [x] v0.5.14: PlacementHighlightWindow: ctypes replaces pywin32 (no CreateRectRgn)
- [x] v0.5.15: SetWindowRgn via ctypes confirmed working
- [x] v0.5.16: cycle_time_panel manually added to hud_regions_user.yaml; calibration
      prompt: standard label list, min size requirement, px-coord warning
- [x] v0.5.17: _on_settings_saved restart notice only fires on hotkey changes; Settings
      tab foreground fix via theme_use("default")
- [x] v0.5.18: two-line progress status during AI calls on all three paths

---

## v0.5.2 ✅ — Atomic settings file writes

- [x] _write_atomic() in settings_manager.py — tmp+rename pattern
- [x] save_settings, save_window_geometry, save_prompt_history all use atomic write
- [x] Redundant read-modify-write round trip removed

---

## v0.5.1 ✅ — GamePackManifest forward compatibility

- [x] rag_top_k, rag_min_game_version, preferred_backend, window_class,
      anticheat_note — all optional, all None default

---

## v0.4.7 ✅ — Nebuchadnezzar live testing

- [x] CalibrationService: 3/3 regions accepted
- [x] objectives_panel region manually corrected to x=0.838
- [x] F1 advisor (screenshot + OCR modes) confirmed working
- [x] F2 placement + highlight box confirmed working
- [x] Hotkey fixes: Alt+8/9/0 bindings validated
- [x] preferred_advisor_source: screenshot set in manifest
- [x] Timberborn retested: calibration, F1, F2, highlight all working

---

## v0.4.6 ✅ — Docs: v1_scope.md update

- [x] Nebuchadnezzar added, all features updated, deferred items renumbered,
      known limitations updated

---

## v0.4.5 ✅ — Docs: adding_game_pack.md rewrite

- [x] game_id manifest requirement, bootstrap workflow, OCR tuning guide,
      placement prompt template, testing checklist, Settings UI activation

---

## v0.4.4 ✅ — Game switch restart notice

- [x] _on_settings_saved detects active_game_id change, shows restart notice
- [x] Startup log includes pack display name

---

## v0.4.3 ✅ — Settings dialog height fix

- [x] SettingsDialog._HEIGHT increased to accommodate game selector row
- [x] Calibration button no longer clips on standard resolutions

---

## v0.4.2 ✅ — Nebuchadnezzar OCR preprocessor configs

- [x] NEBU_RESOURCE_BAR_CONFIG: 4× upscale, block=11, C=6
- [x] NEBU_STATUS_BAR_CONFIG: 3× upscale, block=13, C=8
- [x] NEBU_OBJECTIVES_CONFIG: 2.5× upscale, no denoise
- [x] All three registered in LABEL_CONFIGS by region label

---

## v0.4.1 ✅ — Active game selector

- [x] Active game selector ttk.Combobox in Settings → General
- [x] GamePackLoader.list_available_packs(): scans game_packs/
- [x] MainOverlay.set_pack_loader() setter
- [x] active_game_id saved to settings.json
- [x] SettingsDialog accepts optional pack_loader param

---

## v0.4.0 ✅ — Second game pack (Nebuchadnezzar)

- [x] game_packs/nebuchadnezzar/ folder structure created
- [x] manifest.yaml: 3 HUD regions (resource_bar, status_bar, objectives)
- [x] prompts/advisor_ocr.txt: full domain knowledge
- [x] prompts/advisor_screenshot.txt: screenshot variant
- [x] prompts/placement.txt: grid overlay + JSON response
- [x] 5 quick_prompts added

---

## v0.3.2 ✅ — Placement bounding box

- [x] PlacementHighlightWindow — transparent tk.Toplevel, full monitor size
- [x] Yellow outline box + cell label at Gemini-returned cell position
- [x] SetWindowRgn hollow frame (Windows); -alpha 0.75 fallback (non-Windows)
- [x] WS_EX_TRANSPARENT click-through on outline
- [x] Auto-dismiss after placement_highlight_seconds (default 8s)
- [x] Cleared on next F2 press before capture
- [x] placement_highlight_seconds in AppSettings
- [x] AD-24 added to architecture.md

---

## v0.3.1 ✅ — Grid overlay (spatial placement v2)

- [x] Draw A–Z / 1–N grid on captured screenshot before sending to Gemini
- [x] Placement prompt: Gemini returns {"cell": "D5", "advice": "..."} JSON
- [x] Parse cell reference (response_schema + _parse_placement_response())
- [x] cell_to_screen_pixels() — pixel rect conversion
- [x] Grid overlay toggle in Settings → General tab
- [x] GeminiBackend.complete_with_image() accepts optional response_schema
- [x] AD-23 added to architecture.md

---

## v0.3.0 ✅ — Input improvements

- [x] Game window focus check: hotkeys ignored when game not in foreground
- [x] Inline placement input strip: F2 toggles PlacementInputStrip inside overlay body
- [x] Placement strip auto-hides/restores/expands with overlay state
- [x] Focus check moved to trigger_advisor only — placement submit not blocked
- [x] Prompt history: last 5 queries persisted, deduplicated, newest first
- [x] Quick-prompts: list in manifest, shown in dropdown after history
- [x] get_prompt_suggestions() on ViewModel: merges history + quick-prompts
- [x] save_prompt_history() / load_prompt_history() in settings_manager.py

---

## v0.2.0 ✅ — Calibration + OCR pipeline

- [x] CalibrationService: Gemini multimodal + response_schema + OCR validation
- [x] hud_regions_user.yaml override: per-game user calibration, never overwrites defaults
- [x] GamePackLoader: user calibration priority, manifest fallback, logs source at startup
- [x] CalibrationDialog: background thread, progress bar, ✓/✗ per-region results
- [x] "Calibrate HUD" button in Settings → General
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

---

## v0.1.3 ✅ — Debug tools + prompt polish

- [x] Window resizable: ◢ grip in bottom-right, drag to resize, min size enforced
- [x] Footer cooldown label: fixed width=12 reserved space, hints text shortened
- [x] _can_trigger: removed show_advice() call (stale cooldown text bug fixed)
- [x] "Ready" indicator: cooldown label flashes green ✓ Ready for 1.5s when cooldown expires
- [x] update_cooldown() accepts optional fg colour; delegates through OverlayCanvas
- [x] _ready_colour resolved from canvas theme at ViewModel init (theme-aware)
- [x] manifest.yaml: recalibrated regions measured from real gameplay screenshots at 1456×816
- [x] advisor_ocr.txt: updated region label documentation in prompt preamble
- [x] docs/adding_game_pack.md: complete new game tutorial
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

---

## v0.1.2 ✅ — Settings dialog

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

---

## v0.1.1 ✅ — UX shell

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

---

## v0.1.0 ✅ — Project scaffold

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
