"""Async-to-tkinter bridge via background thread + queue.

Runs one asyncio event loop in a daemon thread. Coroutines are submitted
from the ViewModel; results are drained into the tkinter main loop via
root.after() polling — the only thread-safe way to update tkinter widgets.
"""

import asyncio
import logging
import queue
import threading
import tkinter as tk
from collections.abc import Callable, Coroutine
from typing import Any

logger = logging.getLogger(__name__)

_POLL_INTERVAL_MS = 50


class AsyncBridge:
    """Bridge between asyncio coroutines and tkinter's main loop."""

    def __init__(self, root: tk.Tk) -> None:
        self._root = root
        self._queue: queue.Queue[tuple[Callable[..., Any], Any]] = queue.Queue()
        self._loop = asyncio.new_event_loop()

        self._thread = threading.Thread(
            target=self._run_loop,
            daemon=True,
            name="gassi-async-bridge",
        )
        self._thread.start()
        self._root.after(_POLL_INTERVAL_MS, self._poll_results)

    def _run_loop(self) -> None:
        """Run the asyncio event loop in a background thread."""
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    def submit(
        self,
        coro: Coroutine[Any, Any, Any],
        on_done: Callable[[Any], None],
        on_error: Callable[[Exception], None] | None = None,
    ) -> None:
        """Submit a coroutine for execution; callback runs on tkinter thread."""
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)

        def _handle_result(f: asyncio.Future[Any]) -> None:
            try:
                result = f.result()
                self._queue.put((on_done, result))
            except Exception as exc:
                if on_error is not None:
                    self._queue.put((on_error, exc))
                else:
                    logger.exception("Unhandled error in async task")

        future.add_done_callback(_handle_result)

    def _poll_results(self) -> None:
        """Drain completed results into tkinter callbacks (main thread)."""
        while not self._queue.empty():
            try:
                callback, value = self._queue.get_nowait()
                callback(value)
            except queue.Empty:
                break
        self._root.after(_POLL_INTERVAL_MS, self._poll_results)

    def shutdown(self) -> None:
        """Stop the background event loop cleanly."""
        self._loop.call_soon_threadsafe(self._loop.stop)
        self._thread.join(timeout=2.0)
