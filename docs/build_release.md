# GASSI — Build & Release Guide

## Prerequisites

- Python 3.12 via uv
- All dev extras installed: `uv sync --extra dev`
- Optional extras for full bundle: `uv sync --extra dev --extra claude --extra rag --extra windows`

## Build

```bash
uv run python -m PyInstaller gassi.spec --clean
```

Output: `dist/gassi/` folder containing `gassi.exe` + `_internal/` + `game_packs/`.

## Testing the build on dev machine

**Important:** The `.exe` shares the same OS keyring and `%LOCALAPPDATA%\gassi\settings.json`
as your dev environment. This means:

- Your existing API key is found immediately — no "No API key" prompt appears
- Your existing settings (theme, model, hotkeys) are loaded
- Your existing calibration files are NOT used — the build bundles the repo's
  `game_packs/` tree, so `hud_regions_user.yaml` from the repo is used, not
  the one in your dev AppData

**To test the first-run experience (no API key prompt):**

```bash
# Temporarily clear your Gemini key from keyring
python -c "import keyring; keyring.delete_password('gassi', 'gemini_api_key')"

# Run the build
dist\gassi\gassi.exe

# After testing, restore your key
python -c "import keyring; keyring.set_password('gassi', 'gemini_api_key', 'YOUR_KEY')"
```

**To test with completely clean settings:**

```bash
# Rename existing settings (backup)
ren "%LOCALAPPDATA%\gassi\settings.json" settings.json.bak

# Clear keyring
python -c "import keyring; keyring.delete_password('gassi', 'gemini_api_key')"

# Run the build — should show "No API key set" and open Settings
dist\gassi\gassi.exe

# Restore after testing
ren "%LOCALAPPDATA%\gassi\settings.json.bak" settings.json
python -c "import keyring; keyring.set_password('gassi', 'gemini_api_key', 'YOUR_KEY')"
```

## Smoke test checklist

1. [ ] App window appears (overlay with toolbar)
2. [ ] Console shows `GASSI v0.8.6 started` with correct provider/game
3. [ ] Settings dialog opens via gear icon
4. [ ] API key fields visible in General tab (masked)
5. [ ] Model dropdown populates (Gemini live fetch or Claude static list)
6. [ ] Game pack selector shows available packs
7. [ ] F1 fires advisor query (requires game running in background)
8. [ ] F2 opens placement strip (overlay visible) or floating dialog (overlay offscreen)
9. [ ] F3 toggles click-through lock
10. [ ] Slide offscreen and back (pull tab) works
11. [ ] Collapse and expand works
12. [ ] Close exits cleanly (no traceback in console)

## Full release procedure

### 1. Pre-release checks

```bash
# Ensure all changes committed
git status

# Run tests
uv run pytest -v

# Lint
uv run ruff check src/ tests/
```

### 2. Version bump (if not already done)

Three files must stay in sync:

| File | What to update |
|------|----------------|
| `pyproject.toml` | `version = "X.Y.Z"` |
| `src/gassi/main.py` | `_get_version()` fallback string |
| `RELEASE_NOTES.md` | Version in title and zip filename |

### 3. Build

```bash
uv run python -m PyInstaller gassi.spec --clean
```

### 4. Smoke test

Run `dist\gassi\gassi.exe` and go through the checklist above.

### 5. Create zip

```bash
powershell Compress-Archive -Path dist\gassi\* -DestinationPath GASSI-v0.8.6-beta-win64.zip -Force
```

Verify the zip contents:
```
gassi.exe
_internal/          (Python runtime, all dependencies)
game_packs/         (Timberborn + Nebuchadnezzar packs)
```

### 6. Commit, tag, push

```bash
git add -A
git commit -m "release: v0.8.6-beta"
git tag v0.8.6-beta
git push origin main --tags
```

### 7. GitHub Release

1. Go to **GitHub** -> **Releases** -> **Draft a new release**
2. **Choose a tag:** `v0.8.6-beta`
3. **Release title:** `GASSI v0.8.6-beta — First Public Beta`
4. **Description:** paste the contents of `RELEASE_NOTES.md`
5. **Attach binary:** drag `GASSI-v0.8.6-beta-win64.zip` into the assets area
6. Check **Set as a pre-release** (this is a beta)
7. Click **Publish release**

### 8. Post-release

- Verify the release page shows correctly on GitHub
- Download the zip from the release page and confirm it runs on the dev machine
- Announce on any relevant channels (Discord, Reddit, etc.)

## Future releases

For subsequent releases, repeat steps 1-8 with the new version number.
The naming convention is:

| Release type | Tag format | Zip filename | Notes |
|---|---|---|---|
| Beta | `v0.X.Y-beta` | `GASSI-v0.X.Y-beta-win64.zip` | Pre-release checkbox on |
| Stable | `v0.X.Y` | `GASSI-v0.X.Y-win64.zip` | Full release |

## Known limitations of the beta build

- **Console window visible** — `console=True` in spec for debugging. Change to
  `console=False` for a future release once stable.
- **RAG not bundled** — chromadb is excluded from the build (too heavy for beta).
  RAG falls back to `NullRagService` silently. Advice quality is still good
  without RAG — it uses the static prompts.
- **No auto-updater** — users must download new zips manually.
- **Windows only** — PyInstaller spec targets Windows. macOS/Linux builds are
  tracked in v0.9.1.
- **Anti-cheat untested** — overlay may be detected by aggressive anti-cheat.
  See v0.8.2 roadmap.
