"""In-memory log handler for the overlay log viewer panel.

Attaches to the root logger and buffers the last N formatted records
in a deque. The overlay panel polls this buffer to display log lines.

Usage:
    handler = OverlayLogHandler(max_lines=200)
    logging.getLogger().addHandler(handler)
"""

import logging
from collections import deque
from collections.abc import Iterator


class OverlayLogHandler(logging.Handler):
    """Logging handler that stores formatted records in a fixed-size deque."""

    def __init__(self, max_lines: int = 200) -> None:
        super().__init__()
        self._max_lines = max_lines
        self._buffer: deque[str] = deque(maxlen=max_lines)

        # compact formatter — fits in a narrow overlay panel
        self.setFormatter(
            logging.Formatter(
                fmt="%(asctime)s [%(levelname).1s] %(name)s: %(message)s",
                datefmt="%H:%M:%S",
            )
        )

    def emit(self, record: logging.LogRecord) -> None:
        try:
            line = self.format(record)
            self._buffer.append(line)
        except Exception:  # noqa: BLE001 — logging must never raise
            self.handleError(record)

    def get_lines(self, last_n: int | None = None) -> list[str]:
        """Return the buffered log lines, newest last.

        Args:
            last_n: if given, return only the last N lines.
        """
        lines = list(self._buffer)
        if last_n is not None:
            lines = lines[-last_n:]
        return lines

    def iter_lines(self) -> Iterator[str]:
        yield from self._buffer

    def clear(self) -> None:
        self._buffer.clear()

    @property
    def line_count(self) -> int:
        return len(self._buffer)
