# Architecture Decisions Record

This document captures the key architecture decisions made for GASSI and the rationale behind each.

## AD-01: MVVM over MVC

**Decision:** Use Model-View-ViewModel pattern.

**Rationale:** ViewModel owns the mode state machine and exposes commands. Views (tkinter) bind to ViewModel state via callbacks. Models are pure Pydantic data. This keeps AI call dispatch, polling logic, and mode transitions testable without a running UI.

## AD-02: Protocol-based abstractions for all backends

**Decision:** `AiBackend`, `CaptureBackend`, `CaptureRegionProvider` are all `typing.Protocol` interfaces.

**Rationale:** v1 ships with exactly one implementation each (Gemini, mss, overlay-anchored). But swapping backends (Claude, Ollama, PipeWire capture, native window detection) must not require touching ViewModel code. Protocols enforce this contract without ABC inheritance overhead.

## AD-03: tkinter over PyQt6/PySide6

**Decision:** Use stdlib tkinter + ttk with per-OS native hooks for transparency/click-through.

**Rationale:** v1 has no local ML runtime (no PyTorch). Qt's 80-150MB footprint becomes the largest fixed cost for no proportional benefit. Tkinter is zero-install. Platform-specific transparency (pywin32, pyobjc, python-xlib) is more code but less weight. If overlay reliability becomes a maintenance burden, PySide6 (LGPL) is the fallback — not PyQt6 (GPL, requires commercial license if monetizing).

## AD-04: mss for screen capture

**Decision:** Use `mss` library, not OpenCV or dxcam.

**Rationale:** Pure Python, ~60fps, minimal CPU, cross-platform (Windows/macOS/X11). OpenCV's VideoCapture is heavier and designed for video streams, not screen grabs. dxcam is Windows-only. Wayland (PipeWire/portal) is a known gap — abstracted behind `CaptureBackend` Protocol for future implementation.

## AD-05: Overlay-anchored region detection (v1)

**Decision:** Derive capture rect from the overlay window's own screen geometry. No OS-level window enumeration.

**Rationale:** Removes pywin32/pyobjc/Xlib window-lookup from v1 critical path. User manually positions overlay over the game. `CaptureRegionProvider` Protocol allows v2's `NativeWindowRegionProvider` to drop in without ViewModel changes.

## AD-06: RapidOCR over EasyOCR/Tesseract

**Decision:** Use RapidOCR (ONNX runtime) for local text extraction.

**Rationale:** EasyOCR requires ~2GB PyTorch — contradicts low-footprint goal. Tesseract needs a bundled system binary per OS (PyInstaller packaging pain) and has poor accuracy on stylized game fonts. RapidOCR is pip-installable, ONNX CPU runtime (~100-150MB with models), no CUDA, cross-platform, better on anti-aliased text.

## AD-07: Static system prompts, no RAG in v1

**Decision:** Embed game knowledge directly in prompt text files. No Chroma/embeddings pipeline.

**Rationale:** Single game (Timberborn) — the knowledge fits comfortably in a system prompt. Removes chromadb + sentence-transformers from v1 deps (real footprint win) and eliminates an entire subsystem (ingestion, chunking, persistence). `rag_collection_name` field reserved in manifest for v2.

## AD-08: Game packs as folder convention, not a plugin system

**Decision:** `game_packs/<game_id>/manifest.yaml` + prompts folder. Plain pydantic parse at startup. No dynamic loader, no plugin registry, no entry-point discovery.

**Rationale:** N=1 game. Plugin architecture would be speculative generality — we don't know what's actually game-specific vs. core until game pack #2 is built. Folder convention separates data from code without committing to an API contract.

## AD-09: Fractional HUD region coordinates

**Decision:** Store HUD regions as `x_pct`, `y_pct`, `width_pct`, `height_pct` (0.0-1.0) relative to the captured window.

**Rationale:** Survives resolution changes, UI scale changes, and window resizing without recalibration. Absolute pixel coordinates would break across user configurations.

## AD-10: Async bridge via thread + queue

**Decision:** Dedicated asyncio event loop in a daemon thread. Results drain into tkinter via `queue.Queue` + `root.after()` polling at 50ms intervals.

**Rationale:** tkinter widgets aren't thread-safe — async results can't touch UI directly from a worker thread. The thread+queue pattern is more robust under real network latency than manual event-loop stepping inside `after()`, which can jank the UI on slow Gemini calls.

## AD-11: API key via OS keyring, not config files

**Decision:** Use `keyring` library to store/retrieve Gemini API key from the OS credential store.

**Rationale:** No plaintext secrets in config files, env files, or source. Cross-platform (Windows Credential Locker, macOS Keychain, Linux SecretService). Enforced at v1, not retrofitted later.

## AD-12: Pre-calibrated HUD regions, not user-drawn (v1)

**Decision:** Ship `hud_regions.yaml` as part of the game pack, pre-calibrated by the developer. No click-drag calibration UI in v1.

**Rationale:** Game-specific assistant model means the developer knows the game's HUD layout. Removes a UI feature from v1 scope. If future packs need user calibration (modded UIs), it can be added without changing the data model.

## AD-13: Layered OverlayCanvas (scaffolded for v2)

**Decision:** Canvas uses a `_layers` dict with named layers (text, highlights, arrows, overlays). v1 uses only the text layer.

**Rationale:** v2 needs independent layer control (clear tutorials without wiping advice, draw arrows without redrawing all text). Building the layer structure now costs nothing; retrofitting it later means tracking item IDs manually or full-canvas redraws.

## AD-14: PlacementResult carries v2 fields now

**Decision:** `PlacementResult` includes `target_direction`, `target_offset_pct`, `confidence` — all optional, unpopulated in v1.

**Rationale:** v1 returns free-text advice. v2's grid/arrow system will populate these fields. Adding them now means the model shape doesn't change between versions — only the prompt and response parsing do.

## AD-15: No game memory reading, ever

**Decision:** Pure computer vision (screen capture) and screen overlays. No process injection, no memory reading, no automated in-game clicks/keypresses.

**Rationale:** Anti-cheat compliance. Even for single-player games without anti-cheat (Timberborn, RimWorld), this stance is maintained as a product principle — especially since online multiplayer game support is planned for future versions.

## AD-16: Python 3.12 pinned, uv as package manager

**Decision:** Pin to Python `>=3.12,<3.13` (stable release). Use `uv` (Astral) for venv creation and dependency management.

**Rationale:** 3.12 is the current stable with mature ecosystem support. Avoids 3.13+ breaking changes in dependencies (especially compiled ones like ONNX runtime, mss, numpy). `uv` chosen over Poetry because (a) it was already installed on the dev machine managing Python, (b) faster installs/resolution, (c) simpler mental model (no separate shell/plugin ecosystem), (d) standard PEP 621 `pyproject.toml` with no tool-specific lock-in. Hatchling as build backend — lightweight, standard-compliant.

## AD-17: Persistent settings via JSON + pydantic-settings merge

**Decision:** User settings saved to a JSON file in the OS app data directory (`%LOCALAPPDATA%\gassi\settings.json` on Windows). At startup, saved JSON is loaded first, then merged into `AppSettings` (pydantic-settings) which also reads `GASSI_*` env vars. Env vars override saved settings.

**Rationale:** pydantic-settings is read-only from env vars — it has no write-back mechanism. A runtime settings dialog needs persistence. JSON was chosen over YAML/TOML because it requires no additional dependency (json is stdlib), the config is flat key-value pairs (no nesting), and human-editability is not a primary concern (the settings dialog is the UI). The merge order (JSON → env vars → defaults) preserves the escape hatch of env var overrides for CI/testing.

## AD-18: Custom frameless window with overrideredirect

**Decision:** Use `overrideredirect(True)` to remove the native OS titlebar entirely. All window chrome (title, drag, close, collapse, settings) is custom tkinter.

**Rationale:** The overlay needs a compact, themed toolbar that blends with the game. Native titlebars waste vertical space, can't be themed, and their minimize/maximize buttons are irrelevant for an overlay. Trade-off: custom drag handling, custom close button, and `withdraw()`/`deiconify()` instead of native minimize (since `overrideredirect` windows don't participate in the OS window manager's minimize/restore).

## AD-19: Settings dialog over config-file-only

**Decision:** Build a full settings dialog (gear icon → tabbed window) rather than config-file-only or env-var-only settings.

**Rationale:** The hotkey conflict with Timberborn (F1/F2 are used by the game) made configurable hotkeys a blocking usability issue. A config file would work but requires the user to know pynput's key string format, find the file, edit it, and restart. The dialog with a key-capture widget ("press Set, then press your key") is the correct UX for a desktop app. Once the dialog exists, adding theme picker, cooldown slider, and model selector is marginal cost.

## AD-20: In-memory log handler, not file-based, for overlay log panel

**Decision:** `OverlayLogHandler` is a `logging.Handler` subclass that buffers formatted records in a `collections.deque(maxlen=N)`. The overlay log panel polls this buffer. No file I/O path is involved for the in-overlay display.

**Rationale:** A file-based approach (`logging.FileHandler` + tail) introduces filesystem polling, file handles, and OS-specific path concerns. The deque is zero-cost for writes, constant memory (maxlen caps it), and produces no I/O during normal operation — which matters for a gaming overlay running alongside a GPU-bound game. The `OverlayLogHandler` also doubles as the source for debug inspection without requiring the user to find a log file. Actual log file output is still available by attaching a `FileHandler` separately (future option under v0.6.0 distribution).

## AD-21: Debug frames co-located with settings in the config directory

**Decision:** Debug frame PNGs are saved to `<config_dir>/debug_frames/` — same root as `settings.json` (e.g. `%LOCALAPPDATA%\gassi\debug_frames\` on Windows). Auto-pruned to 50 files (oldest first).

**Rationale:** Using the OS app data directory keeps debug output off the user's desktop and out of the project repo. Co-locating with settings means `_get_config_dir()` from `settings_manager` is the single source for the app's writable directory — no new path logic. The 50-frame cap prevents unbounded disk growth during active debugging sessions; frames are timestamped so the user can correlate them with log output. The ViewModel stores the frame reference immediately after every capture so F4 always reflects the most recent API submission, regardless of source.

## AD-24: Placement highlight uses SetWindowRgn, not WS_EX_LAYERED / -transparentcolor

**Decision:** `PlacementHighlightWindow` (`views/placement_highlight.py`) clips the window to a hollow frame region (outer rect minus inner rect, plus label rect) using `SetWindowRgn`. The cell interior is outside the window region — the OS never renders those pixels and the game shows through completely. `WS_EX_TRANSPARENT` (without `WS_EX_LAYERED`) provides click-through on the visible outline strip. Non-Windows falls back to `wm_attributes("-alpha", 0.75)` with a small semi-transparent window.

**Rationale:** `WS_EX_LAYERED` + `SetLayeredWindowAttributes(LWA_COLORKEY)` + tkinter Canvas (GDI child window) is unreliable on Windows 10/11 with DWM compositing — the color key is not composited correctly and the window renders as a solid near-black rectangle regardless of ordering or timing of Win32 calls. `SetWindowRgn` avoids layered windows entirely: it is a pure hit-test and paint-clip operation that works correctly on all Windows versions with DWM. The HWND is never destroyed between calls (moved off-screen instead of withdrawn) to avoid region and style state being reset.

## AD-23: Grid overlay drawn on frame pre-submission; canvas bounding box deferred to v0.3.2

**Decision:** In v0.3.1, the coordinate grid is drawn directly onto the captured frame (as a BGR image annotation via OpenCV) before that frame is sent to Gemini. Gemini returns a structured JSON response (`response_schema`) with a `cell` reference and `advice` text. The cell reference is validated and converted to screen pixel coordinates via `cell_to_screen_pixels()`, but no canvas bounding box is rendered — the cell reference is appended to the advice text instead.

**Rationale:** Rendering a canvas overlay on top of the tkinter `Text` widget requires placing a `tk.Canvas` above it using `place()` geometry. On Windows, canvas backgrounds are not truly transparent without `WS_EX_LAYERED` hacks, and this conflicts with the existing click-through implementation (`WS_EX_TRANSPARENT` on the same HWND). The correct solution — a separate always-on-top transparent `Toplevel` canvas window — is a non-trivial architecture change that is better justified when tutorial overlays (v0.3.2) need the same infrastructure. Doing it in v0.3.1 would create half-solved technical debt. The v0.3.1 approach validates the full structured response pipeline (`response_schema`, cell parsing, pixel conversion) and keeps the interface clean for v0.3.2 to drop canvas rendering into without refactoring.

## AD-22: Auto-calibration uses response_schema + OCR validation, writes separate user file

**Decision:** `CalibrationService` sends a full screenshot to Gemini with `response_schema` enforcing a structured JSON response (`{regions: [{label, x_pct, y_pct, width_pct, height_pct}]}`). Each returned region is immediately validated by running RapidOCR on the crop and checking confidence against threshold. Accepted regions are written to `game_packs/<id>/hud_regions_user.yaml`. `GamePackLoader` checks for this file first and falls back to `manifest.yaml` if absent.

**Rationale:** `response_schema` makes the Gemini response deterministic and directly parseable — no regex or free-text parsing of coordinates. The immediate OCR validation step catches hallucinated regions (Gemini returning a bounding box that covers map terrain instead of HUD text) before they corrupt the working region set. Keeping user calibration in a separate file means the developer-authored `manifest.yaml` defaults are never overwritten by AI output, and clearing calibration is a single file delete. The `GamePackLoader` override pattern means the rest of the system (ViewModel, OCR pipeline) is completely unaware of whether regions came from manual or auto-calibration.
