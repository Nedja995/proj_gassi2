# GASSI — Game-specific AI Strategy Screen Inspector

A lightweight, cross-platform desktop overlay that assists players in real-time with complex strategy and colony-sim games. Currently supports **Timberborn**.

## How It Works

GASSI captures your game screen, extracts information via local OCR or direct screenshot, and sends it to an AI model (Google Gemini) for strategic advice — displayed as a translucent overlay on top of your game.

**No game memory reading. No process injection. Pure computer vision + screen overlay.**

## Features (v0.1.0)

### Advisor Mode (`F1`)
Periodic polling of pre-calibrated HUD regions. Two input sources (toggle with `Shift+F1`):
- **OCR** — local text extraction via RapidOCR, sends text to Gemini (cheapest)
- **Screenshot** — sends cropped HUD image directly to Gemini (fallback / richer context)

Automatic confidence-gated fallback: if OCR confidence drops below threshold, that cycle uses screenshot instead.

### Placement Mode (`F2`)
On-demand: captures full game window + your typed question → Gemini returns spatial advice using visible landmarks and directions.

## Supported Games

| Game | Pack Version | Status |
|------|-------------|--------|
| Timberborn | 0.6 | Active |

## Requirements

- Python 3.12.x (managed via [uv](https://docs.astral.sh/uv/))
- Google Gemini API key
- Windows / macOS / Linux (X11). Wayland support is planned.

## Installation

```bash
# Clone
git clone <repo-url>
cd proj_gassi2

# Create venv and install all dependencies (including dev)
uv venv --python 3.12
uv pip install -e ".[dev]"

# On Windows, also install pywin32 for click-through overlay
uv pip install -e ".[dev,windows]"

# Store your Gemini API key in OS keyring (requires activated venv)
uv run python -c "import keyring; keyring.set_password('gassi', 'gemini_api_key', 'YOUR_API_KEY')"
```

## Usage

```bash
# Activate venv first
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# Run
gassi

# Or without activating
uv run gassi
```

Position the overlay window over your game. Hotkeys:
- `F1` — Toggle Advisor mode (periodic polling)
- `Shift+F1` — Switch Advisor input source (OCR ↔ Screenshot)
- `F2` — Placement query (one-shot screenshot + question)

## Project Structure

```
src/gassi/
├── main.py                     # Entry point, wiring
├── models/                     # Pydantic data models
│   ├── config.py               # AppSettings (pydantic-settings)
│   ├── enums.py                # AssistantMode, AdvisorInputSource
│   ├── game_pack.py            # GamePackManifest, HudRegion
│   └── results.py              # AdvisorResult, PlacementResult, OcrResult
├── core/                       # Game-agnostic engine
│   ├── ai/
│   │   ├── protocol.py         # AiBackend Protocol
│   │   └── gemini_backend.py   # Gemini implementation
│   ├── capture/
│   │   ├── protocol.py         # CaptureBackend, CaptureRegionProvider Protocols
│   │   ├── mss_backend.py      # mss-based capture
│   │   └── region_provider.py  # Overlay-anchored region (v1)
│   ├── ocr/
│   │   └── rapid_ocr_engine.py # RapidOCR wrapper
│   ├── overlay/
│   │   └── overlay_canvas.py   # Layered tkinter Canvas
│   ├── async_bridge.py         # asyncio ↔ tkinter threading bridge
│   ├── game_pack_loader.py     # YAML manifest + prompt loader
│   └── hotkey_manager.py       # pynput global hotkeys
├── viewmodels/
│   └── assistant_viewmodel.py  # Mode FSM, dispatch, state management
└── views/
    ├── dialogs.py              # Placement prompt input dialog
    └── main_overlay.py         # Root tkinter overlay window

game_packs/
└── timberborn/
    ├── manifest.yaml           # Game config, HUD regions
    └── prompts/                # AI system prompts
        ├── advisor_ocr.txt
        ├── advisor_screenshot.txt
        └── placement.txt
```

## Architecture

- **MVVM pattern**: Models (data) → ViewModel (logic/state) → Views (tkinter UI)
- **Protocol-based abstractions**: `AiBackend`, `CaptureBackend`, `CaptureRegionProvider` — swap implementations without touching ViewModel
- **Async bridge**: dedicated asyncio thread + queue → tkinter `after()` polling. AI calls never block the UI.
- **Game packs**: folder convention with manifest.yaml + prompt files. No dynamic plugin loader — just add a folder.

See `docs/architecture.md` for detailed decisions and rationale.

## Development

```bash
# Run tests
uv run pytest -v

# Lint
uv run ruff check src/ tests/

# Type check
uv run mypy src/
```

## License

MIT
