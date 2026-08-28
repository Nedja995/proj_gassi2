# GASSI — New Session Handoff Document

Read this before starting any work. It captures everything needed to continue
development without going through previous chat history.

---

## What GASSI Is

A Windows desktop overlay (Python/tkinter) that provides real-time AI strategy advice
for PC games via screen capture + Gemini API. No game memory reading — pure CV + overlay.

**Current state:** v0.8.2. v0.8.0 UX Polish complete (FloatingAdviceWindow + FloatingPlacementDialog).
Next: v0.8.1 Distribution milestone — API key in Settings dialog, PyInstaller build, zip bundle.
Key v0.8.1 decisions: no first-run wizard; API key via masked Settings field + keyring;
zip bundle only for beta (NSIS/MSI deferred to vFuture); TTS deferred to vFuture.

**Note on versioning:** `pyproject.toml` is at `0.8.2`. Each sub-version gets a discrete
bump: v0.8.1.1 will bump to `0.8.3`, v0.8.1.2 to `0.8.4`, etc.

**Repo:** `F:\__STORAGE\__PROJECTS_F\proj-gassi\proj_gassi2`
**Stack:** Python 3.12, tkinter/ttk, pydantic-settings, mss, RapidOCR (ONNX), google-genai,
anthropic (optional `[claude]`), pynput, opencv-python-headless, pywin32,
chromadb (optional `[rag]`), uv package manager

---

## Key Docs — Read On Demand, Not Upfront

**Read all these at session start**
This handoff doc is designed to be self-contained for starting work.

- `TODO.md` — only if planning the next milestone or checking roadmap ordering
- `CHANGELOG.md` — only if debugging a regression or checking what changed in a specific version
- `docs/architecture.md` — only if making a non-obvious design decision (check if an AD already covers it)
- `docs/adding_game_pack.md` — only when adding a new game pack
- `docs/v1_scope.md` — only when updating the known limitations or scope

**Source files:** read only the specific files the task touches. Never edit from memory.

---

## Architecture — Quick Summary

**Pattern:** MVVM. Models (Pydantic) → ViewModel (`assistant_viewmodel.py`) → Views (tkinter).
ViewModel owns the mode FSM (IDLE/ADVISOR/PLACEMENT), all AI call dispatch, cooldown, debug.

**Protocol abstractions** (in `core/ai/protocol.py`, `core/capture/protocol.py`):
- `AiBackend` — currently `GeminiBackend`. Swap in Claude/Ollama without touching ViewModel.
- `CaptureBackend` — currently `MssCaptureBackend`.
- `CaptureRegionProvider` — currently overlay-anchored. Future: native window detection.

**Async bridge:** dedicated asyncio thread + `queue.Queue` → tkinter `after()` at 50ms.
AI calls never block the UI thread. Pattern is in `core/async_bridge.py`.

**Game packs:** folder convention `game_packs/<game_id>/manifest.yaml` + `prompts/`.
No plugin system. Adding a game = adding a folder. See `docs/adding_game_pack.md`.

---

## Platform-Specific Code Pattern

All platform-specific code uses `platform.system()` + `try/except ImportError` fail-open.
This pattern is used everywhere — never break it.

```python
if platform.system() == "Windows":
    try:
        import win32gui
        # windows-specific code
    except ImportError:
        logger.debug("pywin32 not available — skipping")
elif platform.system() == "Darwin":
    try:
        from AppKit import NSApp
        # macos-specific code
    except ImportError:
        logger.debug("pyobjc not available — skipping")
# Linux: silently no-op or alpha fallback
```

**Critical Windows lessons learned (document in every relevant file):**
- `WS_EX_LAYERED` + `SetLayeredWindowAttributes(LWA_COLORKEY)` + tkinter Canvas
  (GDI child window) = DOES NOT WORK on Windows 10/11 DWM. Causes solid black overlay.
  Use `SetWindowRgn` instead (AD-24).
- `win32gui` does NOT have `CreateRectRgn` — that is a GDI32 function.
  Use `ctypes.windll.gdi32.CreateRectRgn` directly.
- `winfo_id()` on a Toplevel returns the correct HWND directly.
  Do NOT use `GetAncestor(GA_ROOT)` — for tkinter Toplevels that returns the
  main Tk window HWND, not the Toplevel's HWND.
- `withdraw()` / `deiconify()` on `overrideredirect(True)` Toplevels recreates the HWND
  on Windows, losing all WS_EX_* style bits. Use geometry() to move off-screen instead.
- Call `top.update()` (not `update_idletasks()`) before any win32 calls — ensures
  the Win32 window is fully mapped and sized before region/style operations.

---

## Naming Conventions

- Python: PEP8, `snake_case`. Private: `_underscore_prefix`. Names should be informative.
- Prefer `ttk` over `tk` widgets. Prefer subclassing.
- Variable names: low case snake, slightly longer descriptive names preferred.
- No hardcoded version strings anywhere except `pyproject.toml`.
- Never remove markdown from prompts. Never simplify documentation without instruction.

---

## Version and Commit Discipline

**Every feature is split into discrete sub-versions** (e.g. v0.4.1, v0.4.2, v0.4.3).
Each sub-version gets its own commit. Docs (CHANGELOG, TODO, pyproject.toml) are committed
separately as a final commit per batch.

**Commit structure per sub-version:**
```bash
# Code commit — only files changed for that specific sub-version
git add <specific files only>
git commit -m "v0.X.Y: short description of what changed"

# Docs commit — after all sub-versions in a batch are done
git add CHANGELOG.md TODO.md pyproject.toml
git commit -m "docs: changelog, todo, pyproject for v0.X.Y-v0.X.Z"
```

**Never** `git add .` — always add specific files so each commit is clean and revertable.

**pyproject.toml version** must be bumped with every sub-version.

---

## Mandatory Doc Updates Per Task

Every task must update ALL of these:
1. `CHANGELOG.md` — add `## [X.Y.Z] - YYYY-MM-DD` section with Added/Fixed/Changed
2. `TODO.md` — mark completed items `[x]`, add new sub-version to Completed section
3. `pyproject.toml` — bump `version = "X.Y.Z"`
4. `docs/architecture.md` — add ADR if a non-obvious design decision was made
5. `README.md` — update Features section version number and feature list if visible behaviour changed

---

## Current Roadmap Summary

```
v0.4.7  ✅ Complete — Nebuchadnezzar + Timberborn live testing
v0.5.x  ✅ Complete (v0.5.1–v0.5.18) — GamePackManifest fields, atomic settings,
           calibration fixes, hotkey fixes, placement highlight (SetWindowRgn)
v0.6.0  ✅ Complete (v0.6.1–v0.6.7) — RAG pipeline (Chroma + ONNXMiniLM,
           ingestion CLI, Timberborn + Nebuchadnezzar knowledge bases)
v0.7.0  ✅ Complete (v0.7.1–v0.7.4) — Multi-backend: ClaudeBackend, backend selector
           UI, token/cost tracking, building footprint registry
v0.8.0  🔜 Active — UX Polish pre-release
  v0.8.0.1 ✅ — FloatingAdviceWindow (F1 when overlay offscreen, themed, auto-dismiss)
  v0.8.0.2 ✅ — Floating placement dialog (F2 when overlay offscreen)
  v0.8.0.3 — retired, items moved to vFuture
v0.8.1  — Distribution / beta release (PyInstaller, zip bundle, GitHub Release)
  v0.8.1.1 — API key entry in Settings dialog (masked ttk.Entry, keyring write)
  v0.8.1.2 — settings.json upgrade safety verification
  v0.8.1.3 — PyInstaller build + gassi.spec
  v0.8.1.4 — zip bundle + GitHub Release + end-user README
v0.8.2  — Anti-cheat posture (SetWindowDisplayAffinity, docs)
v0.9.0  — Local SLM + cloud providers (Ollama/Moondream2, Groq, Together AI)
v0.9.1  — Platform (Wayland, native window detection, macOS, SteamOS)
```

---

## Active Game Packs

### Timberborn (v0.6) — Primary, fully tested
- HUD regions: `top_resource_bar`, `population_panel`, `cycle_time_panel`
- `hud_regions_user.yaml` exists and working (5 regions)
- `cycle_time_panel` manually added — Gemini consistently misses it in auto-calibration
- Advisor source: OCR (default) + Screenshot fallback

### Nebuchadnezzar (v1.0) — Secondary, live-tested
- HUD regions: `resource_bar`, `date_time_panel`, `objectives_panel`
- `objectives_panel` manually corrected to x=0.838 (calibration keeps placing it at x=0.43)
- `preferred_advisor_source: screenshot` — OCR unreliable until regions stabilise
- `hud_regions_user.yaml` exists and working (3 regions)
- No Borderless Windowed mode — test in Windowed mode only

---

## Key Technical Decisions Already Made

| Decision | What was chosen | Why / Don't reverse without reading AD |
|---|---|---|
| Transparency for overlay highlight | `SetWindowRgn` | AD-24. WS_EX_LAYERED+LWA_COLORKEY fails on DWM |
| Win32 API calls | `ctypes` directly | `win32gui` lacks GDI32 functions like CreateRectRgn |
| HWND for Toplevel | `winfo_id()` directly | GetAncestor(GA_ROOT) returns wrong window for tkinter |
| Hide/show Toplevel | Move off-screen via geometry() | withdraw() recreates HWND, loses style bits |
| OCR engine | RapidOCR (ONNX) | AD-06. EasyOCR needs PyTorch, Tesseract needs binary |
| Game pack format | YAML folder convention | AD-08. No plugin system until 2+ packs existed |
| Region coordinates | Fractional 0.0–1.0 | AD-09. Survives resolution changes |
| Async bridge | Thread + queue | AD-10. tkinter not thread-safe |
| Settings storage | JSON in app data | AD-17. pydantic-settings is read-only |
| Window chrome | overrideredirect(True) | AD-18. Native titlebar irrelevant for overlay |
| RAG embedding | `ONNXMiniLM_L6_V2` (chromadb built-in) | AD-25. sentence-transformers pulls PyTorch (~2GB), violates AD-06 |
| RAG dep group | optional `[rag]` — chromadb only | AD-25. App runs with NullRagService when not installed |
| RAG injection point | OCR path only | No text query available on screenshot/placement paths |
| AI backend selection | Settings always wins over manifest `preferred_backend` | AD-26. Pack hint is logged only |
| ClaudeBackend JSON output | System prompt instruction, not native schema | AD-26. Claude has no `types.Schema` equivalent |
| Token tracking return type | `tuple[str, UsageStats]` from both Protocol methods | v0.7.3. Breaking change — both backends updated atomically |
| Footprint lookup | Keyword substring scan of advice text, longest match wins | AD-27. No extra AI call; graceful 1×1 fallback |
| RAG game_version type | Stored as `float` in Chroma metadata, queried as `float` | Chroma `$gte` requires numeric. String `"0.6"` caused silent RAG off. Re-ingest after fix. |
| AI call progress | `_start_progress_ticker()` updates canvas every 5s with elapsed time | Long calls (Gemini 3-4min on slow quota) were silent. Ticker stops on result/error. |

---

## Calibration Service — Known Quirks

Gemini returns coordinates in three inconsistent scales:
- `0.0–1.0` fractions (correct)
- `0–100` percentages (divide by 100)
- pixel coordinates (divide by img_w/img_h)

Scale is auto-detected by `max(x, y, w, h)` value:
- `> 100` → pixel coords
- `> 1.0` → percentages
- `≤ 1.0` → already correct

Gemini also invents different label names each run (`top_bar_resources`, `resource_bar_top`,
`top_resource_bar` for the same region). The calibration prompt lists canonical names to steer
it, but manual correction of `hud_regions_user.yaml` may still be needed.

Region labels in `hud_regions_user.yaml` must match `LABEL_CONFIGS` in `preprocessor.py`
for the correct OCR preprocessing config to be applied. Check after any calibration run.

## MainOverlay Structure (key for v0.8.0 UX work)

`views/main_overlay.py` — `MainOverlay(tk.Tk)` root window.

**Widget hierarchy (pack order matters):**
```
MainOverlay (tk.Tk)
├── _toolbar (tk.Frame, bg_header, pack TOP) — always visible
│   ├── LEFT: _slide_btn (◄), _collapse_btn (▲), _title_label, _status_label
│   └── RIGHT: _close_btn, _lock_btn, _settings_btn, _log_btn (optional)
└── _body (tk.Frame, bg_primary, pack BOTH+expand) — hidden when collapsed
    ├── _footer (tk.Frame, bg_footer, h=footer_height, pack BOTTOM first)
    │   ├── _hints_label (LEFT) — “F1 Adv │ F2 Place…”
    │   ├── _token_label (RIGHT, v0.7.3) — “↑1.2k ↓0.8k ~$0.001”, empty until first call
    │   └── _cooldown_label (RIGHT) — “Ready in Ns” / “✓ Ready”
    ├── _log_panel (LogPanel, pack BOTTOM, hidden by default)
    ├── _placement_strip (PlacementInputStrip, hidden by default)
    └── canvas (OverlayCanvas, pack BOTH+expand)
```

**Key public methods used by ViewModel / main.py:**
- `update_status(mode, source)` — toolbar status label
- `update_cooldown(text, fg)` — footer cooldown label
- `update_token_display(text)` — footer token label (v0.7.3)
- `show_placement_highlight(pixel_rect, cell_ref, monitor_rect, auto_dismiss_ms, footprint)`
- `clear_placement_highlight()`
- `toggle_placement_strip(suggestions)`
- `auto_expand_for_result()` — slides onscreen + expands if collapsed
- `set_calibration_service(service, game_id, api_key)`
- `set_claude_api_key(key)`
- `set_pack_loader(loader)`
- `set_settings_handler(handler)`
- `set_close_handler(handler)`
- `set_placement_handler(handler)`

**State flags:** `_offscreen: bool`, `_collapsed: bool`, `_click_through_active: bool`

**v0.8.0.1 SHIPPED — `FloatingAdviceWindow`:**
- `views/floating_advice_window.py` — `FloatingAdviceWindow(parent, theme)`
- Created in `MainOverlay.__init__` alongside `PlacementHighlightWindow`
- `MainOverlay.show_floating_advice(advice_text, timeout_seconds=12)` — public method
- Destroyed in `_on_close_click()`
- ViewModel `_on_result` checks `overlay._offscreen` + `settings.show_floating_advice_when_hidden`
  — routes to floating window or inline canvas accordingly
- Position: 8% from top, centered. 35% width × 28% height, min 340×180px
- withdraw()/deiconify() pattern (no HWND Win32 style tricks needed — normal Toplevel)
- Markdown rendering: standalone implementation (h2/h3/bullet/bold tags), does NOT
  import or reuse OverlayCanvas to avoid coupling
- `AppSettings.show_floating_advice_when_hidden: bool = True`
- `AppSettings.floating_advice_timeout_seconds: int = 12`
- Settings dialog: "Floating advice" toggle in General tab

**For v0.8.0.2 — Floating placement dialog:**
- When overlay is offscreen and F2 fires, show a centered `tk.Toplevel` dialog
- Larger than the inline `PlacementInputStrip`, full keyboard focus, Esc dismisses
- Reuses same history + quick-prompts data from ViewModel (`get_prompt_suggestions()`)
- No ViewModel changes needed — only view layer
- `MainOverlay` needs: `show_floating_placement_dialog(suggestions, on_submit)` method
- The on_submit callback is `viewmodel.trigger_placement` (already exists)
- `toggle_placement_strip()` should check `_offscreen` and show dialog instead of strip
  OR ViewModel checks `_offscreen` before calling `toggle_placement_strip`
- New file: `views/floating_placement_dialog.py`

---

## RAG Subsystem — How It Works (AD-25)

`core/rag/` subpackage. Three classes + factory:
- `RagService` — `typing.Protocol`, `@runtime_checkable`. `query(text, top_k, min_game_version) -> list[str]`, `is_available() -> bool`
- `NullRagService` — no-op. Zero extra imports. Returned when no collection or chromadb absent.
- `ChromaRagService` — loads persistent Chroma collection from `game_packs/<id>/rag/`. Deferred chromadb import. Uses `ONNXMiniLM_L6_V2` (chromadb built-in ONNX embedder, no PyTorch).
- `RagServiceFactory.for_game_pack(game_pack_path, collection_name)` — checks `rag/` folder exists + `collection_name` set + chromadb importable → `ChromaRagService`, else `NullRagService`.

**Wiring in `main.py`:**
```python
_active_manifest = pack_loader.load_manifest(settings.active_game_id)
_game_pack_path = pack_loader._packs_dir / settings.active_game_id
rag_service = RagServiceFactory.for_game_pack(
    game_pack_path=_game_pack_path,
    collection_name=_active_manifest.rag_collection_name,
)
viewmodel = AssistantViewModel(..., rag_service=rag_service)
```

**Injection in ViewModel (`_build_rag_context`):**
- Called on OCR advisor path only (combined OCR text used as query)
- Prepends `## Retrieved Knowledge\n- chunk...\n\n` to system prompt
- Returns `""` when RAG unavailable — callers never emit empty section
- Logs `rag=on (N chunks)` or `rag=off (reason)` per call

**Manifest fields per game pack:**
```yaml
rag_collection_name: timberborn_knowledge  # null = NullRagService
rag_top_k: 4                               # chunks per call, default 3
rag_min_game_version: "0.6"               # Chroma $gte filter on game_version metadata
```

**Knowledge base structure:**
```
game_packs/<id>/
├── knowledge/   # .md source files (human-readable, editable)
└── rag/         # Chroma binary (committed to repo)
```

**Ingestion CLI** (run after editing knowledge files):
```bash
uv sync --extra rag
uv run python tools/ingest_knowledge.py \
    --game-id timberborn \
    --source-dir game_packs/timberborn/knowledge \
    --game-version 0.6 --reset
```
Use `--reset` when editing existing files. Omit for incremental (new files only).

**⚠️ Re-ingestion required after RAG bug fix:**
The `game_version` metadata was stored as string in the original collections.
After the `ingest_knowledge.py` fix (stores as `float`), re-run ingestion with `--reset`:
```bash
uv run python tools/ingest_knowledge.py --game-id timberborn \
    --source-dir game_packs/timberborn/knowledge --game-version 0.6 --reset
uv run python tools/ingest_knowledge.py --game-id nebuchadnezzar \
    --source-dir game_packs/nebuchadnezzar/knowledge --game-version 1.0 --reset
```
Then commit the updated `rag/` binaries.

**Current collections:** Timberborn (`timberborn_knowledge`, 6 files), Nebuchadnezzar (`nebuchadnezzar_knowledge`, 6 files).

---

## Placement Highlight — How It Works (AD-24)

`PlacementHighlightWindow` in `views/placement_highlight.py`:
1. F2 placement query → Gemini returns `{"cell": "H5", "advice": "..."}` JSON
2. `cell_to_screen_pixels()` converts cell ref to `(x, y, w, h)` screen rect
3. `PlacementHighlightWindow.show()` is called with the pixel rect
4. A `tk.Toplevel` with `overrideredirect(True)` is positioned at the cell
5. `ctypes.windll.gdi32.CreateRectRgn` + `CombineRgn` creates hollow frame region
6. `ctypes.windll.user32.SetWindowRgn` clips the window to just the outline + label
7. `WS_EX_TRANSPARENT` (no WS_EX_LAYERED) makes the outline strip click-through
8. Window moves off-screen (not withdrawn) when cleared — preserves HWND and styles
9. Auto-dismisses after `placement_highlight_seconds` (default 8s)

---

## Prompts — Key Rules

Every `advisor_ocr.txt` and `advisor_screenshot.txt` must include:
> `NEVER ask the player for more information. If a region is missing or unclear,
> give your best advice based on whatever data is available.`

Every `placement.txt` must include:
> `IMPORTANT: The grid covers the ENTIRE screenshot including UI panels and non-game areas.
> Only reference cells that fall within the visible game map area.
> Describe the cell using visible in-game landmarks so the player can find it even
> if the cell highlight appears in the wrong screen position.`

Placement response format (JSON, enforced via `response_schema`):
```json
{"cell": "H5", "advice": "## Cell H5 — description\n- bullet 1\n- bullet 2"}
```

---

## Hotkey Format (pynput)

After v0.5.7 fix — correct pynput hotkey string format:
- Single printable char: `a`, `8`, `0` (NO angle brackets)
- Special keys: `<f1>`, `<f2>`, `<space>`, `<escape>`
- Combos: `<alt>+8`, `<ctrl>+<f1>`, `<shift>+a`

Old broken format (`<alt>+<8>`) would cause `<alt>` alone to trigger via pynput.
If a user reports "hotkey fires on modifier alone", check their `settings.json` for
`<X>+<Y>` where Y is a printable char — they need to rebind in Settings.

`HotkeyManager.register()` rejects modifier-only strings (e.g. `<alt>`) with a warning.

---

## macOS / Linux Status

Platform-specific code follows fail-open pattern. Current state:
- **Click-through:** Windows only (pywin32). macOS: pyobjc stub. Linux: no-op.
- **PlacementHighlightWindow:** Windows: SetWindowRgn (working). Others: alpha=0.75 fallback.
- **Focus check:** Windows only (pywin32 GetForegroundWindow). Others: always returns True.
- **Improvement path:** v0.7.0 milestone — NSWindow APIs (macOS), XShapeCombineRectangles (X11).

Developer works remotely on MacBook but GASSI runs and is tested on Windows PC.

---

## Session Start Protocol

**Paste this into the new chat to begin:**

> Read these files in order before we start:
> 1. `F:\__STORAGE\__PROJECTS_F\proj-gassi\proj_gassi2\docs\session_handoff.md`
> 2. `F:\__STORAGE\__PROJECTS_F\proj-gassi\proj_gassi2\TODO.md`
> 3. `F:\__STORAGE\__PROJECTS_F\proj-gassi\proj_gassi2\CHANGELOG.md`
> 4. `F:\__STORAGE\__PROJECTS_F\proj-gassi\proj_gassi2\docs\architecture.md`
> Then tell me what's missing before we start.

**Read on demand only (not at session start):**
- `docs/adding_game_pack.md` — only when adding a new game pack
- `docs/v1_scope.md` — only when updating known limitations or scope
- **Source files** — read only the specific files the task touches. Never edit from memory.

**Keep this file updated** as the project evolves:
- After any major architectural decision (new AD added) — summarise it here
- After a milestone is complete — update the roadmap summary section
- After a new "lesson learned" — add it to the relevant section
- After a new game pack reaches tested status — update the game packs section

No version bump needed — this is a living doc, not a changelog entry.
