# GASSI — Game-specific AI Strategy Screen Inspector

A lightweight, cross-platform desktop overlay that assists players in real-time with complex
strategy and colony-sim games. Currently supports **Timberborn** and **Nebuchadnezzar**.

**No game memory reading. No process injection. Pure computer vision + screen overlay.**

---

## How It Works

GASSI captures your game screen, extracts information via local OCR or direct screenshot,
and sends it to an AI model for strategic advice — displayed as a translucent, always-on-top
overlay on top of your game. Supports Google Gemini and Anthropic Claude backends.

---

## Features (v0.7.4)

### Advisor Mode (`F1`)

On-demand capture of pre-calibrated HUD regions. Two input sources (toggle with `Shift+F1`):

- **OCR** — local text extraction via RapidOCR → text sent to AI backend (low cost)
- **Screenshot** — HUD image sent directly to AI backend (richer context, fallback)

Automatic confidence-gated fallback: if OCR confidence drops below threshold, that cycle
switches to screenshot automatically.

### Placement Mode (`F2`)

On-demand: captures full game window + your typed question → Gemini returns spatial advice.

**Grid overlay** (enabled by default): a coordinate grid (A–L columns, 1–8 rows) is drawn on
the screenshot before sending to the AI backend. The model returns a specific cell reference
(e.g. `H7`) alongside markdown advice. Multi-cell building footprints are highlighted correctly
based on the `building_footprints` registry in each game pack's manifest.

**Cell highlight**: a yellow outline box appears over the target cell on the game screen for
8 seconds (configurable). The cell interior stays fully visible — only the outline is drawn.
Click-through enabled; the highlight never blocks game input.

### Overlay Controls

| Hotkey | Action |
|--------|--------|
| `F1` | Advisor query (one-shot) |
| `Shift+F1` | Switch Advisor source (OCR ↔ Screenshot) |
| `F2` | Placement query (full screen + grid overlay + question) |
| `F3` | Toggle click-through lock |
| `F4` | Save last captured frame to debug folder |
| `⚙` (toolbar) | Open settings dialog |
| `◀` (toolbar) | Slide overlay off-screen (pull-back tab remains) |
| `▲` (toolbar) | Collapse to toolbar-only strip |
| `◢` (corner) | Drag to resize overlay |

### Settings Dialog (`⚙`)

- Select AI backend (Gemini / Claude) and model
- Rebind all hotkeys via key-capture widget
- Switch theme (dark / midnight / forest)
- Adjust cooldown interval (5–60s)
- Select default advisor input source (OCR / Screenshot)
- Toggle grid overlay for placement mode
- Settings persist across sessions (`settings.json` in OS app data dir)

Session token usage and estimated cost shown in the overlay footer after each AI call.

### RAG Knowledge Retrieval

Game-specific knowledge (formulas, building costs, ratios, patch notes) is embedded into
a local vector database and retrieved at query time. Relevant chunks are injected into the
AI prompt automatically on every OCR advisor call — giving deeper, formula-level advice
without inflating the static prompt size.

- Per-game knowledge base: human-readable `.md` source files in `game_packs/<id>/knowledge/`
- Pre-compiled [Chroma](https://www.trychroma.com/) vector DB committed to repo — no user
  ingestion required
- Uses chromadb's built-in ONNX embedding (`ONNXMiniLM_L6_V2`) — no PyTorch dependency
- Optional: requires `[rag]` dep group (`uv sync --extra rag`). Falls back silently to
  static prompts when not installed.

### Debug Tools

- `F4` saves last captured frame as timestamped PNG to `<app data>/debug_frames/`
- `⌨` toolbar button toggles collapsible log viewer panel (last 200 log lines, colour-coded)
- Prompt iteration CLI: `tests/prompt_iteration.py` — test prompts against saved frames without
  running the full app

---

## Supported Games

| Game | Pack Version | Status |
|------|-------------|--------|
| Timberborn | 0.6 | Active, RAG enabled |
| Nebuchadnezzar | 1.0 | Active, RAG enabled |

---

## Requirements

- Python 3.12.x (managed via [uv](https://docs.astral.sh/uv/))
- Google Gemini API key (or Anthropic Claude API key — one is required)
- Windows / macOS / Linux (X11). Wayland not yet supported.

---

## Installation

```bash
# Clone
git clone <repo-url>
cd proj_gassi2

# Create venv and install
uv venv --python 3.12
uv pip install -e ".[dev]"

# Windows: also install pywin32 for click-through overlay
uv pip install -e ".[dev,windows]"

# Optional: install RAG support (Chroma vector DB for game knowledge retrieval)
# Required to use the knowledge base — falls back to static prompts without it
uv sync --extra rag
# or all: uv sync --extra windows --extra rag --extra claude

# Store API keys in OS keyring
uv run python -c "import keyring; keyring.set_password('gassi', 'gemini_api_key', 'YOUR_GEMINI_KEY')"
# Optional: Claude backend
uv run python -c "import keyring; keyring.set_password('gassi', 'claude_api_key', 'YOUR_CLAUDE_KEY')"
```

---

## Usage

```bash
# Activate venv first (recommended for daily use)
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# Run
gassi

# Or without activating
uv run gassi
```

Position the overlay over your game window. Use hotkeys listed above.

---

## Project Structure

```
src/gassi/
├── main.py                      # Entry point, dependency wiring
├── models/
│   ├── config.py                # AppSettings (pydantic-settings + JSON persistence)
│   ├── enums.py                 # AssistantMode, AdvisorInputSource, AiProvider
│   ├── game_pack.py             # GamePackManifest, HudRegion
│   └── results.py               # AdvisorResult, PlacementResult, OcrResult, UsageStats
├── core/
│   ├── ai/
│   │   ├── protocol.py          # AiBackend Protocol
│   │   ├── factory.py           # Backend factory (build_ai_backend, get_api_key)
│   │   ├── gemini_backend.py    # Gemini implementation
│   │   └── claude_backend.py    # Claude implementation (optional [claude] extras)
│   ├── capture/
│   │   ├── protocol.py          # CaptureBackend, CaptureRegionProvider Protocols
│   │   ├── mss_backend.py       # mss screen capture
│   │   └── region_provider.py   # Overlay-anchored region provider (v1)
│   ├── ocr/
│   │   └── rapid_ocr_engine.py  # RapidOCR wrapper
│   ├── overlay/
│   │   └── overlay_canvas.py    # Layered canvas + markdown renderer
│   ├── async_bridge.py          # asyncio ↔ tkinter bridge (thread + queue)
│   ├── debug_manager.py         # Debug frame save, auto-prune
│   ├── game_pack_loader.py      # YAML manifest + prompt loader
│   ├── hotkey_manager.py        # pynput global hotkeys
│   ├── log_handler.py           # In-memory logging handler (feeds log panel)
│   ├── settings_manager.py      # JSON settings persistence
│   └── theme/
│       └── theme.py             # Theme model + 3 presets
├── viewmodels/
│   └── assistant_viewmodel.py   # Mode FSM, capture dispatch, cooldown, debug
└── views/
    ├── log_panel.py             # Collapsible log viewer panel
    ├── main_overlay.py          # Root overlay window (toolbar, canvas, footer)
    ├── placement_highlight.py   # Cell highlight window (SetWindowRgn, v0.3.2)
    ├── placement_strip.py       # Inline placement input strip (F2)
    └── settings_dialog.py       # Settings dialog (hotkeys + general tabs)

game_packs/
├── timberborn/
│   ├── manifest.yaml            # HUD regions, footprints, RAG config
│   ├── knowledge/               # .md source files for RAG ingestion
│   ├── rag/                     # Chroma vector DB (committed)
│   └── prompts/
│       ├── advisor_ocr.txt
│       ├── advisor_screenshot.txt
│       └── placement.txt
└── nebuchadnezzar/
    ├── manifest.yaml
    ├── knowledge/
    ├── rag/
    └── prompts/
        ├── advisor_ocr.txt
        ├── advisor_screenshot.txt
        └── placement.txt

docs/
├── architecture.md              # Architecture Decision Records (AD-01 – AD-27)
├── adding_game_pack.md          # Guide: adding support for a new game
├── session_handoff.md           # Session context for new chats
└── v1_scope.md                  # Feature scope and known limitations

tests/
├── conftest.py
├── prompt_iteration.py          # CLI tool: test prompts against screenshots
├── test_game_pack_loader.py
└── test_models.py
```

---

## Architecture

- **MVVM pattern** — Models (Pydantic data) → ViewModel (logic/FSM) → Views (tkinter)
- **Protocol abstractions** — `AiBackend`, `CaptureBackend`, `CaptureRegionProvider` — swap implementations without touching ViewModel
- **Async bridge** — dedicated asyncio thread + queue → tkinter `after()` polling. AI calls never block the UI.
- **Game packs** — folder convention: `game_packs/<id>/manifest.yaml` + `prompts/`. No plugin system — just add a folder. See `docs/adding_game_pack.md`.
- **Markdown renderer** — `OverlayCanvas` renders `## headings`, `- bullets`, and `**bold**` natively.
- **Theme system** — all visual constants in `Theme` model, 3 presets, selectable via settings dialog.
- **Persistent settings** — JSON in OS app data dir, merged with env var overrides at startup.

See `docs/architecture.md` for full decision records.

---

## Development

```bash
# Tests
uv run pytest -v

# Lint
uv run ruff check src/ tests/

# Type check
uv run mypy src/

# Prompt iteration (no full app required)
uv run python tests/prompt_iteration.py --mode advisor_screenshot --image path/to/frame.png
uv run python tests/prompt_iteration.py --mode advisor_ocr --hud "[top_bar]: Day 3, Food: 12"
```

---

## Adding a New Game

See [`docs/adding_game_pack.md`](docs/adding_game_pack.md) for the complete guide covering:
folder structure, manifest calibration, prompt authoring, and early/mid/late game stage design.

---

## Market Position

GASSI wins by **hyper-specialization** — deep, formula-level knowledge for individual games —
where generalist tools (NVIDIA G-Assist, Steam Gaming Copilot) give only surface advice.
Multiple AI backends (Gemini, Claude) with more providers planned post-beta (Groq, Together AI,
local SLM via Ollama/Moondream2).

---

## License

MIT
