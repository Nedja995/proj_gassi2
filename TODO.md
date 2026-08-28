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
- [x] Dashed yellow bounding box + cell label rendered at Gemini's returned cell position
- [x] Windows `-transparentcolor`, macOS `-transparent`, Linux `-alpha` fallback
- [x] Click-through via `WS_EX_TRANSPARENT` on highlight HWND (separate from main overlay)
- [x] Auto-dismiss after `placement_highlight_seconds` (default 8s)
- [x] Cleared on next F2 press before capture
- [x] `placement_highlight_seconds` in `AppSettings`
- [x] AD-24 added to architecture.md

---

## v0.4.0 — Second Game Pack (Nebuchadnezzar) ✅ Complete

Real-world validation that the game pack architecture generalizes.

### Completed
- [x] Game selected: Nebuchadnezzar (isometric city-builder, ancient Mesopotamia)
- [x] `game_packs/nebuchadnezzar/` folder structure created
- [x] `manifest.yaml`: 3 HUD regions estimated from reference screenshots
      (`resource_bar`, `status_bar`, `objectives`) — needs calibration on real resolution
- [x] `prompts/advisor_ocr.txt`: full domain knowledge (resources, housing evolution,
      bazaar system, wells, labor pool, approval, prestige, 3 game stages)
- [x] `prompts/advisor_screenshot.txt`: screenshot variant with spatial context
- [x] `prompts/placement.txt`: grid overlay + JSON response, Nebuchadnezzar spatial rules
- [x] 5 quick_prompts added to manifest

---

## v0.4.1 — Active Game Selector ✅ Complete

- [x] Active game selector in Settings → General: `ttk.Combobox` listing all installed packs
- [x] `GamePackLoader.list_available_packs()`: scans `game_packs/`, returns `(game_id, display_name)` list
- [x] `MainOverlay.set_pack_loader()` setter — same pattern as `set_calibration_service()`
- [x] `active_game_id` saved to `settings.json` on Settings save
- [x] `SettingsDialog` accepts optional `pack_loader` param (graceful fallback if absent)
- [x] `main.py` wired: `overlay.set_pack_loader(pack_loader)`

---

## v0.4.2 — Nebuchadnezzar OCR Preprocessor Configs ✅ Complete

- [x] `NEBU_RESOURCE_BAR_CONFIG`: 4× upscale, block=11, C=6 — small digits on dark icon strip
- [x] `NEBU_STATUS_BAR_CONFIG`: 3× upscale, block=13, C=8 — medium text on dark band
- [x] `NEBU_OBJECTIVES_CONFIG`: 2.5× upscale, no denoise — clean text on solid dark panel
- [x] All three registered in `LABEL_CONFIGS` by region label — auto-applied at runtime

---

## v0.4.3 — Settings Dialog Height Fix ✅ Complete

- [x] `SettingsDialog._HEIGHT` increased to accommodate game selector row
- [x] Calibration button no longer clips on standard resolutions

---

## v0.4.4 — Game Switch Restart Notice ✅ Complete

- [x] `_on_settings_saved` in `main.py` detects `active_game_id` change and logs clear
      "restart required to switch game" message
- [x] Overlay title bar updated to show active game name on startup

---

## v0.4.5 — Docs: adding_game_pack.md rewrite ✅ Complete

- [x] Section 1: `game_id` manifest requirement for Settings dropdown documented
- [x] Section 2: bootstrap-from-screenshots workflow + CalibrationService as primary path
- [x] Section 3 (new): OCR preprocessor config guide with tuning table by HUD type
- [x] Section 4: placement prompt template updated for grid overlay JSON format
- [x] Section 6: testing checklist updated (dropdown, calibration, highlight box)
- [x] Section 7: Settings UI activation documented; env var override noted

---

## v0.4.6 — Docs: v1_scope.md update ✅ Complete

- [x] Nebuchadnezzar added as second target game
- [x] All features updated to reflect shipped state (grid overlay, cell highlight,
      settings, calibration, debug tools, placement strip)
- [x] Deferred items renumbered to match current roadmap (v0.6.0–v0.9.0)
- [x] Known limitations updated (game switch restart, macOS fallback, Nebu OCR note)

---

## v0.4.7 — Nebuchadnezzar Testing ✅ Complete

**Known limitation:** Nebuchadnezzar has no Borderless Windowed mode.
Test in Windowed mode — GASSI overlay works correctly, taskbar visible at bottom.
Fullscreen exclusive mode bypasses DWM (Windows limitation, not a bug).

**Building footprint note:** Cell highlight shows single grid cell (placement anchor).
Multi-tile buildings extend beyond it. Full footprint rendering tracked in v0.7.0.

### Completed
- [x] Open Settings → General → select Nebuchadnezzar from Active game dropdown
- [x] Save settings and restart GASSI
- [x] CalibrationService: 3/3 regions accepted
- [x] `objectives_panel` region manually corrected to x=0.838
- [x] F1 advisor (Screenshot mode) — good advice quality confirmed
- [x] F1 advisor (OCR mode) — tested, works with corrected region
- [x] F2 placement — confirmed working, hollow yellow outline correct
- [x] Yellow highlight box renders correctly via SetWindowRgn (ctypes)
- [x] Hotkey fixes: Alt+8/9/0 bindings work correctly after rebind
- [x] `preferred_advisor_source: screenshot` set in manifest
- [x] Quick prompts refined for better spatial advice quality
- [x] Timberborn tested: calibration, F1, F2, highlight all working

---

## v0.5.1 — GamePackManifest Forward Compatibility ✅ Complete

- [x] `rag_top_k: int | None` — per-game RAG chunk count override
- [x] `rag_min_game_version: str | None` — RAG chunk version filtering
- [x] `preferred_backend: str | None` — pack-level AI backend preference
- [x] `window_class: str | None` — OS window class for native detection
- [x] `anticheat_note: str | None` — informational anti-cheat note
- [x] All fields optional/None — existing packs unaffected

---

## v0.5.2 — Atomic Settings File Writes ✅ Complete

- [x] `_write_atomic()` in `settings_manager.py` — write to `.tmp` then rename
- [x] `save_settings`, `save_window_geometry`, `save_prompt_history` all use atomic write
- [x] Eliminates corrupted `settings.json` on mid-write process kill
- [x] `save_window_geometry` / `save_prompt_history` no longer call `save_settings`
      internally — removes redundant read-modify-write round trip

---

## v0.6.0 — RAG Pipeline (milestone) ✅ Complete

Local knowledge retrieval to augment static game knowledge in system prompts.
Delivered across v0.6.1–v0.6.7. All sub-versions complete.

---

## v0.6.1 — RagService: Protocol + Chroma Backend ✅ Complete

- [x] `RagService` Protocol (`core/rag/protocol.py`): `query(text, top_k, min_game_version)`,
      `is_available()` — `@runtime_checkable`, structural subtyping
- [x] `ChromaRagService` (`core/rag/chroma_backend.py`): loads persistent Chroma collection
      from `game_packs/<id>/rag/`, deferred chromadb import, `ONNXMiniLM_L6_V2` embedder
      (no PyTorch), graceful degradation on load/query error
- [x] `NullRagService` (`core/rag/null_backend.py`): no-op, zero extra imports,
      `is_available()` returns `False`
- [x] `RagServiceFactory.for_game_pack()` (`core/rag/factory.py`): `ChromaRagService`
      when prerequisites met, else `NullRagService`
- [x] Optional dep group `[rag]` in `pyproject.toml`: `chromadb>=0.6` only —
      `sentence-transformers` dropped (pulled PyTorch ~2GB, violates AD-06);
      `ONNXMiniLM_L6_V2` uses `onnxruntime` already present via `rapidocr-onnxruntime`
- [x] AD-25 added to `docs/architecture.md`

---

## v0.6.2 — Ingestion CLI ✅ Complete

- [x] `tools/ingest_knowledge.py`: `--game-id`, `--source-dir` required;
      `--game-version`, `--model`, `--chunk-size`, `--chunk-overlap`,
      `--reset`, `--game-packs-root` optional
- [x] Reads `.md` / `.txt` recursively from `--source-dir`
- [x] Paragraph-split chunking; sentence sub-split for oversized paragraphs;
      configurable size (default 400 tokens) and overlap (default 50 tokens)
- [x] Metadata per chunk: `source_file`, `chunk_index`, `game_version`
- [x] Idempotent: skips already-ingested `source_file` values; `--reset` rebuilds
- [x] Output: `game_packs/<game_id>/rag/`, collection `<game_id>_knowledge`
- [x] `game_packs/` root auto-detected from script location
- [x] Uses `ONNXMiniLM_L6_V2` (no PyTorch) consistent with `ChromaRagService`

---

## v0.6.3 — Timberborn Knowledge Base ✅ Complete

- [x] `game_packs/timberborn/knowledge/01_resources.md` — logs/planks/food/water/science/metal
- [x] `game_packs/timberborn/knowledge/02_water_management.md` — drought cycle, dams vs
      floodgates, tanks, badwater, irrigation; reserve formula (500–800 units/10 beavers/day)
- [x] `game_packs/timberborn/knowledge/03_power_system.md` — windmills, water wheels,
      batteries (3,600 units capacity), shaft distribution
- [x] `game_packs/timberborn/knowledge/04_forestry_farming_costs.md` — tree growth rates,
      crop calorie densities, building cost table (20 buildings)
- [x] `game_packs/timberborn/knowledge/05_districts_labour.md` — districts, labour ratios,
      builder %, worker priority, expansion timing signals
- [x] `game_packs/timberborn/knowledge/06_v06_patch_meta.md` — v0.6 changes, terrain meta,
      common failure modes, useful ratios table
- [x] `manifest.yaml`: `rag_collection_name: timberborn_knowledge`, `rag_top_k: 4`,
      `rag_min_game_version: "0.6"`
- [x] Collection ingested (`uv run python tools/ingest_knowledge.py --game-id timberborn
      --source-dir game_packs/timberborn/knowledge --game-version 0.6 --reset`)
- [x] `game_packs/timberborn/rag/` committed to repo after ingestion

---

## v0.6.4 — RAG Injection into Advisor ✅ Complete

- [x] `AssistantViewModel.__init__` accepts optional `rag_service: RagService`
      (defaults to `NullRagService` — backward-compatible)
- [x] `_build_rag_context(query_text) -> str`: queries service, formats chunks as
      `## Retrieved Knowledge\n- chunk...`, returns `""` when unavailable
- [x] OCR advisor path: OCR text used as RAG query; context prepended to system prompt;
      logs `rag=on (N chunks)` or `rag=off (no chunks returned)`
- [x] Screenshot advisor path: RAG skipped; logs
      `rag=off (screenshot mode — no text query available)` when collection present
- [x] `main.py`: `RagServiceFactory.for_game_pack()` at startup, result passed to ViewModel
- [x] Startup log includes `rag: on/off` status
- [x] `rag_top_k` from manifest honoured; fallback default `top_k=3`

---

## v0.6.5 — Game Version Metadata Filtering ✅ Complete

- [x] `ChromaRagService.query()` accepts `min_game_version: str | None` —
      applies `{"game_version": {"$gte": min_game_version}}` Chroma `where` filter
- [x] `RagService` Protocol: `query(text, top_k, min_game_version=None)` — already
      present from v0.6.1
- [x] `NullRagService.query()` signature matches (no-op)
- [x] `_build_rag_context()` passes `self._manifest.rag_min_game_version` through
      to `query()` — implemented as part of v0.6.4
- [x] No additional code required — full pipeline already wired

---

## v0.6.6 — Nebuchadnezzar Knowledge Base ✅ Complete

- [x] `game_packs/nebuchadnezzar/knowledge/01_resources.md` — food, materials,
      luxury goods, workers, bronze tools
- [x] `game_packs/nebuchadnezzar/knowledge/02_housing_evolution.md` — tier chain,
      evolution checklist, coverage radii, devolution warning
- [x] `game_packs/nebuchadnezzar/knowledge/03_bazaar_distribution.md` — walker
      mechanics, placement rules, storehouse positioning, failure signs
- [x] `game_packs/nebuchadnezzar/knowledge/04_approval_prestige_objectives.md` —
      approval causes/fixes, prestige sources and values, objective tracking
- [x] `game_packs/nebuchadnezzar/knowledge/05_building_costs_production.md` —
      cost table (18 buildings), all production chains, labor requirements
- [x] `game_packs/nebuchadnezzar/knowledge/06_stages_meta_strategy.md` — 3-stage
      guide, failure modes, useful ratios
- [x] `manifest.yaml`: `rag_collection_name: nebuchadnezzar_knowledge`,
      `rag_top_k: 4`, `rag_min_game_version: "1.0"`
- [x] Collection ingested (`uv run python tools/ingest_knowledge.py --game-id
      nebuchadnezzar --source-dir game_packs/nebuchadnezzar/knowledge
      --game-version 1.0 --reset`)
- [x] `game_packs/nebuchadnezzar/rag/` committed to repo after ingestion

---

## v0.6.7 — Docs: RAG Pipeline ✅ Complete

- [x] `docs/adding_game_pack.md`: Section 5 added — full RAG guide (folder structure,
      chunk authoring tips, ingestion CLI reference table, manifest fields, embedding
      model note, REPL retrieval test, `.gitignore` note); Section 7 checklist
      extended with 5 RAG items
- [x] `docs/architecture.md`: AD-25 updated with `ONNXMiniLM_L6_V2` decision,
      `sentence-transformers` rejection rationale, injection point (OCR path only)
- [x] `docs/v1_scope.md`: Feature 6 RAG added (architecture, game packs, injection
      behaviour, dep group)
- [x] `README.md`: RAG in Features section, installation `[rag]` dep group,
      project structure updated with `core/rag/`, `knowledge/`, `rag/`

---

## v0.7.0 — Multi-Backend (Cloud) ✅ Complete

Protocol-based AI backend swap. ClaudeBackend as the second implementation,
validates that AiBackend Protocol is truly backend-agnostic.
Delivered across v0.7.1–v0.7.4.

---

## v0.7.1 — ClaudeBackend ✅ Complete

- [x] `core/ai/claude_backend.py`: `ClaudeBackend` implementing `AiBackend` Protocol
      (Anthropic SDK `anthropic>=0.40`)
- [x] `complete_text()` and `complete_with_image()` matching exact Protocol signatures
- [x] Structured output via JSON mode (system prompt instruction) — Claude has no native
      schema object; falls back to same `_parse_placement_response()` JSON parsing
- [x] 429 / rate-limit error handling with readable message (same pattern as `GeminiBackend`)
- [x] `fetch_available_claude_models()` — returns static list (no Anthropic listing endpoint)
- [x] Optional dep group `[claude]`: `anthropic>=0.40` only, not installed by default
- [x] Deferred import pattern — safe to import module without extras installed
- [x] No UI wiring yet — backend instantiated only if `[claude]` extras present
- [x] AD-26 in `docs/architecture.md`

---

## v0.7.2 — Backend Selector UI + Wiring ✅ Complete

- [x] `AiProvider` enum added to `models/enums.py`: `GEMINI`, `CLAUDE`
- [x] `active_ai_provider: AiProvider` field added to `AppSettings` (default `GEMINI`)
- [x] `claude_model: str` field added to `AppSettings` (default `claude-sonnet-4-6`)
- [x] Backend factory in `core/ai/factory.py`: `build_ai_backend()`, `get_api_key()`,
      `is_claude_available()`
- [x] Backend selector `ttk.Combobox` in Settings → General
- [x] Model dropdown content switches based on selected provider:
      Gemini fetches live, Claude shows static list
- [x] `preferred_backend` manifest field: logged at startup as informational hint only;
      Settings always wins — pack field does not override user selection
- [x] Claude option hidden from dropdown if `[claude]` extras not installed;
      startup log explains why
- [x] `main.py` wiring: backend constructed via factory at startup
- [x] `MainOverlay.set_claude_api_key()` setter; `_open_settings()` passes it through
- [x] Provider change detected in `_on_settings_saved`: shows restart notice
- [x] CalibrationService always uses Gemini key regardless of active provider

---

## v0.7.3 — Token Usage / Cost Tracking ✅ Complete

- [x] `UsageStats` Pydantic model (`models/results.py`):
      `input_tokens: int`, `output_tokens: int`, `estimated_cost_usd: float | None`
- [x] `estimate_cost()` helper with hardcoded rate table (Gemini + Claude tiers)
- [x] `AiBackend` Protocol updated: both methods return `tuple[str, UsageStats]`
      instead of bare `str` — both backends updated atomically in this sub-version
- [x] `GeminiBackend`: extracts `usage_metadata.prompt_token_count` /
      `candidates_token_count` from response, populates `UsageStats`
- [x] `ClaudeBackend`: extracts `response.usage.input_tokens` /
      `output_tokens`, populates `UsageStats`
- [x] Session accumulator in ViewModel: `_session_input_tokens`,
      `_session_output_tokens`, `_session_cost_usd`
- [x] `_accumulate_usage()` helper: accumulates + calls `overlay.update_token_display()`
- [x] `MainOverlay.update_token_display()` setter; `_token_label` in footer
      (hidden until first call; format: `↑1.2k ↓0.8k ~$0.0012`)
- [x] Per-call stats logged at DEBUG level

---

## v0.7.4 — Building Footprint Registry + Multi-cell Highlight ✅ Complete

- [x] `building_footprints: dict[str, list[int]]` field added to `GamePackManifest`
      (optional, default `{}`)
- [x] `cell_to_screen_pixels()` extended with optional `footprint: tuple[int, int]`;
      rect spans `fp_w × fp_h` cells; footprint clamped to grid bounds
- [x] `PlacementHighlightWindow.show()` accepts optional `footprint` param;
      label suffix added e.g. `D5 (4×4)` when footprint ≠ (1, 1)
- [x] `MainOverlay.show_placement_highlight()` passes `footprint` through
- [x] `_lookup_footprint()` module-level helper: case-insensitive keyword scan
      of advice text vs manifest keys; longest match wins; no AI call
- [x] ViewModel `_on_placement_result`: calls `_lookup_footprint()`, passes result
      to `cell_to_screen_pixels()` and `show_placement_highlight()`
- [x] Timberborn manifest: 13 building footprint entries
- [x] Nebuchadnezzar manifest: 11 building footprint entries (replaces v0.6.0 comment)
- [x] AD-27 in `docs/architecture.md`

---

## v0.8.0 — UX Polish (pre-release)

Interaction improvements that make GASSI usable when the overlay is offscreen.
Required before beta distribution — these are the biggest daily-use pain points.

### v0.8.0.1 — Floating Advice Window ✅ Complete

- [x] `views/floating_advice_window.py`: `FloatingAdviceWindow` — semi-transparent centered
      `tk.Toplevel`, themed, reuses same markdown tag rendering as `OverlayCanvas`
- [x] Position: upper-center of primary monitor (`_WIN_Y_FRACTION = 0.08`),
      35% screen width × 28% screen height, min 340×180px
- [x] Header bar with title + ✕ close button; footer hint; click background to dismiss
- [x] Auto-dismiss after `floating_advice_timeout_seconds` (default 12s)
- [x] `show_floating_advice_when_hidden: bool = True` in `AppSettings`
- [x] `floating_advice_timeout_seconds: int = 12` in `AppSettings`
- [x] `MainOverlay.show_floating_advice(advice_text, timeout_seconds)` public method
- [x] `MainOverlay._floating_advice` created at init; destroyed on `_on_close_click`
- [x] ViewModel `_on_result`: checks `_offscreen` + setting — routes to floating window
      or inline canvas (current behaviour) accordingly
- [x] Settings dialog: "Floating advice" toggle checkbutton in General tab
- [x] `SettingsDialog._HEIGHT` increased to 540px

### v0.8.0.2 — Floating Placement Dialog ✅ Complete

- [x] When overlay is offscreen and F2 fires, show a centered `tk.Toplevel` dialog
      (larger than the inline strip) with combobox + history + quick-prompts.
- [x] Full keyboard focus, Escape dismisses, Enter submits.
- [x] Reuses same history + quick-prompts data as `PlacementInputStrip` — no ViewModel changes.
- [x] Dialog hides itself before `on_submit` so it is absent from the placement screenshot.
- [x] `placement_input_style` setting deferred to vFuture UX backlog (not needed for current behaviour).

### v0.8.0.3 — General UX

All items moved to `vFuture — Additional UX (post-beta backlog)`.
Nothing remaining — this sub-version is retired.

---

## v0.8.1 — Distribution (beta release target)

Packaging for end-users who don't have Python/uv installed.
This is the milestone that makes GASSI publicly releasable as a zip bundle.

**Scope decisions (2026-08-28):**
- No first-run wizard — on missing API key, show overlay canvas message + auto-open Settings
- API keys entered via Settings dialog (masked `ttk.Entry`, saved to OS keyring) — no terminal needed
- zip bundle only for beta — NSIS/MSI installer deferred to vFuture
- Testing on dev machine only for beta (no clean VM available currently)
- TTS moved to vFuture
- `settings.json` migration = verify no crash on missing/old keys (pydantic defaults cover this)

### v0.8.1.1 — API Key Entry in Settings Dialog ✅ Complete

- [x] `SettingsDialog` General tab: masked `ttk.Entry` (`show="*"`) for Gemini API key
- [x] On Settings open: populate field from keyring (masked); empty string if not set
- [x] On Settings save: if field non-empty and changed, write to keyring via
      `keyring.set_password('gassi', 'gemini_api_key', value)`
- [x] Optional Claude API key field (same pattern, same tab, below Gemini field)
- [x] `main.py` `_get_api_key()`: replace `sys.exit(1)` with `return ""` on missing key
- [x] `main.py` startup: if Gemini key empty, show overlay canvas message
      `"No API key set — open Settings (⚙) to add your Gemini API key"` and auto-open Settings
- [x] `main.py` startup: app continues running (no exit) — user sets key and saves
- Note: "API key saved" restart notice not added separately — existing provider-change
      restart notice covers the case (user will restart after adding a key)

### v0.8.1.2 — settings.json Upgrade Safety

- [ ] Verify app starts cleanly with an empty or missing `settings.json`
- [ ] Verify app starts cleanly with a `settings.json` missing keys added in recent versions
      (pydantic defaults cover this — confirm no `KeyError` / `ValidationError`)
- [ ] Verify app starts cleanly with unknown/extra keys in `settings.json`
      (pydantic-settings ignores extras by default — confirm)
- [ ] Document any migration edge cases found in CHANGELOG

### v0.8.1.3 — PyInstaller Build

- [ ] Add `pyinstaller` to `[dev]` dep group in `pyproject.toml`
- [ ] `gassi.spec`: `--onedir`, hidden imports for `rapidocr_onnxruntime`, `mss`,
      `pynput`, `google.genai`, `anthropic` (optional), `chromadb` (optional),
      `keyring` + OS backend (`keyring.backends.Windows`)
- [ ] `datas`: `game_packs/` tree, `docs/`, bundled at correct relative paths
- [ ] Verify `__file__`-relative paths in `GamePackLoader`, `DebugManager`,
      `settings_manager` work under PyInstaller (`sys._MEIPASS` awareness)
- [ ] Build command documented: `pyinstaller gassi.spec`
- [ ] Smoke-test on dev machine: launch `.exe`, open Settings, set key, F1, F2
- [ ] Output: `dist/gassi/` folder

### v0.8.1.4 — zip Bundle + GitHub Release

- [ ] zip `dist/gassi/` -> `GASSI-v0.8.1-beta-win64.zip`
- [ ] `RELEASE_NOTES.md`: what's in the beta, known limitations, how to get API key
- [ ] GitHub Release: tag `v0.8.1-beta`, attach zip, paste release notes
- [ ] README end-user installation section: download zip, extract, run `gassi.exe`,
      open Settings to enter Gemini API key — no Python or terminal required

---

## v0.8.2 — Anti-Cheat Posture (post-beta)

For games with anti-cheat. Pure overlay + CV approach already avoids memory reading;
this adds capture hiding and explicit documentation.

- [ ] `SetWindowDisplayAffinity` (Windows): hide overlay from OBS/game capture
- [ ] Per-game `anticheat_note` surfaced in Settings UI (already in manifest model)
- [ ] Anti-cheat compatibility notes in `adding_game_pack.md`

---

## v0.9.0 — Local SLM + Extra Cloud Providers (post-beta)

Deferred from pre-beta roadmap. Freemium tier + alternative inference providers.
Hardware context: GTX 1660 Super (6GB VRAM) — large vision models offload to RAM.

### Local SLM (Ollama)

- [ ] `OllamaBackend` implementing `AiBackend` Protocol (Ollama REST API, no SDK needed)
- [ ] Moondream2 (2B) as primary local vision model recommendation — fits in 6GB VRAM
- [ ] Llama-3.2-3B text-only option for low-VRAM machines (advisor OCR path only)
- [ ] CPU offload path: Qwen2.5-VL / Llama 3.2 Vision via Ollama RAM offload (slow, documented)
- [ ] GPU detection at startup: `nvidia-smi` subprocess or `GPUtil` — suggest best local model
- [ ] Optional `[ollama]` dep group (no SDK — pure `httpx` calls to Ollama REST)
- [ ] Quality comparison guide in docs: local vs cloud advice quality per game

### Free Cloud API Providers

- [ ] `GroqBackend`: Llama 3.2 Vision via Groq API (fast, free tier, `groq` SDK)
      — same `AiBackend` Protocol pattern as `ClaudeBackend`
- [ ] `TogetherAIBackend`: Qwen2.5-VL / Llama 3.2 Vision via Together AI
- [ ] Provider selector in Settings extended to show all available backends
- [ ] Optional dep groups: `[groq]`, `[together]`
- [ ] API key entry in Settings for each provider (keyring storage, same pattern)

---

## v0.9.1 — Platform Support (post-beta)

Expand beyond Windows. Native window detection.

- [ ] `NativeWindowRegionProvider`: per-OS window handle lookup (pywin32/pyobjc/Xlib)
- [ ] Wayland capture backend (PipeWire/portal)
- [ ] SteamOS / Steam Deck testing
- [ ] macOS Screen Recording permission: first-run prompt

---

## vFuture — Additional UX (post-beta backlog)

- [ ] Advisor result auto-copy to clipboard (settings toggle, default off)
- [ ] Response font size setting (accessibility)
- [ ] Overlay opacity quick-slider in toolbar (avoids opening settings for common adjustment)
- [ ] `placement_input_style: strip | dialog` setting (default `strip`) — allow user to
      prefer floating dialog even when overlay is visible
- [ ] TTS voice readout: `edge-tts` integration, toggle in Settings (deferred from v0.8.1)
- [ ] Windows installer (NSIS or MSI) — deferred from v0.8.1 beta (zip bundle sufficient for beta)

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

### v0.5.18 (2026-08-25)
- [x] OCR advisor: shows `✓ HUD captured (N regions) / Analyzing with <model>...` after capture
- [x] Screenshot advisor: shows `✓ Screenshot captured (WxHpx) / Analyzing with <model>...`
- [x] Placement: shows `✓ Screenshot captured (WxHpx + CxR grid) / Analyzing with <model>...`
- [x] OCR fallback shows `OCR confidence low — switching to screenshot...`
- [x] `update_idletasks()` after each status message ensures repaint before bridge submit

### v0.5.17 (2026-08-25)
- [x] `_on_settings_saved`: restart notice only fires when hotkeys actually changed
- [x] Non-hotkey saves (model, theme, cooldown, game) log "Settings saved" with no warning
- [x] Settings tabs: `theme_use("default")` fixes Windows foreground override;
      inactive=`fg_dim`, selected=`fg_accent`, hover=`fg_text`, font explicit

### v0.5.16 (2026-08-25)
- [x] Timberborn `hud_regions_user.yaml`: `cycle_time_panel` manually added
- [x] Calibration prompt: standard label list, min size requirement, px-coord warning

### v0.5.15 (2026-08-25)
- [x] SetWindowRgn via ctypes confirmed working — hollow yellow outline rendering correctly
- [x] Nebuchadnezzar quick_prompts refined for better spatial advice

### v0.5.14 (2026-08-25)
- [x] `PlacementHighlightWindow`: ctypes replaces pywin32 (win32gui lacks CreateRectRgn)
- [x] `update()` before SetWindowRgn, GetAncestor reverted, error code logging added

### v0.5.13 (2026-08-25)
- [x] `PlacementHighlightWindow`: use `GetAncestor(GA_ROOT)` to get root HWND
      from child HWND — fixes SetWindowRgn failure and click-through

### v0.5.12 (2026-08-25)
- [x] `GamePackManifest.preferred_advisor_source` field + ViewModel wiring
- [x] Nebuchadnezzar manifest sets screenshot as default advisor source
- [x] `objectives` region corrected in manifest.yaml baseline

### v0.5.11 (2026-08-25)
- [x] Placement prompts (both games): IMPORTANT landmark note for windowed mode grid offset

### v0.5.10 (2026-08-25)
- [x] `objectives_panel` in `hud_regions_user.yaml` corrected: x=0.838 (was 0.433)
- [x] `objectives` in `manifest.yaml` corrected: x=0.838 (was 0.78)

### v0.5.9 (2026-08-25)
- [x] `HotkeyManager`: reject modifier-only hotkey strings — prevents `<alt>` alone triggering
- [x] `_is_game_focused()`: log blocked foreground window title, block when GASSI is foreground

### v0.5.8 (2026-08-25)
- [x] `advisor_ocr.txt` (both games): NEVER ask for more data rule added

### v0.5.7 (2026-08-25)
- [x] Hotkey capture: printable chars no longer wrapped in `<>` — `<alt>+8` correct
- [x] Alt detection: added `0x20000` Windows Mod2 flag alongside `0x8`
- [x] Bare modifier presses no longer terminate capture prematurely
- [x] Display label width: 16 → 22 chars
- [x] `_display_hotkey` capitalises plain characters correctly

### v0.5.6 (2026-08-25)
- [x] Diagnostic logger.info reverted to logger.debug
- [x] Calibration confirmed working: 3/3 Nebuchadnezzar regions accepted
- [x] objectives_panel placement issue noted in TODO for manual correction

### v0.5.5 (2026-08-25)
- [x] `CalibrationService`: scale detection via max value — handles fractions,
      percentages, and pixel coords in one pass without mixed-scale corruption

### v0.5.4 (2026-08-25)
- [x] `CalibrationService`: clamp all coords to [0.0, 1.0] before validation
      instead of rejecting — `objectives_panel` now passes through to OCR gate

### v0.5.3 (2026-08-24)
- [x] `CalibrationService`: auto-normalise 0–100 coords from Gemini to 0.0–1.0 fractions
- [x] `_CALIBRATION_PROMPT`: CRITICAL warning + wrong/right examples to prevent recurrence

### v0.5.2 (2026-08-24)
- [x] `_write_atomic()` in `settings_manager.py` — tmp+rename pattern, no corrupt settings.json
- [x] All save functions use atomic write; geometry/history saves bypass redundant save_settings call

### v0.5.1 (2026-08-24)
- [x] `GamePackManifest` forward-compat fields: `rag_top_k`, `rag_min_game_version`,
      `preferred_backend`, `window_class`, `anticheat_note` — all optional, all None default

### v0.4.7 (2026-08-25)
- [x] Nebuchadnezzar: full F1/F2/calibration/highlight testing complete
- [x] Timberborn: retested, all features working with new code
- [x] All hotkey fixes validated (Alt+8/9/0, modifier-only rejection)
- [x] PlacementHighlightWindow: SetWindowRgn via ctypes working correctly
- [x] Calibration: coord normalisation robust across all three Gemini scale formats

### v0.4.6 (2026-08-24)
- [x] `docs/v1_scope.md` updated to shipped state: Nebuchadnezzar added, all features
      updated, deferred items renumbered, known limitations updated

### v0.4.5 (2026-08-24)
- [x] `docs/adding_game_pack.md` rewritten: bootstrap workflow, OCR tuning guide,
      grid JSON template, Settings UI activation, updated checklist

### v0.4.4 (2026-08-24)
- [x] Game switch restart notice in overlay canvas when `active_game_id` changes
- [x] Startup log includes pack display name

### v0.4.3 (2026-08-24)
- [x] `SettingsDialog._HEIGHT` increased to 470px for game selector row

### v0.4.2 (2026-08-24)
- [x] Nebuchadnezzar OCR preprocessor configs: `NEBU_RESOURCE_BAR_CONFIG` (4×, aggressive),
      `NEBU_STATUS_BAR_CONFIG` (3×, standard), `NEBU_OBJECTIVES_CONFIG` (2.5×, minimal)
- [x] All three registered in `LABEL_CONFIGS` by region label — auto-applied at runtime

### v0.4.1 (2026-08-24)
- [x] Active game selector in Settings → General — `ttk.Combobox` listing installed packs
- [x] `GamePackLoader.list_available_packs()` — scans game_packs/ dir, reads manifest display names
- [x] `MainOverlay.set_pack_loader()` setter — same pattern as `set_calibration_service()`
- [x] `active_game_id` saved to `settings.json` on Settings save
- [x] `SettingsDialog` accepts optional `pack_loader` parameter (graceful fallback if absent)

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
