# TODO — GASSI Roadmap

## v0.1.2 — Usability & Debugging (IN PROGRESS)

### Settings UI
- [x] Settings dialog accessible from toolbar (gear icon)
- [x] Configurable hotkeys with key capture widget
- [x] Theme picker (dark/midnight/forest)
- [x] Cooldown interval slider
- [x] API model selector
- [x] Default input source selector (ocr/screenshot)
- [x] Persistent settings (JSON config file in OS app data directory)
- [x] Window position/size remembered across sessions

### Debug Tools
- [ ] Debug capture viewer: hotkey to save last captured frame as PNG to disk
- [ ] Show what was sent to Gemini (captured region outline or saved image)
- [ ] Log viewer panel in overlay (collapsible, shows last N log lines)

### Prompt Quality
- [ ] Tighten advisor prompt: max 3-4 lines, no markdown formatting instruction
- [ ] Add early-game context recognition (Cycle 1/Day 1 = beginner advice)
- [ ] Prompt iteration against real Timberborn gameplay screenshots

### Window Behavior
- [ ] "Ready" indicator in green after cooldown expires (before clearing)

## v0.2.0 — OCR & Input Improvements

### OCR Pipeline
- [ ] OCR preprocessing: contrast boost, binarization, upscaling crops before OCR
- [ ] Per-game font tuning profiles in game pack manifest
- [ ] Test RapidOCR against Timberborn's actual font with preprocessed images
- [ ] Fallback chain: OCR → screenshot only when OCR actually works for the game

### Input Improvements
- [ ] Inline text entry in the overlay body (replace popup dialog for F2)
- [ ] Prompt history (last 5 placement queries, selectable)
- [ ] Predefined quick-prompts per game pack (e.g. "Where to build next?", "Water strategy?")

## v0.3.0 — Spatial & Visual Feedback

### Grid Overlay (v2 placement)
- [ ] Draw A-Z / 1-N grid on captured screenshot before sending to Gemini
- [ ] Parse Gemini's cell references (e.g. "D5") from structured response
- [ ] Cell → screen pixel conversion using capture_rect + scale_factor
- [ ] Bounding box rendering on overlay at target coordinates

### Tutorial Overlays
- [ ] Arrow rendering: directional arrows pointing to game UI elements
- [ ] Tutorial step system: "click here" highlights with instruction text
- [ ] Tutorial sequences defined in game pack YAML (per-game tutorials)
- [ ] Dim background + highlighted region for focused guidance

## v0.4.0 — Multi-Game & RAG

### Second Game Pack
- [ ] RimWorld or Factorio game pack
- [ ] Validate pack structure generalizes (manifest, prompts, HUD regions)
- [ ] Identify what's truly game-specific vs. core engine
- [ ] Extract common prompt patterns into reusable templates

### RAG Pipeline
- [ ] Chroma + sentence-transformers for game knowledge retrieval
- [ ] Wiki/formula ingestion pipeline (chunking, embedding, persistence)
- [ ] Pre-baked Chroma collections shipped per game pack
- [ ] RAG-augmented prompts replacing static system prompt knowledge
- [ ] patch_version metadata filtering in Chroma queries

## v0.5.0 — Multi-Backend & Local Models

### AI Backend Expansion
- [ ] Claude API backend (ClaudeBackend implementing AiBackend Protocol)
- [ ] Backend selector in settings UI
- [ ] Cost tracking / token usage display per session

### Local SLM Support
- [ ] Ollama backend (OllamaBackend implementing AiBackend Protocol)
- [ ] Qwen2.5-VL / Llama 3.2 Vision support
- [ ] Freemium model: local SLM free, cloud paid
- [ ] GPU detection and model recommendation

## v0.6.0 — Platform & Distribution

### Platform Support
- [ ] Wayland capture backend (PipeWire/portal)
- [ ] Native window detection: per-OS window handle lookup (NativeWindowRegionProvider)
- [ ] SteamOS / Steam Deck testing
- [ ] macOS Screen Recording permission first-run prompt

### Anti-Cheat Posture (for online games)
- [ ] SetWindowDisplayAffinity (Windows — hide overlay from other screen captures)
- [ ] Adjustable window class/enumeration behavior
- [ ] Document per-game anti-cheat compatibility

### Distribution
- [ ] PyInstaller packaging and testing
- [ ] Auto-updater mechanism
- [ ] Installer for Windows (MSI or NSIS)
- [ ] TTS voice readout (edge-tts integration, optional)

## Ongoing / Cross-Cutting

- [ ] Unit tests for new features (maintain test coverage)
- [ ] Update README.md and docs/architecture.md with each version
- [ ] Performance profiling (memory, CPU during capture + OCR)
- [ ] Gemini API cost monitoring and optimization

---

## Completed

### v0.1.2 (2026-08-22) — Settings & Persistence
- [x] Settings dialog with two tabs (Hotkeys, General)
- [x] Key capture widget for hotkey rebinding
- [x] Theme picker dropdown
- [x] Cooldown slider (5-60s)
- [x] AI model text field
- [x] Default input source dropdown
- [x] Gear icon (⚙) in toolbar
- [x] Persistent JSON config in OS app data directory
- [x] Window geometry saved on close, restored on launch
- [x] Settings manager module (load/save/window geometry)

### v0.1.1 (2026-08-22) — Theme & Overlay UX
- [x] Theme system extracted (Theme model + 3 presets)
- [x] Collapsible overlay (▲/▼ toggle)
- [x] Slide-off-screen (◀ hide + ▶ pull-tab)
- [x] Custom frameless window (no native titlebar)
- [x] Compact toolbar with icon buttons
- [x] Markdown bold rendering in responses
- [x] Auto-hide overlay during capture
- [x] Full-screen capture for F2 placement and F1 screenshot fallback
- [x] Single-shot query model (no auto-polling)
- [x] Combined HUD regions into single API call
- [x] Cooldown timer with visible countdown
- [x] Footer hotkey hints in accent color
- [x] F3 lock hotkey
- [x] Themed placement dialog
- [x] Migrated Poetry → uv
- [x] Fixed rate limiting (36 req/min → 4 req/min)
- [x] Fixed overlay self-capture in screenshots
- [x] Fixed slide-off-screen reliability (withdraw/deiconify)

### v0.1.0 (2026-08-22) — Initial Scaffold
- [x] MVVM project scaffold with Protocol abstractions
- [x] Advisor mode (OCR + Screenshot sources)
- [x] Placement mode (free-text spatial advice)
- [x] Gemini backend (google-genai SDK)
- [x] mss screen capture
- [x] Overlay-anchored region provider
- [x] Layered OverlayCanvas (v2 layers scaffolded)
- [x] Async-to-tkinter bridge
- [x] pynput global hotkeys
- [x] Per-OS click-through (Windows/macOS/Linux)
- [x] Game pack system (folder + manifest.yaml + prompts)
- [x] Timberborn pack (v0.6)
- [x] OS keyring API key storage
- [x] pydantic-settings config
- [x] OCR confidence fallback
- [x] API error backoff
