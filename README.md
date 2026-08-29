# GASSI — Game-specific AI Strategy Screen Inspector

A lightweight, cross-platform desktop overlay that assists players in real-time with complex
strategy and colony-sim games. Currently supports **Timberborn** and **Nebuchadnezzar**.

**No game memory reading. No process injection. Pure computer vision + screen overlay.**

---

## How It Works

GASSI captures your game screen, extracts information via local OCR or direct screenshot,
and sends it to an AI model for strategic advice — displayed as a translucent, always-on-top
overlay on top of your game.

Six AI backends supported: **Gemini**, **Claude**, **Ollama** (local), **Groq** (free),
**Together AI** (free), and **HuggingFace Inference API** (free). Switch provider in
Settings without restarting the app.

---

## Features (v0.9.5)

### Advisor Mode (`F1`)

On-demand capture of pre-calibrated HUD regions. Two input sources (toggle with `Shift+F1`):

- **OCR** — local text extraction via RapidOCR → text sent to AI backend (low cost)
- **Screenshot** — HUD image sent directly to AI backend (richer context, fallback)

Automatic confidence-gated fallback: if OCR confidence drops below threshold, that cycle
switches to screenshot automatically.

### Placement Mode (`F2`)

On-demand: captures full game window + your typed question → AI returns spatial advice.

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

- Select AI backend (all six providers with tier labels) and model
- Per-provider credential: API key (cloud) or server URL (Ollama)
- Rebind all hotkeys via key-capture widget
- Switch theme (dark / midnight / forest)
- Adjust cooldown interval (5–60s)
- Select default advisor input source (OCR / Screenshot)
- Toggle grid overlay for placement mode
- Settings persist across sessions (`settings.json` in OS app data dir)

Session token usage and estimated cost shown in the overlay footer after each AI call.

### AI Provider Tiers

| Provider | Type | Free Tier | Vision | Notes |
|---|---|---|---|---|
| Gemini | Cloud — paid | 1,500 req/day free | Yes | Best quality; primary backend |
| Claude | Cloud — paid | No | Yes | Strong reasoning; optional `[claude]` |
| Ollama | Local | Free (self-hosted) | Yes (vision models) | Needs GPU; see `docs/local_models.md` |
| Groq | Cloud — free | 14,400 req/day | Yes | Fast; best free-tier option |
| Together AI | Cloud — free | $1 credit on signup | Yes | Wide model selection |
| HuggingFace | Cloud — free | Rate-limited | Yes | Inference API only; no PyTorch |

All four OpenAI-compatible providers (Ollama, Groq, Together, HuggingFace) share the
`[providers]` optional dep group (`openai>=1.50`).

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

- Windows 10 or 11 (64-bit)
- One of the following:
  - **Gemini API key** (free tier: 1,500 req/day) — https://aistudio.google.com/apikey
  - **Groq API key** (free tier: 14,400 req/day) — https://console.groq.com
  - **Together AI key** — https://api.together.xyz
  - **HuggingFace token** — https://huggingface.co/settings/tokens
  - **Ollama** (local, no key) — https://ollama.com — see `docs/local_models.md`

---

## Quick Start (End Users)

1. Download `GASSI-v0.8.5-beta-win64.zip` from the [latest release](../../releases/latest)
2. Extract the zip to any folder
3. Run `gassi.exe`
4. Settings opens automatically on first run — select your AI backend and paste your API key
5. Restart `gassi.exe`
6. Start your game in **Borderless Windowed** mode
7. Press **F1** for advice, **F2** for placement help

**No Python required. No terminal. No config files.**

For local inference (Ollama), see [`docs/local_models.md`](docs/local_models.md).

---

## Developer Setup

```bash
# Clone
git clone <repo-url>
cd proj_gassi2

# Create venv and install core deps
uv venv --python 3.12
uv sync

# Windows: also install pywin32 for click-through overlay
uv sync --extra windows

# Optional extras (install any combination)
uv sync --extra rag        # Chroma RAG pipeline
uv sync --extra claude     # Anthropic Claude backend
uv sync --extra providers  # Ollama + Groq + Together AI + HuggingFace backends
uv sync --extra dev        # pytest, ruff, mypy, pyinstaller

# All at once
uv sync --extra windows --extra rag --extra claude --extra providers --extra dev
```

### Store API keys in OS keyring

```bash
# Gemini (primary)
uv run python -c "import keyring; keyring.set_password('gassi', 'gemini_api_key', 'YOUR_KEY')"

# Claude (if using [claude] extras)
uv run python -c "import keyring; keyring.set_password('gassi', 'claude_api_key', 'YOUR_KEY')"

# Groq
uv run python -c "import keyring; keyring.set_password('gassi', 'groq_api_key', 'YOUR_KEY')"

# Together AI
uv run python -c "import keyring; keyring.set_password('gassi', 'together_api_key', 'YOUR_KEY')"

# HuggingFace
uv run python -c "import keyring; keyring.set_password('gassi', 'huggingface_api_key', 'YOUR_TOKEN')"
```

Keys can also be entered via the Settings dialog (⚙) — stored in OS keyring, never written to disk.

---

## Usage

```bash
# Run
uv run gassi

# Or activate venv first
.venv\Scripts\activate   # Windows
source .venv/bin/activate # macOS/Linux
gassi
```

Position the overlay over your game window. Use hotkeys listed above.

---

## Project Structure

```
src/gassi/
├── main.py                          # Entry point, dependency wiring
├── models/
│   ├── config.py                    # AppSettings (pydantic-settings + JSON persistence)
│   ├── enums.py                     # AssistantMode, AdvisorInputSource, AiProvider
│   ├── game_pack.py                 # GamePackManifest, HudRegion
│   └── results.py                   # AdvisorResult, PlacementResult, OcrResult, UsageStats
├── core/
│   ├── ai/
│   │   ├── protocol.py              # AiBackend Protocol
│   │   ├── factory.py               # Backend factory (build_ai_backend, get_api_key)
│   │   ├── gemini_backend.py        # Gemini (google-genai SDK)
│   │   ├── claude_backend.py        # Claude (anthropic SDK, optional [claude])
│   │   ├── openai_compat_backend.py # Shared base for OpenAI-compat providers
│   │   ├── ollama_backend.py        # Ollama local (optional [providers])
│   │   ├── groq_backend.py          # Groq cloud free (optional [providers])
│   │   ├── together_backend.py      # Together AI cloud (optional [providers])
│   │   └── huggingface_backend.py   # HuggingFace Inference API (optional [providers])
│   ├── capture/
│   │   ├── protocol.py              # CaptureBackend, CaptureRegionProvider Protocols
│   │   ├── mss_backend.py           # mss screen capture
│   │   └── region_provider.py       # Overlay-anchored region provider (v1)
│   ├── ocr/
│   │   └── rapid_ocr_engine.py      # RapidOCR wrapper
│   ├── rag/
│   │   ├── protocol.py              # RagService Protocol
│   │   ├── chroma_backend.py        # ChromaRagService (optional [rag])
│   │   ├── null_backend.py          # NullRagService (no-op fallback)
│   │   └── factory.py               # RagServiceFactory
│   ├── overlay/
│   │   └── overlay_canvas.py        # Layered canvas + markdown renderer
│   ├── async_bridge.py              # asyncio ↔ tkinter bridge (thread + queue)
│   ├── capture_affinity.py          # SetWindowDisplayAffinity (anti-cheat, v0.8.2)
│   ├── debug_manager.py             # Debug frame save, auto-prune
│   ├── game_pack_loader.py          # YAML manifest + prompt loader
│   ├── hotkey_manager.py            # pynput global hotkeys
│   ├── log_handler.py               # In-memory logging handler (feeds log panel)
│   ├── paths.py                     # get_base_dir() — dev vs PyInstaller frozen
│   ├── settings_manager.py          # JSON settings persistence
│   └── theme/
│       └── theme.py                 # Theme model + 3 presets
├── viewmodels/
│   └── assistant_viewmodel.py       # Mode FSM, capture dispatch, cooldown, debug
└── views/
    ├── floating_advice_window.py    # Floating advice window (F1 when overlay hidden)
    ├── floating_placement_dialog.py # Floating placement dialog (F2 when overlay hidden)
    ├── log_panel.py                 # Collapsible log viewer panel
    ├── main_overlay.py              # Root overlay window (toolbar, canvas, footer)
    ├── placement_highlight.py       # Cell highlight window (SetWindowRgn)
    ├── placement_strip.py           # Inline placement input strip (F2)
    └── settings_dialog.py           # Settings dialog (hotkeys + general tabs)

game_packs/
├── timberborn/
│   ├── manifest.yaml                # HUD regions, footprints, RAG config
│   ├── knowledge/                   # .md source files for RAG ingestion
│   ├── rag/                         # Chroma vector DB (committed)
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
├── architecture.md                  # Architecture Decision Records (AD-01 – AD-29)
├── adding_game_pack.md              # Guide: adding support for a new game
├── build_release.md                 # Build, test, and release guide
├── local_models.md                  # Local inference guide (Ollama, VRAM tiers)
├── session_handoff.md               # Session context for new chats
└── v1_scope.md                      # Feature scope and known limitations

tools/
└── ingest_knowledge.py              # RAG ingestion CLI

tests/
├── conftest.py
├── prompt_iteration.py              # CLI tool: test prompts against screenshots
├── test_game_pack_loader.py
└── test_models.py
```

---

## Architecture

- **MVVM pattern** — Models (Pydantic data) → ViewModel (logic/FSM) → Views (tkinter)
- **Protocol abstractions** — `AiBackend`, `CaptureBackend`, `CaptureRegionProvider`, `RagService` — swap implementations without touching ViewModel
- **Async bridge** — dedicated asyncio thread + queue → tkinter `after()` polling. AI calls never block the UI.
- **Game packs** — folder convention: `game_packs/<id>/manifest.yaml` + `prompts/`. No plugin system — just add a folder. See `docs/adding_game_pack.md`.
- **OpenAI-compat transport** — Ollama, Groq, Together AI, HuggingFace all share `OpenAiCompatBackend` + `openai` SDK. Adding a new provider = one subclass + one `base_url` constant (AD-29).
- **Markdown renderer** — `OverlayCanvas` renders `## headings`, `- bullets`, and `**bold**` natively.
- **Theme system** — all visual constants in `Theme` model, 3 presets, selectable via settings dialog.
- **Persistent settings** — JSON in OS app data dir, merged with env var overrides at startup.

See `docs/architecture.md` for full decision records (AD-01 – AD-29).

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

# RAG ingestion (after editing knowledge files)
uv run python tools/ingest_knowledge.py --game-id timberborn \
    --source-dir game_packs/timberborn/knowledge --game-version 0.6 --reset
```

---

## Adding a New Game

See [`docs/adding_game_pack.md`](docs/adding_game_pack.md) for the complete guide covering:
folder structure, manifest calibration, prompt authoring, RAG knowledge authoring,
and early/mid/late game stage design.

---

## Market Position

GASSI wins by **hyper-specialization** — deep, formula-level knowledge for individual games —
where generalist tools (NVIDIA G-Assist, Steam Gaming Copilot) give only surface advice.

Six AI backends cover every user tier: free cloud (Groq, Together AI, HuggingFace),
paid cloud (Gemini, Claude), and local/offline (Ollama). The freemium model means users
with strong GPUs pay nothing; users on weak hardware have multiple free cloud options.

---

## License

MIT
