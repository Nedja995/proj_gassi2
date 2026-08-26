# v1 Scope — Feature Specification

This document tracks what was in scope for v1 and the current state of each feature.
Updated to reflect actual shipped state as of v0.4.4.

---

## Target Games

- **Timberborn** — primary pack, fully tested
- **Nebuchadnezzar** — second pack, prompts and OCR configs complete, live testing pending (v0.4.5)

---

## Feature 1: Advisor Mode

**Trigger:** `F1` (one-shot per press, not polling)

**Input sources** (switch via `Shift+F1`):
- **OCR:** RapidOCR on pre-calibrated HUD region crops → extracted text → Gemini text-only call
- **Screenshot:** full-screen capture → Gemini multimodal call

**Confidence fallback:** if OCR confidence < threshold (default 0.6), automatically uses screenshot.

**Output:** advice text displayed on overlay canvas with markdown rendering (`##`, `- bullets`, `**bold**`).

**HUD regions:** pre-calibrated in `manifest.yaml` as fractional coordinates. User calibration
via CalibrationService writes to `hud_regions_user.yaml` (never overwrites manifest defaults).

---

## Feature 2: Placement Mode

**Trigger:** `F2` (opens inline input strip in overlay)

**Input:** full-screen capture + player's typed question from `PlacementInputStrip`.

**Grid overlay (v0.3.1+):** coordinate grid (A–Z columns, 1–N rows) drawn on screenshot before
submission. Gemini returns structured JSON `{"cell": "D5", "advice": "..."}` via `response_schema`.

**Cell highlight (v0.3.2+):** yellow outline box drawn over the target cell on the game screen
via `PlacementHighlightWindow` (`SetWindowRgn`, Windows) or alpha fallback (macOS/Linux).
Auto-dismisses after `placement_highlight_seconds` (default 8s).

**Prompt history:** last 5 queries persisted to `settings.json`. Quick-prompts from manifest
shown in dropdown.

---

## Feature 3: Settings

**Access:** ⚙ gear icon in toolbar.

**Configurable:**
- Active game pack (dropdown — all installed packs)
- Theme (dark / midnight / forest)
- Cooldown interval (5–60s)
- AI model (fetched live from Gemini API)
- Default advisor input source (OCR / Screenshot)
- Grid overlay toggle + dimensions
- All hotkeys (key-capture widget)

**Persistence:** `settings.json` in OS app data dir. Game switch shows restart notice in overlay.

---

## Feature 4: Debug Tools

- `F4` — saves last captured frame as timestamped PNG to `<app data>/debug_frames/` (auto-prune 50 files)
- `⌨` toolbar button — collapsible log panel (last 200 lines, colour-coded by level)
- `prompt_iteration.py` CLI — test prompts against saved frames without running the full app

---

## Feature 5: Auto-Calibration

**Access:** Settings → Calibrate HUD (shown when CalibrationService is wired).

Sends full screenshot to Gemini with `response_schema`, detects HUD regions, validates each
with RapidOCR, writes `hud_regions_user.yaml`. Clear user calibration button reverts to manifest defaults.

---

## Feature 6: RAG Knowledge Retrieval

**Shipped:** v0.6.1–v0.6.6

Game-specific knowledge is embedded into a local Chroma vector database and retrieved
at query time. Retrieved chunks are prepended to the system prompt on every OCR advisor
call, giving the AI access to formula-level, wiki-sourced knowledge without bloating
the static prompt.

**Architecture:**
- `RagService` Protocol — `ChromaRagService` (Chroma + ONNXMiniLM_L6_V2 ONNX embeddings,
  no PyTorch) and `NullRagService` (no-op fallback when collection absent)
- `tools/ingest_knowledge.py` — CLI for chunking, embedding, and persisting collections
- Per-game `knowledge/` folder (human-readable `.md` sources) and `rag/` folder
  (compiled Chroma binary, committed to repo)
- Optional `[rag]` dep group (`chromadb` only — `onnxruntime` reused from RapidOCR)

**Game packs with RAG:**
- Timberborn — 6 knowledge files, `timberborn_knowledge` collection
- Nebuchadnezzar — 6 knowledge files, `nebuchadnezzar_knowledge` collection

**Injection:** OCR advisor path only (OCR text used as query). Screenshot path skipped
(no text query available). `rag_top_k` and `rag_min_game_version` configurable per pack.

---

## Feature 7: Multi-Backend AI

**Shipped:** v0.7.1–v0.7.2

Swappable AI backends via `AiBackend` Protocol. Settings dialog selects provider;
factory constructs the correct backend at startup.

- **Gemini** (default) — `google-genai` SDK, live model list fetch, `response_schema` for placement
- **Claude** (optional `[claude]` dep group) — `anthropic>=0.40`, static model list,
  JSON output via prompt instruction
- **Backend factory** (`core/ai/factory.py`) — single construction point, keyring lookup per provider
- **Token/cost tracking** (v0.7.3) — `UsageStats` per call, session totals in overlay footer
- **Building footprints** (v0.7.4) — manifest registry, multi-cell highlight on placement

---

## Explicitly Out of Scope (still deferred)

- Arrow rendering over game screen
- Tutorial overlay (highlight UI elements, step-through instructions)
- Local SLM backends (Ollama/Moondream2) — v0.9.0 post-beta
- Groq / Together AI cloud providers — v0.9.0 post-beta
- Native window detection (OS-level window handle lookup) — v0.9.1
- Wayland capture support — v0.9.1
- TTS voice readout — v0.8.1 (optional, post-beta)
- Automated in-game clicks/keypresses (out of scope permanently — anti-cheat posture)
- Monetization / app store distribution — post v0.8.1

---

## Known Limitations (current)

- Overlay must be manually positioned over the game window (no native window detection yet)
- HUD regions calibrated per game pack — mods that change HUD layout require recalibration
- Full resource panel visibility requires the player to open panels before triggering Advisor
- Game pack switch requires GASSI restart to take effect
- AI backend / provider switch requires GASSI restart to take effect
- Wayland desktops (SteamOS/Steam Deck) are not supported
- macOS click-through and transparency fallback to alpha (no `SetWindowRgn` equivalent yet)
- `resource_bar` OCR in Nebuchadnezzar unvalidated — small digits may need preprocessor tuning
- Fullscreen exclusive mode (DirectX/OpenGL) bypasses DWM — GASSI overlay is not visible.
  Use Borderless Windowed mode in game settings. Games without that option (e.g. Nebuchadnezzar)
  must be run in Windowed mode for GASSI to work.
- When overlay is offscreen, F1/F2 restore the full overlay — floating windows not yet
  implemented (v0.8.0).
- Claude `response_schema` not enforced natively — placement JSON output relies on prompt
  instruction; fallback parser handles malformed responses gracefully.
