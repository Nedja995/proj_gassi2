# Changelog

All notable changes to GASSI will be documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned (v2)
- Grid overlay for Placement mode (A–Z / 1–N coordinate system)
- Arrow/bounding-box rendering on overlay for spatial guidance
- Tutorial overlay system (highlight UI elements, step-by-step instructions)
- Native window detection (replace overlay-anchored region with per-OS window lookup)
- RAG pipeline (Chroma + sentence-transformers) replacing static prompt knowledge
- Claude API backend
- Local SLM support via Ollama (Qwen2.5-VL / Llama 3.2 Vision)
- Wayland capture backend (PipeWire/portal)
- TTS voice readout of advice (edge-tts integration)

## [0.1.0] - Unreleased

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
