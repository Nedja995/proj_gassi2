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
_OFFSCREEN = "-99999+-99999"
## sufficiently negative to avoid all realistic multi-monitor arrangements
#_OFFSCREEN = "-32000+-32000"


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

        # position on-screen, apply region, then lift
        self._toplevel.geometry(f"{win_w}x{win_h}+{win_x}+{win_y}")
        self._toplevel.update_idletasks()

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
        # start off-screen — no visible flash
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

        # label area: (0, 0) → (label_w, _LABEL_H)
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
        """Clip window to outline + label and set WS_EX_TRANSPARENT."""
        try:
            import win32gui   # type: ignore[import-untyped]
            import win32con   # type: ignore[import-untyped]

            hwnd = self._toplevel.winfo_id()  # type: ignore[union-attr]

            # ── build region ──────────────────────────────────────────
            # label: solid rectangle at top
            label_rgn = win32gui.CreateRectRgn(0, 0, label_w, _LABEL_H)

            # box outline: outer minus inner
            box_y = _LABEL_H
            outer = win32gui.CreateRectRgn(0, box_y, pw, box_y + ph)
            if pw > _BOX_WIDTH * 2 and ph > _BOX_WIDTH * 2:
                inner = win32gui.CreateRectRgn(
                    _BOX_WIDTH, box_y + _BOX_WIDTH,
                    pw - _BOX_WIDTH, box_y + ph - _BOX_WIDTH,
                )
                win32gui.CombineRgn(outer, outer, inner, win32con.RGN_DIFF)
                win32gui.DeleteObject(inner)

            # combine label + box outline
            win32gui.CombineRgn(outer, outer, label_rgn, win32con.RGN_OR)
            win32gui.DeleteObject(label_rgn)

            win32gui.SetWindowRgn(hwnd, outer, True)
            logger.debug("SetWindowRgn applied (hwnd=%d pw=%d ph=%d)", hwnd, pw, ph)

            # ── WS_EX_TRANSPARENT for click-through ───────────────────
            # Note: WS_EX_TRANSPARENT alone (no WS_EX_LAYERED) passes all
            # mouse messages through — no interference with transparency
            ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
            ex_style |= win32con.WS_EX_TRANSPARENT
            win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, ex_style)

        except ImportError:
            logger.debug("pywin32 not available — no region clipping or click-through")
        except Exception as exc:  # noqa: BLE001
            logger.warning("SetWindowRgn failed: %s", exc)

    def _label_width(self, cell_ref: str) -> int:
        """Approximate label rectangle width in px."""
        # Consolas 11pt ≈ 8px per char; add padding
        return len(cell_ref) * 8 + _LABEL_PAD * 4

    def _cancel_dismiss(self) -> None:
        if self._dismiss_after_id is not None:
            try:
                if self._toplevel and self._toplevel.winfo_exists():
                    self._toplevel.after_cancel(self._dismiss_after_id)
            except Exception:  # noqa: BLE001
                pass
            self._dismiss_after_id = None
