# Adding a New Game Pack to GASSI

This guide covers everything needed to add support for a new game: folder structure,
manifest requirements, prompt authoring, OCR preprocessor config, and the early/mid/late
game stage design process.

No code changes are required for a new game pack. Everything is data.

---

## 1. Folder Structure

Create a new folder under `game_packs/` named after your game ID (lowercase, no spaces):

```
game_packs/
└── your_game_id/
    ├── manifest.yaml
    └── prompts/
        ├── advisor_ocr.txt
        ├── advisor_screenshot.txt
        └── placement.txt
```

The `game_id` must match the folder name exactly. It must also appear as the `game_id` field
in `manifest.yaml` — `GamePackLoader.list_available_packs()` reads it to populate the
Settings → General → Active game dropdown. Missing `game_id` in the manifest means the pack
will not appear in the selector.

To activate your pack: open Settings → General → select from the **Active game** dropdown → Save
& Close → restart GASSI. The overlay will show a restart notice automatically.

---

## 2. manifest.yaml

Full schema with all fields:

```yaml
game_id: your_game_id              # must match folder name AND appear in manifest
display_name: "Your Game"          # shown in Settings dropdown and startup log
window_title_pattern: "Your Game"  # used by focus check (F1 advisor hotkey guard)
game_version: "1.0"                # track which game version this pack targets
rag_collection_name: null          # reserved for v0.5.0 RAG pipeline; leave null

quick_prompts:
  - "Where should I build X?"      # shown in F2 placement strip dropdown
  - "Where is the best spot for Y?"
  - "Where should I place Z?"

hud_regions:
  - label: "top_bar"               # used in OCR log output and prompt context
    x_pct: 0.10                    # left edge, fraction of full monitor width (0.0–1.0)
    y_pct: 0.00                    # top edge, fraction of full monitor height
    width_pct: 0.80                # region width as fraction
    height_pct: 0.05               # region height as fraction

  - label: "resource_panel"
    x_pct: 0.00
    y_pct: 0.00
    width_pct: 0.20
    height_pct: 0.10
```

### Bootstrapping HUD regions from internet screenshots

You don't need to be at the game to write a first draft. Use review screenshots, Steam
screenshots, or wiki images to estimate fractional coordinates:

1. Open a reference screenshot at known resolution (e.g. 1456×816).
2. Measure pixel positions of each HUD element you want to capture.
3. Convert: `x_pct = x / W`, `y_pct = y / H`, `width_pct = w / W`, `height_pct = h / H`.
4. Add ~5–10px margins on each side (expressed as fractions) for OCR breathing room.
5. Mark all regions as estimated in a comment — run CalibrationService when at the game.

This is exactly how the Nebuchadnezzar pack was bootstrapped before any live testing.

### Calibrating HUD Regions (live game)

**Recommended path:** use the built-in CalibrationService (Settings → Calibrate HUD).
It sends a full screenshot to Gemini, detects HUD regions automatically, validates each
with RapidOCR, and writes the result to `hud_regions_user.yaml` (never overwrites your
manifest defaults).

**Manual path (if calibration fails or you prefer control):**

1. Run GASSI with the game open and press `F4` after pressing `F1` once.
   The debug frame PNG is saved to `%LOCALAPPDATA%\gassi\debug_frames\` (Windows).
2. Open the PNG in any image editor. Note total dimensions (W × H).
3. Measure each HUD element (left edge, top edge, width, height in pixels).
4. Convert to fractions and paste into `manifest.yaml`.

**Tips:**
- Prefer regions with **text only** — no icons or progress bars. OCR accuracy drops on mixed content.
- Keep region count low (2–4). All regions are captured and sent in one API call per F1 press.
- Labels become part of the OCR context: `[top_bar]: Day 3, Food: 45`. Use descriptive labels.
- Fractions are relative to the **full primary monitor**, not the overlay window.

---

## 3. OCR Preprocessor Config

Each HUD region label is looked up in `LABEL_CONFIGS` in `core/ocr/preprocessor.py`.
If your label isn't in the registry, `DEFAULT_CONFIG` is used (3× upscale, grayscale,
adaptive threshold — tuned for Timberborn's small white text on dark backgrounds).

If OCR confidence is consistently low for a region, add a custom config:

```python
# in core/ocr/preprocessor.py

YOUR_GAME_BAR_CONFIG = OcrPreprocessConfig(
    scale_factor=4.0,       # increase for very small text (<12px)
    grayscale=True,
    denoise=True,           # False for clean solid-colour backgrounds
    adaptive_threshold=True,
    adaptive_block_size=11, # smaller = tighter; use 11–15 for small digits
    adaptive_c=6,           # lower = keeps bright pixels; use 6–10 for white-on-dark
    sharpen=True,
    padding_px=6,
)

LABEL_CONFIGS["your_region_label"] = YOUR_GAME_BAR_CONFIG
```

**Config guidance by HUD type:**

| HUD type | scale_factor | block_size | C | denoise |
|----------|-------------|------------|---|---------|
| Small digits on dark icon strip | 4.0 | 11 | 6 | True |
| Medium text on dark band | 3.0 | 13 | 8 | True |
| Large clean text on solid dark | 2.5 | 15 | 10 | False |
| White text on light/gradient bg | 3.0 | 17 | 12 | True |

Use `F4` to save the preprocessed frame and visually confirm what RapidOCR receives.

---

## 4. Prompt Files

Three prompt files are required. All live in `prompts/` and are plain `.txt` files.
GASSI reads them from disk on every query — edit and re-test without restarting the app.

### 4a. advisor_ocr.txt

Receives: formatted OCR text from all HUD regions, labelled by region name.

Example user message the model will receive:
```
Current HUD readings:
[top_bar]: Day 3, Food: 45, Wood: 120
[resource_panel]: Workers: 8/10, Idle: 2
```

**Template:**

```
You are a <Game Name> strategy advisor. You receive OCR-extracted HUD text from: <list regions>.

<Game Name>: <one dense sentence — genre, core loop, primary threat/goal>.
Core resources: <comma list>. Key buildings: <comma list>.

GAME STAGES — use <signal> as indicator:
EARLY (<threshold>): focus on <3 survival priorities>.
MID (<threshold>): focus on <3 growth priorities>.
LATE (<threshold>): focus on <3 optimization priorities>.

TASK: Parse the HUD data. Identify the most urgent issue for the current stage.
Give 1–3 specific actionable recommendations in priority order.

RULES: Use markdown — ## for a short situation heading, bullets for recommendations,
**bold** for the most critical action. Max 1 heading + 3 bullets. Use game terminology.
Lead with the most urgent item.
```

### 4b. advisor_screenshot.txt

Same structure as `advisor_ocr.txt` but for visual input. Key differences:
- Opens with: "You receive a full screenshot. Read all visible HUD values, open panels, and map state."
- Add to RULES: "If a value is unreadable, skip it."

### 4c. placement.txt

Receives: full-screen PNG with coordinate grid overlaid + player's typed question.

Grid convention: columns A–Z (left→right), rows 1–N (top→bottom). Cells referenced as `"D5"`.

**Template:**

```
You are a <Game Name> placement advisor. You receive a screenshot with a coordinate grid
overlaid on it and a player question about where to build or place something.

The grid uses column letters (A, B, C…, left to right) and row numbers (1, 2, 3…, top to bottom).
Reference cells as "<letter><number>", e.g. "D5" or "B3".

<Game Name> spatial rules:
- <Key spatial constraint 1 — terrain, adjacency, radius, connectivity>
- <Key spatial constraint 2>
- <Key spatial constraint 3>

TASK: Answer with a specific grid cell the player can find immediately.
Reference the grid cell AND visible landmarks. Explain why that cell is correct.

RULES: Respond in JSON with exactly two fields:
- "cell": the single best grid cell reference (e.g. "D5")
- "advice": markdown advice. ## heading with cell reference, 1–2 bullets explaining why.
  **Bold** the key landmark or constraint. Max 1 heading + 2 bullets.

Example response:
{
  "cell": "D5",
  "advice": "## Cell D5 — <visible landmark>\n- **<Key reason>** — <why this cell>.\n- <How to connect or secondary step>."
}
```

---

## 5. Early / Mid / Late Game Design

### Step 1: Define your stages

| Stage | Trigger signals (visible in HUD) | Advice focus |
|-------|----------------------------------|--------------|
| Early | low turn/day/cycle, small resource counts | Survival basics, first infrastructure |
| Mid | moderate resources, threat approaching | Efficiency, threat preparation |
| Late | high resources, multiple systems active | Optimization, expansion, advanced systems |

Use only signals that appear in the HUD text or screenshot — the model cannot see
unlock state or past events.

### Step 2: Write the stage clause

Keep it to 3 lines in the prompt. Put it between the game knowledge block and TASK.

```
GAME STAGES — use <signal> as indicator:
EARLY (<threshold>): focus on <3 priorities>.
MID (<threshold>): focus on <3 priorities>.
LATE (<threshold>): focus on <3 priorities>.
```

### Step 3: Validate with prompt_iteration.py

```bash
# Early game test
uv run python tests/prompt_iteration.py --mode advisor_ocr \
  --hud "[top_bar]: Day 3, Gold: 500, Pop: 120"

# Late game test
uv run python tests/prompt_iteration.py --mode advisor_ocr \
  --hud "[top_bar]: Day 180, Gold: 8000, Pop: 2800"

# Screenshot test
uv run python tests/prompt_iteration.py --mode advisor_screenshot \
  --image path/to/saved_debug_frame.png
```

Check that early test → survival advice, late test → optimization advice, and all bullets
use game-specific terminology (not generic "build more food").

---

## 6. Testing Checklist

Before considering a pack ready:

- [ ] `manifest.yaml` parses: `uv run python -c "from gassi.core.game_pack_loader import GamePackLoader; GamePackLoader().load_manifest('your_game_id')"`
- [ ] Pack appears in Settings → General → Active game dropdown
- [ ] CalibrationService runs without error (Settings → Calibrate HUD)
- [ ] F4 debug frame shows correct HUD region crops for all labels
- [ ] OCR confidence > threshold for all regions (check log panel after F1)
- [ ] `advisor_ocr` tested with early/mid/late synthetic HUD via `prompt_iteration.py`
- [ ] `advisor_screenshot` tested with 3 real screenshots (early/mid/late)
- [ ] `placement` tested with 2–3 real screenshots + different placement questions
- [ ] Yellow highlight box appears at the correct cell after F2 placement query
- [ ] All response bullets use game-specific terminology — no generic advice
- [ ] Response length stays within 1 heading + 3 bullets

---

## 7. Switching Packs

Open **Settings → General → Active game** dropdown → select your game → Save & Close.

GASSI will show a restart notice in the overlay canvas. Restart to load the new pack.

The env var override still works for CI/testing:
```bash
GASSI_ACTIVE_GAME_ID=your_game_id uv run gassi
```
