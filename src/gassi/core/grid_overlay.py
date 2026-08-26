"""Grid overlay — draws a labelled coordinate grid on a captured frame.

Used by Placement mode (v0.3.1) to give Gemini a spatial reference system
so it can return a precise cell reference (e.g. "D5") alongside advice text.

Grid convention:
    Columns: A, B, C, … (left → right), up to 26 columns (A–Z).
    Rows:    1, 2, 3, … (top → bottom).
    Cell reference format: "<col_letter><row_number>" e.g. "D5", "A1", "L8".

Design notes (AD-23):
    Canvas bounding box rendering is intentionally deferred to v0.3.2.
    This module provides:
      - draw_grid_on_frame(): annotates a copy of the frame with the grid,
        sent to Gemini so it can reason spatially.
      - cell_to_screen_pixels(): converts a cell reference to absolute screen
        pixel rect — ready for v0.3.2 canvas rendering without changes here.
      - parse_cell_reference(): validates and normalises a raw string from
        Gemini into canonical form or None if unparseable.
"""

import logging
import re

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# cell reference pattern — letter(s) followed by digits, e.g. "D5", "AB12"
_CELL_RE = re.compile(r"^([A-Za-z]+)(\d+)$")

# grid visual style
_GRID_LINE_COLOUR = (80, 80, 80)      # BGR — dark grey, subtle on most game UIs
_GRID_LABEL_COLOUR = (220, 220, 60)   # BGR — yellow, high contrast
_GRID_LINE_THICKNESS = 1
_GRID_FONT = cv2.FONT_HERSHEY_SIMPLEX
_GRID_FONT_SCALE = 0.4
_GRID_FONT_THICKNESS = 1
_LABEL_MARGIN = 3                     # px from cell edge to label text


def draw_grid_on_frame(
    frame: np.ndarray,
    cols: int,
    rows: int,
) -> np.ndarray:
    """Return a copy of frame with a labelled A–Z / 1–N grid drawn on it.

    The grid divides the frame into a uniform cols×rows grid. Column labels
    (A, B, C…) are drawn along the top edge of each cell; row labels (1, 2…)
    along the left edge. Grid lines are semi-transparent grey; labels are
    yellow for readability against varied game backgrounds.

    Args:
        frame: BGR numpy array (H, W, 3) — not modified in place.
        cols:  Number of columns (1–26).
        rows:  Number of rows (1–20).

    Returns:
        Annotated BGR frame copy.
    """
    cols = max(1, min(cols, 26))
    rows = max(1, min(rows, 20))

    output = frame.copy()
    h, w = output.shape[:2]
    cell_w = w / cols
    cell_h = h / rows

    # draw vertical grid lines + column labels
    for col_idx in range(cols):
        x = int(col_idx * cell_w)
        cv2.line(output, (x, 0), (x, h), _GRID_LINE_COLOUR, _GRID_LINE_THICKNESS)
        label = _col_label(col_idx)
        label_x = x + _LABEL_MARGIN
        label_y = int(cell_h * 0.35)  # upper third of cell
        _draw_label(output, label, label_x, label_y)

    # draw horizontal grid lines + row labels
    for row_idx in range(rows):
        y = int(row_idx * cell_h)
        cv2.line(output, (0, y), (w, y), _GRID_LINE_COLOUR, _GRID_LINE_THICKNESS)
        label = str(row_idx + 1)
        label_x = _LABEL_MARGIN
        label_y = y + int(cell_h * 0.35)
        _draw_label(output, label, label_x, label_y)

    logger.debug(
        "Grid drawn: %d cols × %d rows on %dx%d frame", cols, rows, w, h
    )
    return output


def cell_to_screen_pixels(
    cell_ref: str,
    monitor_rect: tuple[int, int, int, int],
    cols: int,
    rows: int,
    footprint: tuple[int, int] | None = None,
) -> tuple[int, int, int, int] | None:
    """Convert a cell reference to absolute screen pixel rect.

    Returns (x, y, width, height) in screen coordinates, or None if the
    cell reference is invalid or out of grid bounds.

    Args:
        cell_ref:     Canonical cell reference e.g. "D5".
        monitor_rect: (x, y, width, height) of the captured monitor area.
        cols:         Number of grid columns used when the frame was annotated.
        rows:         Number of grid rows used when the frame was annotated.
        footprint:    Optional (width_cells, height_cells) for multi-cell buildings.
                      When provided, the returned rect spans footprint_w × footprint_h
                      cells instead of 1×1. cell_ref is the top-left anchor cell.
    """
    parsed = parse_cell_reference(cell_ref)
    if parsed is None:
        return None

    col_idx, row_idx = parsed
    if col_idx >= cols or row_idx >= rows:
        logger.warning(
            "Cell %s (col=%d, row=%d) is outside grid bounds (%d×%d)",
            cell_ref, col_idx, row_idx, cols, rows,
        )
        return None

    mon_x, mon_y, mon_w, mon_h = monitor_rect
    cell_w = mon_w / cols
    cell_h = mon_h / rows

    fp_w, fp_h = footprint if footprint is not None else (1, 1)
    # clamp footprint so it doesn’t extend past grid boundary
    fp_w = min(fp_w, cols - col_idx)
    fp_h = min(fp_h, rows - row_idx)

    px = mon_x + int(col_idx * cell_w)
    py = mon_y + int(row_idx * cell_h)
    pw = int(cell_w * fp_w)
    ph = int(cell_h * fp_h)

    return (px, py, pw, ph)


def parse_cell_reference(raw: str) -> tuple[int, int] | None:
    """Parse and validate a raw cell reference string from Gemini.

    Returns (col_index, row_index) as 0-based integers, or None if the
    string cannot be parsed (wrong format, out-of-alphabet column, row < 1).

    Examples:
        "D5"  → (3, 4)
        "a1"  → (0, 0)
        "Z20" → (25, 19)
        "AA1" → None  (multi-letter columns not supported in v0.3.1)
        "D0"  → None  (rows are 1-based)
        "foo" → None
    """
    if not raw:
        return None

    match = _CELL_RE.match(raw.strip())
    if not match:
        return None

    col_str = match.group(1).upper()
    row_str = match.group(2)

    # only single-letter columns supported (A–Z = 26 max)
    if len(col_str) != 1:
        logger.debug("Multi-letter column '%s' not supported", col_str)
        return None

    col_idx = ord(col_str) - ord("A")  # 0-based
    row_num = int(row_str)
    if row_num < 1:
        return None
    row_idx = row_num - 1  # 0-based

    return (col_idx, row_idx)


# ── internal helpers ──────────────────────────────────────────────────────────

def _col_label(col_idx: int) -> str:
    """Convert 0-based column index to letter label (0→'A', 25→'Z')."""
    return chr(ord("A") + col_idx)


def _draw_label(
    frame: np.ndarray, text: str, x: int, y: int
) -> None:
    """Draw a small yellow label with a dark outline for readability."""
    # dark outline (drawn first, offset by 1px in each direction)
    for dx, dy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
        cv2.putText(
            frame, text, (x + dx, y + dy),
            _GRID_FONT, _GRID_FONT_SCALE,
            (10, 10, 10), _GRID_FONT_THICKNESS, cv2.LINE_AA,
        )
    # foreground label
    cv2.putText(
        frame, text, (x, y),
        _GRID_FONT, _GRID_FONT_SCALE,
        _GRID_LABEL_COLOUR, _GRID_FONT_THICKNESS, cv2.LINE_AA,
    )
