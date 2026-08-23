# Adding a New Game Pack to GASSI

This guide covers everything needed to add support for a new game: folder structure,
manifest calibration, prompt authoring, and the early/mid/late game design process.

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

The `game_id` must match the folder name exactly. It is referenced in `AppSettings.active_game_id`
(default: `"timberborn"`) and loaded by `GamePackLoader` at startup.

To activate your pack, either:
- Set env var: `GASSI_ACTIVE_GAME_ID=your_game_id`
- Or edit `settings.json` in the OS app data dir: `"active_game_id": "your_game_id"`

---

## 2. manifest.yaml

Full schema with all fields:

```yaml
game_id: your_game_id           # must match folder name
display_name: "Your Game"       # shown in logs at startup
window_title_pattern: "Your Game"  # reserved for v2 native window detection (unused in v1)
game_version: "1.0"             # track which game version this pack targets
rag_collection_name: null       # reserved for v2 RAG pipeline; leave null for now

hud_regions:
  - label: "top_bar"            # short descriptor, used in OCR log output and prompt context
    x_pct: 0.10                 # left edge, fraction of captured window width (0.0–1.0)
    y_pct: 0.00                 # top edge, fraction of captured window height (0.0–1.0)
    width_pct: 0.80             # region width as fraction
    height_pct: 0.05            # region height as fraction

  - label: "resource_panel"
    x_pct: 0.00
    y_pct: 0.00
    width_pct: 0.20
    height_pct: 0.10
```

### Calibrating HUD Regions

HUD regions define where GASSI crops for OCR in Advisor mode. All coordinates are
**fractional (0.0–1.0) relative to the full captured area** — they survive resolution
changes without recalibration.

**Calibration process:**

1. Run GASSI and trigger a debug frame save with `F4` after pressing `F1` once.
   The frame is saved to `%LOCALAPPDATA%\gassi\debug_frames\` (Windows).
2. Open the saved PNG in any image editor. Note the total image dimensions (W × H pixels).
3. For each HUD element you want to capture, measure:
   - `x` = left edge in pixels → `x_pct = x / W`
   - `y` = top edge in pixels → `y_pct = y / H`
   - `w` = region width in pixels → `width_pct = w / W`
   - `h` = region height in pixels → `height_pct = h / H`
4. Add margins (~5–10px each side) so OCR has breathing room around text.
5. Paste the fractions into `manifest.yaml`.

**Tips:**
- Prefer regions that contain **text only**, not icons or graphics — OCR accuracy drops on mixed content.
- If the game has a scalable UI, test at 100% UI scale first. Fractional coords handle window
  resize but not UI scale changes (that's a known limitation for v1).
- Keep region count low (2–4). All regions are OCR'd and combined into one API call per F1 press.
- Labels become part of the OCR context sent to the model: `[top_bar]: Day 3, Food: 45`.
  Use descriptive labels that help the model understand what it is reading.

---

## 3. Prompt Files

Three prompt files are required. All live in `prompts/` and are plain `.txt` files.
GASSI reads them from disk on every query — edit and re-test without restarting the app.

### 3a. advisor_ocr.txt

Receives: formatted OCR text from all HUD regions, labelled by region name.

Example user message the model will receive:
```
Current HUD readings:
[top_bar]: Day 3, Food: 45, Wood: 120
[resource_panel]: Workers: 8/10, Idle: 2
```

**Template to start from:**

```
You are a <Game Name> strategy advisor. You receive OCR-extracted HUD text: <list what regions contain>.

<Game Name>: <one dense sentence describing the genre, core loop, and primary threat/goal>.
Core resources: <comma list>. Key buildings/units: <comma list>.

TASK: Parse the HUD data, identify the most urgent issues, and give actionable recommendations in priority order.

<GAME_STAGE_CLAUSE — see Section 4>

RULES: Use markdown for readability — ## for a short situation heading, bullet points for recommendations, **bold** for the most critical item. Keep it concise: 1 heading + 2-4 bullets max. Use game terminology. Skip mechanics the player already knows.
```

### 3b. advisor_screenshot.txt

Receives: full-screen PNG of the game. Same structure as `advisor_ocr.txt` but the model
reads visually rather than from extracted text.

Differences from OCR prompt:
- First line: "You receive a full screenshot of the game. Read all visible HUD values, open panels, and map state."
- Add to RULES: "If a value is unreadable, skip it and advise on what you can see."

### 3c. placement.txt

Receives: full-screen PNG + the player's typed question (e.g. "Where should I put my water pump?").

**Template:**

```
You are a <Game Name> placement advisor. You receive a screenshot and a player question about where to build or place something.

<Game Name> spatial rules: <bullet the key spatial constraints — terrain, adjacency, radius, connectivity, power>.

TASK: Answer the placement question with a specific location the player can find on screen right now.
Reference visible landmarks (buildings, terrain features, resources) and cardinal or relative directions.
Explain why that spot is correct.

RULES: Use markdown for readability — ## for the recommended location, then 1-2 bullets explaining why
and how to connect it. **Bold** the key landmark or direction. Be spatially precise — point to a real
visible spot. No grid coordinates.

Example:
## <Specific visible location name>
- **<Key spatial reason>** — <why this spot works>.
- <How to connect it / secondary consideration>.
```

---

## 4. Early / Mid / Late Game Design

The most important prompt design decision is **game stage detection**. Without it, the model
gives the same advice regardless of whether the player is on day 1 or day 200.

### Principle

The AI cannot truly detect game stage — it reads what the HUD shows. Your job is to tell it
**what signals map to which stage** and **what advice scope applies to each stage**.

### Step 1: Define Your Game's Stages

Every game has a different progression. Before writing prompts, define your stages explicitly:

| Stage | Trigger Signals | Advice Focus |
|-------|----------------|--------------|
| Early | Day/turn < X, low resource counts, few structures | Survival basics, first infrastructure |
| Mid | Moderate resources, first threat approaching | Efficiency, threat preparation |
| Late | High resource counts, multiple systems active | Optimization, expansion, advanced systems |

**Timberborn example:**
- Early: Day 1–15 → water access, food, first housing
- Late: Day 16+ → drought prep, district expansion, power chains

**RimWorld example** (hypothetical):
- Early: Colony < 5 pawns, no threat events yet → base layout, first crops, stockpile
- Mid: First raid warning, < 10 pawns → defenses, medicine, mood management
- Late: 10+ pawns, mechanoids/infestations → automation, trade, advanced weapons

### Step 2: Identify the Signals the Model Can Read

The model only knows what is in the HUD text or visible in the screenshot. Your stage
clause must use signals that actually appear in those inputs.

**Good signals** (visible in HUD):
- Day / turn / cycle number
- Population count
- Specific resource amounts (very low = early, high = late)
- Active event names ("Drought incoming", "Raid: 3 days")

**Bad signals** (not in HUD):
- "When the player has unlocked X" (unlock state not in HUD text)
- "After the first raid" (past events not visible)

### Step 3: Write the Stage Clause

Keep it to 1–2 lines in the prompt. Put it between TASK and RULES.

**Format:**
```
EARLY GAME (<signal threshold>): focus on <3 survival priorities>.
MID GAME (<signal threshold>): focus on <3 growth priorities>.
LATE GAME (<signal threshold>): focus on <3 optimization priorities>.
```

Only include the stages your game actually has. Two stages (early/late) is fine if the
game doesn't have a meaningful mid-game transition.

**Examples:**

```
# Two-stage (Timberborn style)
EARLY GAME (Day 1–15): focus on water access, food, and first housing.
LATE GAME (Day 16+): focus on drought prep, district expansion, power chains.
```

```
# Three-stage (RimWorld style, hypothetical)
EARLY GAME (< 5 colonists): focus on shelter, food, first power source.
MID GAME (5–10 colonists, first threat warnings): focus on defenses, medicine, mood.
LATE GAME (10+ colonists): focus on trade, research, mechanoid countermeasures.
```

```
# Event-triggered (games with explicit event states)
EARLY GAME (no active threats visible): focus on economy and infrastructure.
CRISIS MODE (threat event visible in HUD): focus entirely on the active threat — defer all expansion.
RECOVERY (threat resolved): stabilize supplies before resuming expansion.
```

### Step 4: Validate with the Iteration Tool

After writing prompts, test them with synthetic HUD data before playing:

```bash
# Early game test
uv run python tests/prompt_iteration.py --mode advisor_ocr \
  --hud "[top_bar]: Day 3, Food: 12, Wood: 40 [resource_panel]: Workers: 4, Idle: 1"

# Late game test
uv run python tests/prompt_iteration.py --mode advisor_ocr \
  --hud "[top_bar]: Day 45, Food: 380, Wood: 1200 [resource_panel]: Workers: 28, Idle: 0"
```

Check that:
- Early test → advice focuses on survival priorities, not advanced systems
- Late test → advice focuses on optimization/expansion, not basics
- The `##` heading correctly names the situation
- Bullets are specific to the game, not generic ("build more defenses" is bad; "queue a Sandbag Wall at the north choke point" is good)

---

## 5. Testing Checklist

Before considering a pack ready:

- [ ] `manifest.yaml` parses without error: `uv run python -c "from gassi.core.game_pack_loader import GamePackLoader; GamePackLoader().load_manifest('your_game_id')"`
- [ ] OCR regions cover the key HUD elements with no overlap
- [ ] `advisor_ocr` prompt tested with early/mid/late synthetic HUD strings via `prompt_iteration.py`
- [ ] `advisor_screenshot` prompt tested with at least 3 real screenshots (early/mid/late)
- [ ] `placement` prompt tested with 2–3 real screenshots and different placement questions
- [ ] Early-game clause fires correctly (beginner advice on Day 1 data)
- [ ] Responses use game-specific terminology throughout
- [ ] Response length stays within 1 heading + 4 bullets (no walls of text)
- [ ] No generic advice ("build more food") — all bullets reference specific buildings or locations

---

## 6. Activating and Switching Packs

```bash
# Env var (temporary, overrides saved settings)
GASSI_ACTIVE_GAME_ID=your_game_id uv run gassi

# Permanent: edit settings.json
# Windows: %LOCALAPPDATA%\gassi\settings.json
# macOS: ~/Library/Application Support/gassi/settings.json
# Linux: ~/.config/gassi/settings.json
{
  "active_game_id": "your_game_id"
}
```

Only one game pack is active at a time. Multi-pack switching UI is planned for v0.4.0.
