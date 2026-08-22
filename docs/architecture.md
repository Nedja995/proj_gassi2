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

## AD-16: Python 3.12 pinned

**Decision:** Pin to Python `>=3.12,<3.13` (stable release).

**Rationale:** 3.12 is the current stable with mature ecosystem support. Avoids 3.13+ breaking changes in dependencies (especially compiled ones like ONNX runtime, mss, numpy). Upgrade deliberately after verifying full dep compatibility.
