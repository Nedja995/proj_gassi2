"""Placement highlight window — always-on-top cell outline overlay.

Draws a solid coloured rectangle outline + label directly over the game screen
at the Gemini-returned cell position.

Transparency approach — SetWindowRgn, NOT WS_EX_LAYERED / -transparentcolor:
    WS_EX_LAYERED + SetLayeredWindowAttributes (LWA_COLORKEY) is unreliable
    on Windows 10/11 with DWM when GDI child windows (tkinter Canvas) are
    involved — the color key is not composited correctly and the window renders
    as a solid near-black rectangle.

    SetWindowRgn clips the window's visual and hit-test area to an arbitrary
    region. By setting the region to (outer_rect - inner_rect) we get a
    hollow frame shape: only the outline pixels belong to the window, the cell
    interior is fully outside the region and the game is visible through it.
    No layered window tricks needed.

Click-through:
    WS_EX_TRANSPARENT without WS_EX_LAYERED passes all mouse messages to
    windows below — no click interception on the outline strip.

Non-Windows fallback:
    macOS / Linux use wm_attributes("-alpha", 0.75) with a small opaque
    window covering the cell. Interior is semi-transparent (game partially
    visible), outline clearly visible. Good enough for those platforms.

Hide/show:
    The Toplevel is moved off-screen (not withdrawn) between uses to avoid
    HWND recreation. SetWindowRgn is re-applied on every show() because
    the cell size can change between queries.

Win32 implementation note (AD-24):
    ctypes is used instead of pywin32 for SetWindowRgn / SetWindowLong.
    pywin32 wraps HWNDs in a custom type that can cause validation failures
    with some tkinter-returned handles. ctypes with raw int(winfo_id()) is
    more reliable.
    GetAncestor(GA_ROOT) was tried but is WRONG for tkinter Toplevels —
    it returns the main Tk window HWND (since Toplevels are internal children
    of the Tk root), causing SetWindowRgn to clip the main overlay instead.
    Direct winfo_id() on the Toplevel widget returns the correct HWND.
"""

import logging
import platform
import tkinter as tk

from gassi.core.theme.theme import Theme

logger = logging.getLogger(__name__)

# visual constants
_BOX_COLOUR = "#ffdd00"      # yellow outline + label background border
_LABEL_BG = "#1a1a00"        # dark label fill
_LABEL_FG = "#ffdd00"        # label text
_BOX_WIDTH = 3               # outline thickness in px
_LABEL_H = 22                # fixed label area height in px
_LABEL_FONT = ("Consolas", 11, "bold")
_LABEL_PAD = 6               # horizontal padding inside label

# off-screen position used when "hidden" (no withdraw — preserves HWND)
_OFFSCREEN = "-32000+-32000"

# Win32 constants (avoid importing win32con)
_GWL_EXSTYLE = -20
_WS_EX_TRANSPARENT = 0x00000020
_RGN_DIFF = 4
_RGN_OR = 2


class PlacementHighlightWindow:
    """Placement cell highlight using SetWindowRgn (Windows) or alpha (other)."""

    def __init__(self, parent: tk.Tk, theme: Theme) -> None:
        self._parent = parent
        self._theme = theme
        self._system = platform.system()
        self._toplevel: tk.Toplevel | None = None
        self._canvas: tk.Canvas | None = None
        self._dismiss_after_id: str | None = None

    # ── public API ────────────────────────────────────────────────────

    def show(
        self,
        pixel_rect: tuple[int, int, int, int],
        cell_ref: str,
        monitor_rect: tuple[int, int, int, int],
        auto_dismiss_ms: int = 8000,
    ) -> None:
        """Draw the cell highlight at pixel_rect for auto_dismiss_ms milliseconds."""
        self._cancel_dismiss()

        if self._toplevel is None or not self._toplevel.winfo_exists():
            self._build_toplevel()

        if self._toplevel is None or self._canvas is None:
            logger.warning("PlacementHighlightWindow: build failed")
            return

        px, py, pw, ph = pixel_rect
        label_w = self._label_width(cell_ref)

        # window covers label strip above + cell area below
        win_w = max(pw, label_w)
        win_h = _LABEL_H + ph
        win_x = px
        win_y = py - _LABEL_H

        # draw content before moving on-screen
        self._canvas.config(width=win_w, height=win_h)
        self._draw(pw, ph, label_w, cell_ref)

        # position on-screen then force a full update so the Win32 window
        # is at the correct size before SetWindowRgn is applied
        self._toplevel.geometry(f"{win_w}x{win_h}+{win_x}+{win_y}")
        self._toplevel.update()   # full update, not just idletasks

        if self._system == "Windows":
            self._apply_region_and_clickthrough(pw, ph, label_w)
        else:
            # macOS / Linux: alpha fallback — interior is 75% visible (game shows through).
            # macOS improvement path (v0.6.0): NSWindow.setOpaque_(False) +
            #   NSColor.clearColor() background + CAShapeLayer mask for hollow region.
            # Linux X11 improvement path (v0.6.0): XShapeCombineRectangles via python-xlib.
            # Wayland: shape protocol extension or compositor-specific API.
            self._toplevel.attributes("-alpha", 0.75)

        self._toplevel.lift()

        self._dismiss_after_id = self._toplevel.after(auto_dismiss_ms, self.clear)
        logger.debug(
            "Placement highlight: cell=%s px_rect=%s dismiss_ms=%d",
            cell_ref, pixel_rect, auto_dismiss_ms,
        )

    def clear(self) -> None:
        """Hide the highlight. Moves off-screen — HWND preserved."""
        self._cancel_dismiss()
        if self._canvas is not None:
            self._canvas.delete("all")
        if self._toplevel is not None and self._toplevel.winfo_exists():
            self._toplevel.geometry(f"1x1+{_OFFSCREEN}")

    def destroy(self) -> None:
        """Destroy on app close."""
        self._cancel_dismiss()
        if self._toplevel is not None and self._toplevel.winfo_exists():
            self._toplevel.destroy()
        self._toplevel = None
        self._canvas = None

    # ── internal ──────────────────────────────────────────────────────

    def _build_toplevel(self) -> None:
        top = tk.Toplevel(self._parent)
        top.overrideredirect(True)
        top.attributes("-topmost", True)
        top.configure(bg=_BOX_COLOUR)
        top.geometry(f"1x1+{_OFFSCREEN}")

        canvas = tk.Canvas(
            top, bg=_BOX_COLOUR,
            highlightthickness=0, bd=0,
        )
        canvas.pack(fill=tk.BOTH, expand=True)

        top.update()  # map HWND before any win32 calls in show()

        self._toplevel = top
        self._canvas = canvas
        logger.debug("PlacementHighlightWindow toplevel built")

    def _draw(self, pw: int, ph: int, label_w: int, cell_ref: str) -> None:
        """Draw label and box outline on canvas (local coords)."""
        if self._canvas is None:
            return
        self._canvas.delete("all")

        # label area: (0, 0) -> (label_w, _LABEL_H)
        self._canvas.create_rectangle(
            0, 0, label_w, _LABEL_H,
            fill=_LABEL_BG, outline=_BOX_COLOUR, width=1,
        )
        self._canvas.create_text(
            label_w // 2, _LABEL_H // 2,
            text=cell_ref, fill=_LABEL_FG,
            font=_LABEL_FONT, anchor="center",
        )

        # box outline at y-offset = _LABEL_H
        # only the outline is visible (interior clipped by SetWindowRgn on Windows;
        # on other platforms the full rectangle shows at reduced alpha)
        self._canvas.create_rectangle(
            0, _LABEL_H, pw, _LABEL_H + ph,
            outline=_BOX_COLOUR, width=_BOX_WIDTH, fill=_BOX_COLOUR,
        )

    def _apply_region_and_clickthrough(
        self, pw: int, ph: int, label_w: int
    ) -> None:
        """Clip window to outline + label and set WS_EX_TRANSPARENT.

        Uses ctypes directly instead of pywin32 to avoid HWND type conversion
        issues. winfo_id() on the Toplevel widget returns the correct HWND.

        NOTE: Do NOT use GetAncestor(GA_ROOT) here — for tkinter Toplevels,
        GA_ROOT returns the main Tk window HWND (Toplevels are internal children
        of the Tk root on Windows), which would clip the wrong window.
        """
        try:
            import ctypes

            gdi32 = ctypes.windll.gdi32
            user32 = ctypes.windll.user32
            kernel32 = ctypes.windll.kernel32

            hwnd = int(self._toplevel.winfo_id())  # type: ignore[union-attr]
            if not hwnd:
                logger.warning("PlacementHighlightWindow: winfo_id() returned 0")
                return

            # build region: label rect + box outline (outer minus inner)
            label_rgn = gdi32.CreateRectRgn(0, 0, label_w, _LABEL_H)

            box_y = _LABEL_H
            outer = gdi32.CreateRectRgn(0, box_y, pw, box_y + ph)
            if pw > _BOX_WIDTH * 2 and ph > _BOX_WIDTH * 2:
                inner = gdi32.CreateRectRgn(
                    _BOX_WIDTH, box_y + _BOX_WIDTH,
                    pw - _BOX_WIDTH, box_y + ph - _BOX_WIDTH,
                )
                gdi32.CombineRgn(outer, outer, inner, _RGN_DIFF)
                gdi32.DeleteObject(inner)

            gdi32.CombineRgn(outer, outer, label_rgn, _RGN_OR)
            gdi32.DeleteObject(label_rgn)

            result = user32.SetWindowRgn(hwnd, outer, True)
            if result == 0:
                err = kernel32.GetLastError()
                logger.warning(
                    "SetWindowRgn returned 0 (hwnd=%d err=%d)", hwnd, err
                )
            else:
                logger.debug("SetWindowRgn ok (hwnd=%d pw=%d ph=%d)", hwnd, pw, ph)

            # WS_EX_TRANSPARENT for click-through (no WS_EX_LAYERED needed)
            ex_style = user32.GetWindowLongW(hwnd, _GWL_EXSTYLE)
            user32.SetWindowLongW(hwnd, _GWL_EXSTYLE, ex_style | _WS_EX_TRANSPARENT)

        except Exception as exc:  # noqa: BLE001
            logger.warning("SetWindowRgn failed: %s", exc)

    def _label_width(self, cell_ref: str) -> int:
        """Approximate label rectangle width in px."""
        return len(cell_ref) * 8 + _LABEL_PAD * 4

    def _cancel_dismiss(self) -> None:
        if self._dismiss_after_id is not None:
            try:
                if self._toplevel and self._toplevel.winfo_exists():
                    self._toplevel.after_cancel(self._dismiss_after_id)
            except Exception:  # noqa: BLE001
                pass
            self._dismiss_after_id = None
