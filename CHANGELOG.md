# Changelog

All notable changes to GASSI will be documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased] — v0.8.1 Distribution

See [TODO.md](TODO.md) for planned sub-versions v0.8.1.2–0.8.1.4.

## [0.8.3] - 2026-08-28

### Added
- `SettingsDialog` General tab: API key section (v0.8.1.1) with masked `ttk.Entry`
  fields for Gemini and Claude API keys, separated by a horizontal rule.
- On Settings open: fields pre-populated from OS keyring (displayed masked).
- On Settings save: non-empty changed keys written to keyring via
  `keyring.set_password("gassi", "gemini_api_key" | "claude_api_key", value)`.
  Empty fields and unchanged values are never written.
- Hint label: "Keys stored in OS keyring — never written to disk."
- `SettingsDialog._HEIGHT` bumped from 540 to 640px.

### Changed
- `main.py` `_get_api_key()`: returns `""` on missing key instead of calling
  `sys.exit(1)`. App no longer exits on first run without a key.
- `main.py` startup: if Gemini key is empty, shows overlay canvas message
  `"## No API key set"` and auto-opens Settings after 500ms delay.
- `main.py`: removed `import sys` (no longer needed).
- `main.py`: `logging.StreamHandler()` no longer passes `sys.stdout` explicitly.

## [0.8.2] - 2026-08-26

### Added
- `views/floating_placement_dialog.py`: `FloatingPlacementDialog` — semi-transparent
  centered `tk.Toplevel` shown when main overlay is offscreen and F2 fires.
  Themed, always-on-top, full keyboard focus (Enter submits, Escape dismisses).
- Combobox pre-populated with history + quick-prompts (same data as inline
  `PlacementInputStrip`). Wider combobox and larger font than the strip for
  comfortable keyboard use while the game is visible.
- Header bar (title + ✕ close button), footer hint (`Enter to submit • Esc to dismiss`).
- Position: center screen horizontally, 35% from top vertically. 40% screen width
  × 18% screen height; min 400×120px.
- Dialog hides itself before invoking `on_submit` so it does not appear in the
  placement screenshot sent to the AI backend.
- `MainOverlay.show_floating_placement_dialog(suggestions, on_submit)` public method.
- `MainOverlay._floating_placement: FloatingPlacementDialog` created at init,
  destroyed in `_on_close_click()`.

### Changed
- `main.py` `_open_placement()`: when `overlay._offscreen` is True, calls
  `overlay.show_floating_placement_dialog()` instead of
  `overlay.toggle_placement_strip()`. Overlay remains offscreen; no slide-back.
  Inline strip path unchanged when overlay is visible.

## [0.8.1] - 2026-08-26

### Added
- `views/floating_advice_window.py`: `FloatingAdviceWindow` — semi-transparent centered
  `tk.Toplevel` shown when main overlay is offscreen and F1 advisor result arrives.
  Themed, always-on-top, auto-dismisses after `floating_advice_timeout_seconds`.
- Markdown rendering in floating window: same `##`, `- bullet`, `**bold**` tag logic
  as `OverlayCanvas` — no shared code (standalone implementation to avoid coupling).
- Header bar (title + ✕ button), footer hint, click-background-to-dismiss.
- Position: upper-center of primary monitor (8% from top, centered horizontally).
  35% screen width × 28% screen height; min 340×180px.
- `AppSettings.show_floating_advice_when_hidden: bool = True`
- `AppSettings.floating_advice_timeout_seconds: int = 12`
- `MainOverlay.show_floating_advice(advice_text, timeout_seconds)` public method.
- `MainOverlay._floating_advice: FloatingAdviceWindow` created at init, destroyed on close.
- Settings dialog: "Floating advice" toggle checkbutton in General tab.
  `SettingsDialog._HEIGHT` increased to 540px.

### Changed
- `AssistantViewModel._on_result`: when overlay is offscreen and
  `show_floating_advice_when_hidden` is True, routes advice to
  `overlay.show_floating_advice()` instead of `auto_expand_for_result()` +
  `canvas.show_advice()`. Inline path unchanged when overlay is visible.

## [0.7.4] - 2026-08-26

### Added
- `building_footprints: dict[str, list[int]]` field in `GamePackManifest` (default `{}`).
- `_lookup_footprint(advice_text, building_footprints)` module-level helper in ViewModel:
  case-insensitive substring scan; longest keyword match wins; no AI call.
- `cell_to_screen_pixels()` extended with optional `footprint: tuple[int, int]`;
  pixel rect now spans `fp_w × fp_h` cells; footprint clamped to grid bounds.
- `PlacementHighlightWindow.show()` `footprint` param: label suffix `D5 (4×4)` when
  footprint ≠ `(1, 1)`. `SetWindowRgn` calculation unchanged — works for any rect size.
- `MainOverlay.show_placement_highlight()` passes `footprint` through to highlight window.
- Timberborn manifest: 13 `building_footprints` entries (pump, forester, farm, battery,
  power wheel, sawmill, workshop, warehouse, district center, dam, floodgate, lumberjack).
- Nebuchadnezzar manifest: 11 `building_footprints` entries (shrine, temple, ziggurat,
  bazaar, granary, storehouse, well, house, garden, school, bathhouse). Replaces
  the v0.6.0 commented-out placeholder block.
- AD-27 added to `docs/architecture.md`.

## [0.7.3] - 2026-08-26

### Added
- `UsageStats` Pydantic model (`models/results.py`): `input_tokens`, `output_tokens`,
  `estimated_cost_usd`. `total_tokens` property.
- `estimate_cost()` helper with hardcoded per-1M-token rate table (Gemini Flash/Pro,
  Claude Haiku/Sonnet/Opus). Returns `None` for unknown model strings.
- `_extract_usage()` in `GeminiBackend`: reads `usage_metadata.prompt_token_count`
  and `candidates_token_count` from Gemini response.
- `_extract_usage()` in `ClaudeBackend`: reads `response.usage.input_tokens` /
  `output_tokens` from Anthropic response.
- Session accumulators in `AssistantViewModel`: `_session_input_tokens`,
  `_session_output_tokens`, `_session_cost_usd`.
- `_accumulate_usage()` in ViewModel: adds per-call stats to session totals,
  calls `overlay.update_token_display()`. Logs session totals at DEBUG.
- `MainOverlay._token_label`: dim label in footer, right of cooldown label.
  Hidden (empty text) until first call. Format: `↑1.2k ↓0.8k ~$0.0012`.
- `MainOverlay.update_token_display(text)`: public setter for ViewModel to call.

### Changed
- `AiBackend` Protocol (breaking): both `complete_text()` and `complete_with_image()`
  now return `tuple[str, UsageStats]` instead of bare `str`. Both backends and
  all ViewModel call sites updated atomically.
- `_on_result()` and `_on_placement_result()` unpack `tuple[str, UsageStats]`
  before processing response text.

## [0.7.2] - 2026-08-26

### Added
- `AiProvider` enum (`models/enums.py`): `GEMINI`, `CLAUDE`.
- `active_ai_provider: AiProvider` field in `AppSettings` (default `GEMINI`);
  `claude_model: str` field (default `claude-sonnet-4-6`).
- `core/ai/factory.py`: `build_ai_backend(settings, api_key)` constructs the
  correct backend; `get_api_key(provider)` retrieves from keyring;
  `is_claude_available()` checks for `anthropic` SDK without importing it.
- Backend selector `ttk.Combobox` in Settings → General. Model dropdown
  switches content per provider: Gemini fetches live, Claude shows static list.
  Both model choices persisted independently so switching back restores prior selection.
- Claude option hidden from dropdown when `[claude]` extras absent; note label shown.
- `MainOverlay.set_claude_api_key()` setter; passed through to `SettingsDialog`.
- Provider change in `_on_settings_saved` shows restart notice in overlay canvas.

### Changed
- `main.py`: `GeminiBackend` direct construction replaced by `build_ai_backend()`.
  API key retrieval is now provider-aware (`_get_api_key(provider)`). Startup
  log includes active provider. `preferred_backend` manifest hint logged at startup.
- `CalibrationService` always uses the Gemini key regardless of active provider
  (it requires `response_schema`, a Gemini-only feature).
- `SettingsDialog._HEIGHT` increased to 510px for backend selector row.
- `_fetch_models` renamed to `_fetch_gemini_models` for clarity.

## [0.7.1] - 2026-08-26

### Added
- `core/ai/claude_backend.py`: `ClaudeBackend` implementing `AiBackend` Protocol
  (Anthropic SDK). Drop-in replacement for `GeminiBackend` — same method signatures.
- `complete_text()`: text-only async call via `AsyncAnthropic.messages.create()`.
- `complete_with_image()`: multimodal call with base64-encoded image. `response_schema`
  argument accepted for Protocol compatibility but ignored — JSON output enforced via
  system prompt instruction; `_parse_placement_response()` handles both backends
  without changes (AD-26).
- Rate-limit / overloaded error handling: catches `rate_limit_error`, `overloaded_error`,
  529, 429 by string match; raises readable `RuntimeError` with retry guidance.
- `fetch_available_claude_models()`: returns static ordered list (Haiku → Sonnet → Opus).
  Anthropic has no public model-listing endpoint.
- Optional dep group `[claude]` in `pyproject.toml`: `anthropic>=0.40` only.
  Install with `uv sync --extra claude`. Not installed by default.
- Deferred import: `anthropic` imported at `__init__` time, not module level —
  safe to import `claude_backend` without extras installed.
- AD-26 added to `docs/architecture.md`.

## [0.6.7] - 2026-08-25

### Changed
- All RAG docs written progressively during v0.6.1–v0.6.6; v0.6.7 confirms
  all four doc targets complete.
- `docs/adding_game_pack.md`: Section 5 (RAG guide), Section 7 checklist (5 RAG items)
- `docs/architecture.md`: AD-25 finalised with `ONNXMiniLM_L6_V2` rationale,
  `sentence-transformers` rejection, injection point
- `docs/v1_scope.md`: Feature 6 RAG shipped
- `README.md`: RAG in Features, install, project structure
- `v0.6.0` RAG milestone marked complete in TODO

## [0.6.6] - 2026-08-25

### Added
- `game_packs/nebuchadnezzar/knowledge/` — 6 markdown knowledge files:
  - `01_resources.md` — food types, building materials, luxury goods, workers,
    bronze tools
  - `02_housing_evolution.md` — full tier chain (shack → noble estate), evolution
    checklist, coverage radii (well ~5x5, bazaar walker ~60-80 tiles), devolution warning
  - `03_bazaar_distribution.md` — walker route mechanics, placement rules, storehouse
    positioning, signs of distribution failure
  - `04_approval_prestige_objectives.md` — approval causes/fixes, prestige sources
    (small shrine 1-2, large temple 15-25, monument 50-200), objective tracking
  - `05_building_costs_production.md` — cost table (18 buildings), all core production
    chains (brick, grain, dates, pottery, linen, beer), labor requirements
  - `06_stages_meta_strategy.md` — 3-stage guide, common failure modes, useful ratios
- `game_packs/nebuchadnezzar/manifest.yaml`: `rag_collection_name: nebuchadnezzar_knowledge`,
  `rag_top_k: 4`, `rag_min_game_version: "1.0"`

### Note
Collection must be ingested before RAG activates:
```
uv run python tools/ingest_knowledge.py --game-id nebuchadnezzar --source-dir game_packs/nebuchadnezzar/knowledge --game-version 1.0 --reset
```

## [0.6.5] - 2026-08-25

### Changed
- v0.6.5 implemented as part of v0.6.1 and v0.6.4 — no additional code required.
  `ChromaRagService.query()` `$gte` filter and `_build_rag_context()` `min_game_version`
  pass-through were both already in place.

## [0.6.4] - 2026-08-25

### Added
- `AssistantViewModel.__init__` accepts optional `rag_service: RagService` parameter
  (defaults to `NullRagService` when not provided — fully backward-compatible)
- `AssistantViewModel._build_rag_context(query_text) -> str`: queries `RagService`,
  formats retrieved chunks as `## Retrieved Knowledge\n- chunk...` block prepended
  to system prompt. Returns empty string when RAG unavailable or no chunks returned.
- OCR advisor path: combined OCR text used as RAG query; retrieved context prepended
  to system prompt before Gemini call. Logs `rag=on (N chunks)` or `rag=off`.
- Screenshot advisor path: RAG skipped (no text query available); logs
  `rag=off (screenshot mode — no text query available)` when collection is present.
- `main.py`: `RagServiceFactory.for_game_pack()` called at startup using
  `_active_manifest.rag_collection_name`; result passed to ViewModel.
- Startup log now includes `rag: on/off` status.

## [0.6.3] - 2026-08-25

### Added
- `game_packs/timberborn/knowledge/` — 6 markdown knowledge files:
  - `01_resources.md` — logs, planks, food, water, science, metal mechanics and ratios
  - `02_water_management.md` — drought cycle, dams vs floodgates, water tanks, badwater,
    irrigation; drought reserve formula (500–800 units per 10 beavers per drought day)
  - `03_power_system.md` — windmills (height dependency), water wheels (drought caveat),
    batteries (3,600 units capacity), power shaft distribution
  - `04_forestry_farming_costs.md` — tree growth rates, crop calorie densities, building
    cost table (20 buildings), population growth mechanics
  - `05_districts_labour.md` — district system, labour ratios, builder percentages,
    worker priority, shift scheduling, expansion timing signals
  - `06_v06_patch_meta.md` — v0.6 changes, terrain meta, common failure modes,
    useful ratios table
- `game_packs/timberborn/manifest.yaml`: `rag_collection_name: timberborn_knowledge`,
  `rag_top_k: 4`, `rag_min_game_version: "0.6"`

### Note
Collection must be ingested before RAG activates:
```
uv sync --extra rag
uv run python tools/ingest_knowledge.py --game-id timberborn --source-dir game_packs/timberborn/knowledge --game-version 0.6 --reset
```

## [0.6.2] - 2026-08-25

### Added
- `tools/ingest_knowledge.py`: CLI for chunking, embedding, and persisting game
  knowledge to a Chroma collection.
  - `--game-id`, `--source-dir` (required); `--game-version`, `--model`,
    `--chunk-size`, `--chunk-overlap`, `--reset`, `--game-packs-root` (optional)
  - Reads `.md` / `.txt` recursively from `--source-dir`
  - Paragraph-split chunking with sentence-level sub-split for oversized paragraphs;
    configurable `--chunk-size` (default 400 tokens) and `--chunk-overlap` (default 50)
  - Metadata per chunk: `source_file`, `chunk_index`, `game_version`
  - Idempotent by default: already-ingested `source_file` values skipped;
    `--reset` drops and rebuilds the collection
  - Output: `game_packs/<game_id>/rag/` (persistent Chroma), collection named
    `<game_id>_knowledge`
  - Auto-detects `game_packs/` root from script location; overrideable via
    `--game-packs-root`

## [0.6.1] - 2026-08-25

### Added
- `core/rag/` subpackage: `RagService` Protocol, `NullRagService`, `ChromaRagService`,
  `RagServiceFactory` (AD-25)
- `RagService` Protocol (`core/rag/protocol.py`): `query(text, top_k, min_game_version)`,
  `is_available()` — structural subtyping, `@runtime_checkable`
- `NullRagService` (`core/rag/null_backend.py`): no-op fallback, zero extra imports,
  used when no `rag/` collection present or extras not installed
- `ChromaRagService` (`core/rag/chroma_backend.py`): loads persistent Chroma collection
  from `game_packs/<id>/rag/`, deferred chromadb import, graceful degradation on any
  load or query error
- `RagServiceFactory.for_game_pack()` (`core/rag/factory.py`): returns `ChromaRagService`
  when `rag/` folder exists + `collection_name` set + chromadb available; else `NullRagService`
- Optional dep group `[rag]` in `pyproject.toml`: `chromadb>=0.6`,
  `sentence-transformers>=3.0` — not installed by default
- AD-25 added to `docs/architecture.md`

## [0.5.18] - 2026-08-25

### Changed
- **Status messages during AI calls** — all three paths now show a two-line
  progress sequence visible while the AI call is in flight:
  - OCR advisor: `✓ HUD captured (N regions) / Analyzing with <model>...`
  - Screenshot advisor: `✓ Screenshot captured (WxH px) / Analyzing with <model>...`
  - Placement: `✓ Screenshot captured (WxH px + CxR grid) / Analyzing with <model>...`
- OCR fallback to screenshot now shows `OCR confidence low — switching to screenshot...`
  before re-entering the screenshot path.
- `update_idletasks()` called immediately after each status message so the
  overlay repaints before the blocking bridge submit.

## [0.5.17] - 2026-08-25

### Fixed
- **`_on_settings_saved` in `main.py`**: restart notice no longer fires on every
  settings save. Now compares old vs new hotkey values; only logs
  "restart required for hotkey changes" and shows the overlay notice when a
  hotkey actually changed. Model, theme, cooldown, game changes log "Settings saved"
  with no restart warning.
- **Settings tab readability**: `ttk.Style.theme_use("default")` applied before
  configuring `Settings.TNotebook.Tab` so Windows native "vista" theme no longer
  overrides foreground colours. Inactive tabs now render in `fg_dim`, selected tab
  in `fg_accent`, hover in `fg_text`. Font explicitly set on tab labels.

## [0.5.16] - 2026-08-25

### Fixed
- Timberborn calibration: `cycle_time_panel` manually added to
  `hud_regions_user.yaml` — Gemini consistently returns zero dimensions for the
  top-right time/cycle region. Position from manifest baseline (known good).
- `_CALIBRATION_PROMPT`: added standard label list so Gemini uses consistent
  names (`top_resource_bar`, `cycle_time_panel`, etc.) matching `LABEL_CONFIGS`
  and advisor prompts. Added explicit minimum size requirement (`>= 0.05` width,
  `>= 0.02` height) to prevent zero-dimension regions being returned.
- Added pixel coordinate example to CRITICAL section to reduce px-coord returns.

### Notes
- Root cause of inconsistent label names: Gemini invents labels each run
  (`top_bar_resources`, `resource_bar_top`, `top_resource_bar` for same region).
  Prompt now steers toward canonical names. Full fix would require post-processing
  to match calibrated regions to manifest labels by spatial overlap.

## [0.5.15] - 2026-08-25

### Fixed
- `PlacementHighlightWindow`: `SetWindowRgn` via ctypes confirmed working —
  hollow yellow outline box now renders correctly over game screen.

### Changed
- Nebuchadnezzar `quick_prompts` refined: vague prompts replaced with specific
  building-type questions that produce better spatial advice from Gemini.
  e.g. "Where should I build the next temple or entertainment venue?" →
  "Where should I place the Temple to cover the most housing blocks?"

## [0.5.14] - 2026-08-25

### Fixed
- `PlacementHighlightWindow`: `win32gui` does not expose `CreateRectRgn` (it is
  a GDI32 function, not a win32gui function). Switched entirely to `ctypes`:
  `ctypes.windll.gdi32.CreateRectRgn/CombineRgn/DeleteObject` and
  `ctypes.windll.user32.SetWindowRgn/GetWindowLongW/SetWindowLongW`.
  pywin32 dependency removed from this module entirely.
- `show()`: changed `update_idletasks()` to `update()` before `SetWindowRgn`
  so the Win32 window is fully resized before the region coordinates are applied.
- Reverted `GetAncestor(GA_ROOT)` — documented in module docstring why it is
  wrong for tkinter Toplevels (returns main Tk HWND, not the Toplevel HWND).
- `GetLastError()` now logged when `SetWindowRgn` returns 0.

## [0.5.13] - 2026-08-25

### Fixed
- `PlacementHighlightWindow._apply_region_and_clickthrough()`: `winfo_id()` returns
  a child HWND on Windows, not the root HWND that `SetWindowRgn` and `SetWindowLong`
  require. Added `win32gui.GetAncestor(child_hwnd, GA_ROOT)` to resolve the true
  top-level HWND. Fixes `SetWindowRgn failed` warning and restores click-through
  + hollow region clipping behaviour.

### Notes
- Building footprint rendering (multi-cell highlight for large buildings like Temple
  4×4) tracked in TODO under v0.6.0. Current highlight shows placement anchor cell
  only.

## [0.5.12] - 2026-08-25

### Added
- `GamePackManifest.preferred_advisor_source`: optional per-pack advisor source
  override (`"ocr"` or `"screenshot"`). Applied at startup before global settings.
  Nebuchadnezzar manifest sets `"screenshot"` — OCR unreliable until region
  coordinates are refined.
- `AssistantViewModel.__init__` applies pack preference over global setting;
  logs which source was selected and why.

### Fixed
- Nebuchadnezzar `manifest.yaml`: `objectives` region corrected from x=0.78 (wrong)
  to x=0.838 — calibration had placed it at city name area (x=0.43). Corrected in
  both `manifest.yaml` (baseline default) and `hud_regions_user.yaml` (active).

## [0.5.11] - 2026-08-25

### Fixed
- Placement prompt (both games): added `IMPORTANT` note that the grid covers the
  entire screenshot including UI panels. Instructs Gemini to reference visible
  in-game landmarks alongside cell coordinates so players can locate the target
  even when the cell highlight appears offset (windowed mode).

## [0.5.10] - 2026-08-25

### Fixed
- `game_packs/nebuchadnezzar/hud_regions_user.yaml`: `objectives_panel` region
  manually corrected to x=0.838, y=0.028, w=0.155, h=0.133 — calibration had
  placed it at x=0.433 (centre screen, catching city name "Uruk"), causing OCR
  advisor to read early-game signals and give wrong advice.
- `game_packs/nebuchadnezzar/manifest.yaml`: same correction applied to
  `objectives` baseline region.

## [0.5.9] - 2026-08-25

### Fixed
- **`HotkeyManager.register()`**: modifier-only hotkey strings (e.g. `<alt>`) are
  now rejected with a warning before being passed to pynput. This prevents Alt-alone
  triggering the advisor when `settings.json` contains legacy broken format
  `<alt>+<8>` from pre-v0.5.7 — pynput was silently dropping the invalid `<8>` part
  and matching on `<alt>` alone.
- **`_is_game_focused()`**: logs foreground window title at DEBUG level when hotkey
  is blocked, making window title mismatches diagnosable. Also blocks triggers when
  GASSI's own overlay title is in the foreground.

## [0.5.8] - 2026-08-25

### Fixed
- `game_packs/nebuchadnezzar/prompts/advisor_ocr.txt`: added `NEVER ask the player
  for more information` rule. Gemini was responding with a request for more OCR data
  when a region value was incomplete instead of giving best-effort advice.
- `game_packs/timberborn/prompts/advisor_ocr.txt`: same rule added for consistency.

## [0.5.7] - 2026-08-25

### Fixed
- **Hotkey capture — wrong pynput key format for printable characters.**
  `_on_key_press` was wrapping every key in angle brackets, producing
  `<alt>+<8>` instead of the correct `<alt>+8`. pynput only uses angle
  brackets for special keys (F1–F12, space, escape, etc.); regular printable
  characters (letters, digits, symbols) must not be wrapped. Alt+8/9/0 and
  similar combos now register and trigger correctly.
- **Alt detection on Windows.** Added `event.state & 0x20000` (Windows Mod2)
  alongside the existing `0x8` (X11 standard). Fixes Alt not being detected
  on some Windows configurations.
- **Bare modifier keypresses no longer terminate capture.** Pressing Alt alone
  while waiting for a key no longer saves an incomplete hotkey — the widget
  waits for the non-modifier key to complete the combo.
- **Hotkey display label width** increased from 16 to 22 characters to
  accommodate longer strings like "Alt + 8" without clipping.
- **`_display_hotkey`** updated to capitalise plain characters correctly
  (e.g. `<alt>+8` → "Alt + 8", `<shift>+a` → "Shift + A").

## [0.5.6] - 2026-08-25

### Fixed
- `CalibrationService`: diagnostic `logger.info` for raw coordinates reverted to
  `logger.debug` — only visible when debug logging enabled, not in normal log panel.

### Notes
- Calibration now handles all three Gemini coordinate formats correctly (fractions,
  percentages, pixel coords). Confirmed working: 3/3 regions accepted on Nebuchadnezzar.
- `objectives_panel` accepted but placed at x≈0.43 (centre) not x≈0.84 (top-right) —
  Gemini misidentified the region location. Tracked in TODO v0.4.7 checklist for
  manual correction via F4 debug frame.

## [0.5.5] - 2026-08-25

### Fixed
- `CalibrationService._validate_region()`: smarter coordinate scale detection.
  Previous fix divided all values by 100 when any single value exceeded 1.0,
  causing near-zero dimensions when Gemini mixed scales (e.g. `x=82` but `w=0.15`).
  Now uses `max(x, y, w, h)` to determine scale: >100 → pixel coords (divide by
  `img_w`/`img_h`), >1.0 → percentage (divide by 100), ≤1.0 → already correct.
  All three Gemini coordinate formats now handled correctly in a single pass.

## [0.5.4] - 2026-08-25

### Fixed
- `CalibrationService._validate_region()`: regions were rejected with "out of bounds
  after normalisation" even when the coordinates were valid but slightly over 1.0
  (e.g. `x=1.02` from Gemini rounding). All four coordinate values are now clamped
  to `[0.0, 1.0]` and the region is passed to OCR validation rather than rejected.
  The `objectives_panel` in Nebuchadnezzar was affected by this — now accepted.
  Hard geometry rejection removed; OCR confidence is the only acceptance gate.

## [0.5.3] - 2026-08-24

### Fixed
- `CalibrationService._validate_region()`: Gemini occasionally returns coordinates
  on a 0–100 percentage scale despite the prompt specifying 0.0–1.0 fractions,
  causing a Pydantic `ValidationError` on `HudRegion`. Values > 1.0 are now
  automatically normalised by dividing by 100 before validation.
- `_CALIBRATION_PROMPT`: strengthened coordinate instructions with explicit
  `CRITICAL` warning, concrete wrong/right examples (82.5 WRONG, 0.825 CORRECT),
  and margin expressed as fractions (0.01–0.02) not percentages.

## [0.5.2] - 2026-08-24

### Changed
- `core/settings_manager.py`: all writes now use `_write_atomic()` — writes to
  `.tmp` then renames, preventing corrupted `settings.json` on mid-write process kill.
  `save_window_geometry` and `save_prompt_history` now call `_write_atomic` directly
  instead of routing through `save_settings`, avoiding a redundant `load_saved_settings`
  call on every save.

## [0.5.1] - 2026-08-24

### Added
- `GamePackManifest` forward-compatibility fields (all optional, default `None`):
  - `rag_top_k: int | None` — per-game RAG chunk count override (v0.5.0)
  - `rag_min_game_version: str | None` — minimum game version for RAG chunk filtering (v0.5.0)
  - `preferred_backend: str | None` — pack-level AI backend preference (v0.6.0)
  - `window_class: str | None` — OS window class for native detection (v0.7.0)
  - `anticheat_note: str | None` — informational anti-cheat note (v0.7.1)
- All existing packs unaffected — fields default safely, no manifest.yaml changes needed.

## [0.4.6] - 2026-08-24

### Changed
- `docs/v1_scope.md` fully updated to reflect shipped state as of v0.4.4:
  Nebuchadnezzar added as second target game, all features updated (grid overlay,
  cell highlight, settings, calibration, debug tools), deferred items renumbered
  to match current roadmap, known limitations updated.

## [0.4.5] - 2026-08-24

### Changed
- `docs/adding_game_pack.md` fully rewritten for current state:
  - Section 1: `game_id` in manifest required for Settings dropdown discovery.
    Activation via Settings UI (not manual `settings.json` edit).
  - Section 2: bootstrap-from-screenshots workflow documented (Nebuchadnezzar process).
    CalibrationService as recommended path, manual F4 as fallback.
  - Section 3 (new): OCR preprocessor config guide — per-region tuning table,
    `LABEL_CONFIGS` registry, `scale_factor`/`block_size`/`C` guidance by HUD type.
  - Section 4: placement prompt template updated for grid overlay JSON response format.
  - Section 6: testing checklist updated (Settings dropdown, CalibrationService,
    highlight box verification).
  - Section 7: switching packs via Settings UI documented; env var override noted.

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
