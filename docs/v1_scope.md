# v1 Scope — Feature Specification

## Target Game

Timberborn (single game pack, vanilla UI only)

## Feature 1: Advisor Mode (periodic polling)

**Trigger:** `F1` toggle on/off

**Input sources** (switch via `Shift+F1`):

- **OCR:** RapidOCR on pre-calibrated HUD region crops → extracted text → Gemini text-only call
- **Screenshot:** same cropped HUD region sent as image → Gemini multimodal call

**Confidence fallback:** if OCR confidence < threshold (default 0.6), that poll cycle automatically uses screenshot source instead.

**Output:** both sources resolve to `AdvisorResult` → advice text displayed on overlay canvas.

**Polling:** configurable interval (default 5s). API error triggers backoff (2s exponential) then cooldown (30s pause with HUD message).

**HUD regions:** pre-calibrated in `manifest.yaml` as fractional coordinates. Developer-authored, not user-drawn.

## Feature 2: Placement Mode (on-demand)

**Trigger:** `F2` (one-shot)

**Input:** full game window capture + user prompt (v1: hardcoded test prompt; TODO: input dialog)

**Output:** free-text spatial advice referencing visible landmarks/directions. No grid coordinates, no bounding boxes, no arrows.

**v2 reserved fields:** `target_direction`, `target_offset_pct`, `confidence` in `PlacementResult` — unpopulated in v1.

## Explicitly Out of Scope (v1)

- Grid overlay / coordinate system for placement
- Arrow/bounding-box rendering
- Tutorial overlay (highlight UI elements, step-through instructions)
- RAG pipeline (Chroma, embeddings, vector search)
- Claude or Ollama backends
- Native window detection (OS-level window handle lookup)
- Wayland capture support
- TTS voice readout
- User-drawn HUD region calibration
- Automated in-game clicks/keypresses
- Monetization / app store distribution
- Multi-game support (only Timberborn pack ships)

## Known Limitations

- Overlay must be manually positioned over the game window
- HUD regions calibrated for vanilla Timberborn UI only — mods that change HUD layout will break OCR
- Full resource panel visibility requires the player to open panels manually before triggering Advisor
- Placement advice is directional/landmark-based, not coordinate-precise
- Wayland desktops (including SteamOS/Steam Deck) are not supported
