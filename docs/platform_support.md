# GASSI — Platform Support

This document describes platform support status, known limitations, and
the testing procedure for each platform. Updated as of v0.9.9.

---

## Support Matrix

| Feature                         | Windows 10/11 | macOS 12+ | Linux (X11) | Steam Deck / SteamOS |
|---------------------------------|:---:|:---:|:---:|:---:|
| Overlay (tkinter)               | ✅  | ✅  | ✅  | 🔶 |
| Screen capture (mss)            | ✅  | ✅  | ✅  | 🔶 |
| OCR (RapidOCR / ONNX)          | ✅  | ✅  | ✅  | 🔶 |
| Global hotkeys (pynput)         | ✅  | 🔶  | 🔶  | 🔶 |
| Overlay click-through           | ✅  | 🔶  | ❌  | ❌  |
| Placement highlight (SetWinRgn) | ✅  | 🔶  | ❌  | ❌  |
| Hide from capture (WDA_EXCL.)   | ✅  | ❌  | ❌  | ❌  |
| Native window detection         | ✅  | ❌  | ❌  | ❌  |
| Screen Recording permission     | N/A | 🔶  | N/A | N/A |

**Legend:** ✅ Working | 🔶 Partial / untested | ❌ Not implemented / N/A

---

## Windows 10 / 11 (Primary — Fully Tested)

All features are implemented and tested. pywin32 is required for:
- Overlay click-through (`WS_EX_TRANSPARENT`)
- Placement highlight (`SetWindowRgn`, `GetClientRect`)
- Hide from capture (`SetWindowDisplayAffinity`)
- Native window detection (`EnumWindows`, `FindWindow`)
- Focus check (`GetForegroundWindow`)

pywin32 is listed in the default dependency group and is installed
automatically by `uv sync`.

**Anti-cheat / capture hiding:** `WDA_EXCLUDEFROMCAPTURE` (value `0x11`)
requires Windows 10 build 19041 (2004). On older builds the call fails
silently — the overlay remains visible in capture tools. A WARNING is
logged on failure.

---

## macOS (Partially Supported — Untested Beyond Dev Machine)

### Status
Tested in development on a MacBook but **not tested running GASSI against
actual games**. Game testing on macOS is a TODO item.

### Screen Recording Permission (v0.9.8)
macOS 10.15 (Catalina) and later require the Screen Recording entitlement
for any process that captures the screen.

- mss triggers the system permission prompt automatically on first capture.
- If the user denies permission, `mss.exception.ScreenShotError` is raised.
- GASSI v0.9.8 catches this error and surfaces a readable message in the
  overlay canvas, rather than crashing with a raw exception.
- **User action required:** System Preferences → Privacy & Security →
  Screen Recording → enable GASSI → restart GASSI.

### Click-through
The pyobjc stub exists (`try/except ImportError` fail-open) but the
NSWindow-based click-through is not yet implemented. The overlay is
a normal window on macOS — it will receive mouse clicks.

### Placement highlight
`SetWindowRgn` is Windows-only. The macOS fallback uses `-alpha 0.75`
semi-transparent window. The hollow frame clipping does not work on macOS.

### Hotkeys (pynput)
pynput requires the Accessibility permission on macOS:
System Preferences → Privacy & Security → Accessibility → enable GASSI.
Without it, global hotkeys silently do not fire.

### Native window detection
`NativeWindowRegionProvider._find_window_macos()` is a stub that returns
`None` (falls back to overlay rect). Implementing via NSWorkspace /
`CGWindowListCopyWindowInfo` is deferred to a future sub-version.

---

## Linux / X11 (Alpha — Untested)

### Capture
mss works on X11 via XCB/Xlib. Screen capture of games running under
Proton/Wine via XWayland should work.

### Click-through
Not implemented. `XShapeCombineRectangles` (libXext) would be the
correct approach — tracked as vFuture.

### Placement highlight
The `-alpha 0.75` fallback is used. Hollow frame clipping is not available.

### Hotkeys
pynput uses the evdev backend on Linux. May require the user to be a
member of the `input` group on some distributions:
```bash
sudo usermod -aG input $USER
# then log out and back in
```

---

## SteamOS / Steam Deck (Untested — Procedure Documented)

### Environment
SteamOS 3.x is Arch Linux with KDE Plasma on top of Gamescope
(a Wayland compositor). Most Steam games run via Proton, which uses
XWayland under Gamescope.

### Testing Procedure

**Do not implement code before running the test below.**
The goal is to identify what actually breaks before writing workarounds.

```bash
# 1. Switch Steam Deck to Desktop Mode
# 2. Open Konsole terminal

# Install Python and tkinter (not installed by default on Steam Deck)
sudo steamos-readonly disable
sudo pacman -S python-tk --noconfirm
sudo steamos-readonly enable

# 3. Clone or copy the GASSI repo to the Steam Deck
# 4. Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# 5. Install GASSI dependencies
cd /path/to/proj_gassi2
uv sync

# 6. Run GASSI
uv run python -m gassi.main
```

**Expected failure points:**
- `python-tk` not installed → tkinter `ModuleNotFoundError`
- mss capture via Gamescope XWayland → unknown (test required)
- pynput evdev hotkeys → may need `input` group membership
- pywin32 imports → already fail-open on non-Windows

**Report issues at:** project GitHub issues with label `steamdeck`.

### Wayland Capture (Known Limitation)

mss does **not** support pure Wayland capture — it uses XCB/Xlib, which
means it can only capture XWayland surfaces. For Gamescope (Steam Deck),
most game windows are XWayland, so this should work in practice.

If a game runs as a native Wayland surface (without XWayland), mss will
either capture nothing or return a blank frame. The fix would require the
PipeWire / `xdg-desktop-portal` capture path, which needs `dbus-python` +
GStreamer Python bindings. **This is deferred to vFuture** — the dependency
surface is large and it is unclear whether any target game requires it.

---

## Wayland (Known Limitation — vFuture)

Pure Wayland capture requires the `xdg-desktop-portal` D-Bus API +
PipeWire `pw-capture`. There is no stable Python library for this as of
2026. The `pipewire-screencapture` approach via subprocess is experimental.

**Decision:** Defer pure Wayland capture backend to vFuture. Document it
here as a known limitation. If user demand is high, open a tracking issue.

Required new deps (if implemented): `dbus-python` or `pydbus`, `PyGObject`
(GStreamer Python bindings). These add significant weight and Linux-specific
compile requirements. A new optional dep group `[wayland]` would be needed.

---

## Adding Platform Support (for contributors)

All platform-specific code follows the fail-open pattern established in
`session_handoff.md`:

```python
if platform.system() == "Windows":
    try:
        import win32gui
        # Windows-specific code
    except ImportError:
        logger.debug("pywin32 not available — skipping")
elif platform.system() == "Darwin":
    try:
        from AppKit import NSApp
        # macOS-specific code
    except ImportError:
        logger.debug("pyobjc not available — skipping")
# Linux: silently no-op or alpha fallback
```

Never hard-require a platform-specific import at module level.
The `try/except ImportError` pattern is mandatory — it keeps non-Windows
platforms runnable even when optional platform deps are absent.
