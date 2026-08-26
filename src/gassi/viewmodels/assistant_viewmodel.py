"""Main assistant ViewModel — owns mode FSM, dispatches AI calls, updates overlay.

All queries are single-shot (on-demand). No automatic polling.
User presses a hotkey → one capture → one API call → one response.
A cooldown timer prevents rapid re-triggering (rate limit protection).
"""

import io
import json
import logging
import tkinter as tk
import time
from collections import deque

import numpy as np
from google.genai import types
from PIL import Image

from gassi.core.ai.protocol import AiBackend
from gassi.core.async_bridge import AsyncBridge
from gassi.core.capture.protocol import CaptureBackend, CaptureRegionProvider
from gassi.core.debug_manager import DebugManager
from gassi.core.game_pack_loader import GamePackLoader
from gassi.core.grid_overlay import cell_to_screen_pixels, draw_grid_on_frame, parse_cell_reference
from gassi.core.ocr.preprocessor import config_for_label, preprocess
from gassi.core.ocr.rapid_ocr_engine import RapidOcrEngine
from gassi.core.overlay.overlay_canvas import OverlayCanvas
from gassi.core.rag.null_backend import NullRagService
from gassi.core.rag.protocol import RagService
from gassi.core.settings_manager import load_prompt_history, save_prompt_history
from gassi.models.config import AppSettings
from gassi.models.enums import AdvisorInputSource, AssistantMode
from gassi.models.game_pack import GamePackManifest, HudRegion
from gassi.models.results import PlacementResult, UsageStats

logger = logging.getLogger(__name__)


class AssistantViewModel:
    """MVVM ViewModel — single source of truth for assistant state."""

    def __init__(
        self,
        settings: AppSettings,
        ai_backend: AiBackend,
        capture_backend: CaptureBackend,
        region_provider: CaptureRegionProvider,
        ocr_engine: RapidOcrEngine,
        pack_loader: GamePackLoader,
        canvas: OverlayCanvas,
        async_bridge: AsyncBridge,
        debug_manager: DebugManager,
        rag_service: RagService | None = None,
    ) -> None:
        self._settings = settings
        self._ai = ai_backend
        self._capture = capture_backend
        self._region_provider = region_provider
        self._ocr = ocr_engine
        self._pack_loader = pack_loader
        self._canvas = canvas
        self._bridge = async_bridge
        self._debug = debug_manager
        self._rag: RagService = rag_service if rag_service is not None else NullRagService()

        # state
        self._mode = AssistantMode.IDLE
        self._busy = False
        self._last_call_time: float = 0.0
        self._cooldown_after_id: str | None = None
        self._api_call_start_time: float = 0.0
        self._progress_after_id: str | None = None
        self._ready_colour: str = getattr(canvas._theme, "fg_accent", "#00ff88")

        # prompt history — persisted across sessions
        _saved_history = load_prompt_history()
        self._prompt_history: deque[str] = deque(_saved_history, maxlen=5)

        # session token/cost accumulators (v0.7.3)
        self._session_input_tokens: int = 0
        self._session_output_tokens: int = 0
        self._session_cost_usd: float = 0.0

        # load game pack
        self._manifest: GamePackManifest = self._pack_loader.load_manifest(
            settings.active_game_id
        )
        self._advisor_ocr_prompt = self._pack_loader.load_prompt(
            settings.active_game_id, "advisor_ocr"
        )
        self._advisor_screenshot_prompt = self._pack_loader.load_prompt(
            settings.active_game_id, "advisor_screenshot"
        )
        self._placement_prompt = self._pack_loader.load_prompt(
            settings.active_game_id, "placement"
        )

        # apply pack-level advisor source preference if set, else use global setting
        _pack_source = getattr(self._manifest, "preferred_advisor_source", None)
        if _pack_source and _pack_source in ("ocr", "screenshot"):
            self._input_source = AdvisorInputSource(_pack_source)
            logger.info(
                "Advisor source set to '%s' from game pack preference", _pack_source
            )
        else:
            self._input_source = settings.advisor_input_source

    # ── public commands (bound to hotkeys / UI buttons) ───────────────

    def trigger_advisor(self) -> None:
        """F1: single-shot advisor query."""
        if not self._can_trigger():
            return
        if not self._is_game_focused():
            logger.info(
                "Ignored hotkey — game window '%s' not in foreground",
                self._manifest.window_title_pattern,
            )
            return

        self._mode = AssistantMode.ADVISOR
        self._busy = True
        self._canvas.update_status("ADVISOR", self._input_source.value)
        self._canvas.show_advice("Capturing and analyzing...", is_loading=True)

        if self._input_source == AdvisorInputSource.OCR:
            logger.info(
                "Advisor: OCR mode — model=%s game=%s",
                self._settings.gemini_model,
                self._settings.active_game_id,
            )
            self._canvas.show_advice("Capturing HUD regions (OCR)...", is_loading=True)
            self._canvas.update_idletasks()
            self._process_ocr_advisor()
        else:
            logger.info(
                "Advisor: Screenshot mode — model=%s game=%s",
                self._settings.gemini_model,
                self._settings.active_game_id,
            )
            self._canvas.show_advice("Capturing screenshot...", is_loading=True)
            self._canvas.update_idletasks()
            self._process_screenshot_advisor()

    def switch_advisor_source(self) -> None:
        """Shift+F1: cycle advisor input source (OCR <-> SCREENSHOT)."""
        if self._input_source == AdvisorInputSource.OCR:
            self._input_source = AdvisorInputSource.SCREENSHOT
        else:
            self._input_source = AdvisorInputSource.OCR

        self._canvas.update_status(self._mode.value, self._input_source.value)
        logger.info("Advisor source switched to: %s", self._input_source.value)

    def trigger_placement(self, user_prompt: str) -> None:
        """F2: single-shot placement advice from FULL SCREEN screenshot.

        When grid_overlay_enabled, draws a coordinate grid on the frame before
        sending to Gemini and requests a structured JSON response containing
        both a cell reference and advice text.
        """
        if not self._can_trigger():
            return

        # save to history (newest first, deduplicated)
        if user_prompt in self._prompt_history:
            self._prompt_history.remove(user_prompt)
        self._prompt_history.appendleft(user_prompt)
        save_prompt_history(list(self._prompt_history))

        self._mode = AssistantMode.PLACEMENT
        self._busy = True
        self._canvas.update_status("PLACEMENT")
        self._canvas.show_advice("Capturing full screen...", is_loading=True)
        self._canvas.update_idletasks()

        # clear any previous highlight before new capture
        overlay = self._canvas.winfo_toplevel()
        if hasattr(overlay, "clear_placement_highlight"):
            overlay.clear_placement_highlight()

        # capture full primary monitor, not just the overlay region
        frame = self._capture_without_overlay(region=None)

        grid_enabled = self._settings.grid_overlay_enabled
        cols = self._settings.grid_cols
        rows = self._settings.grid_rows

        if grid_enabled:
            annotated_frame = draw_grid_on_frame(frame, cols, rows)
            self._debug.store_frame(annotated_frame, label="placement")
            image_bytes = self._frame_to_png_bytes(annotated_frame)
        else:
            self._debug.store_frame(frame, label="placement")
            image_bytes = self._frame_to_png_bytes(frame)

        logger.info(
            "Placement: model=%s game=%s grid=%s (%dx%d)",
            self._settings.gemini_model,
            self._settings.active_game_id,
            "on" if grid_enabled else "off",
            cols, rows,
        )

        _grid_note = f" + {cols}×{rows} grid" if grid_enabled else ""
        self._canvas.show_advice(
            f"✓ Screenshot captured ({frame.shape[1]}×{frame.shape[0]}px{_grid_note})\nAnalyzing with {self._settings.gemini_model}...",
            is_loading=True,
        )
        self._canvas.update_idletasks()

        response_schema = _build_placement_schema() if grid_enabled else None

        self._bridge.submit(
            self._ai.complete_with_image(
                system_prompt=self._placement_prompt,
                user_prompt=user_prompt,
                image_bytes=image_bytes,
                response_schema=response_schema,
            ),
            on_done=lambda result: self._on_placement_result(result, grid_enabled, cols, rows),
            on_error=self._on_api_error,
        )
        self._start_progress_ticker(
            f"✓ Screenshot captured ({frame.shape[1]}×{frame.shape[0]}px{_grid_note})\nAnalyzing with {self._settings.gemini_model}"
        )

    def get_prompt_suggestions(self) -> list[str]:
        """Return prompt suggestions: recent history first, then quick-prompts.

        Deduplicates — quick-prompts already in history are not repeated.
        """
        history = list(self._prompt_history)
        quick = [
            p for p in self._manifest.quick_prompts
            if p not in history
        ]
        return history + quick

    def save_debug_frame(self) -> None:
        """F4: save the last captured frame as PNG to the debug directory."""
        if not self._debug.has_frame():
            self._canvas.show_advice(
                "No frame captured yet — trigger Advisor or Placement first.",
                is_loading=False,
            )
            logger.info("Debug save requested but no frame stored")
            return

        saved_path = self._debug.save_last_frame()
        if saved_path:
            short_path = str(saved_path)
            self._canvas.show_advice(
                f"Debug frame saved:\n{short_path}", is_loading=False
            )
        else:
            self._canvas.show_advice(
                "Failed to save debug frame — check logs.", is_loading=False
            )

    # ── advisor internals ─────────────────────────────────────────────

    def _process_ocr_advisor(self) -> None:
        """OCR all HUD regions, combine text, send ONE call to Gemini."""
        # HUD region fractions are relative to the full primary monitor,
        # not the overlay window rect.
        monitor_rect = self._region_provider.get_monitor_rect()
        combined_text_parts: list[str] = []
        any_low_confidence = False
        last_frame: np.ndarray | None = None

        # hide overlay once for all region captures
        overlay = self._canvas.winfo_toplevel()
        overlay.withdraw()
        overlay.update_idletasks()
        time.sleep(0.15)

        try:
            for hud_region in self._manifest.hud_regions:
                cropped_rect = self._resolve_hud_region(monitor_rect, hud_region)
                frame = self._capture.grab(cropped_rect)
                last_frame = frame
                ocr_result = self._ocr.extract(frame, hud_region.label)
                # store preprocessed frame for F4 debug save
                preprocessed = preprocess(frame, config_for_label(hud_region.label))
                self._debug.store_frame(preprocessed, label=f"ocr_preprocessed_{hud_region.label}")

                if ocr_result.confidence < self._settings.ocr_confidence_threshold:
                    logger.info(
                        "OCR confidence %.2f below threshold for '%s'",
                        ocr_result.confidence,
                        hud_region.label,
                    )
                    any_low_confidence = True
                else:
                    combined_text_parts.append(
                        f"[{hud_region.label}]: {ocr_result.text}"
                    )
        finally:
            overlay.deiconify()
            overlay.attributes("-topmost", True)

        # store last captured region for debug frame save (F4)
        if last_frame is not None:
            self._debug.store_frame(last_frame, label="advisor_ocr")

        # if all regions had low confidence, fall back to screenshot
        if not combined_text_parts or any_low_confidence:
            logger.info("OCR unreliable, falling back to screenshot for this cycle")
            self._canvas.show_advice("OCR confidence low — switching to screenshot...", is_loading=True)
            self._canvas.update_idletasks()
            self._process_screenshot_advisor()
            return

        combined_prompt = "Current HUD readings:\n" + "\n".join(combined_text_parts)

        logger.info(
            "Advisor OCR → Gemini %s (%d regions, %d chars)",
            self._settings.gemini_model,
            len(combined_text_parts),
            len(combined_prompt),
        )
        self._canvas.show_advice(
            f"✓ HUD captured ({len(combined_text_parts)} regions)\nAnalyzing with {self._settings.gemini_model}...",
            is_loading=True,
        )
        self._canvas.update_idletasks()

        # RAG: use combined OCR text as query — most relevant knowledge for current state
        _rag_context = self._build_rag_context(combined_prompt)
        _ocr_system_prompt = _rag_context + self._advisor_ocr_prompt if _rag_context else self._advisor_ocr_prompt

        self._bridge.submit(
            self._ai.complete_text(
                system_prompt=_ocr_system_prompt,
                user_prompt=combined_prompt,
            ),
            on_done=self._on_result,
            on_error=self._on_api_error,
        )
        self._start_progress_ticker(
            f"✓ HUD captured ({len(combined_text_parts)} regions)\nAnalyzing with {self._settings.gemini_model}"
        )

    def _process_screenshot_advisor(self) -> None:
        """Capture full screen, send ONE image call to Gemini."""
        frame = self._capture_without_overlay(region=None)
        self._debug.store_frame(frame, label="advisor_screenshot")
        image_bytes = self._frame_to_png_bytes(frame)

        logger.info(
            "Advisor screenshot → Gemini %s (%dx%d px)",
            self._settings.gemini_model,
            frame.shape[1], frame.shape[0],
        )
        self._canvas.show_advice(
            f"✓ Screenshot captured ({frame.shape[1]}×{frame.shape[0]}px)\nAnalyzing with {self._settings.gemini_model}...",
            is_loading=True,
        )
        self._canvas.update_idletasks()

        # RAG: screenshot mode has no text query to embed against — skip retrieval
        if self._rag.is_available():
            logger.info("rag=off (screenshot mode — no text query available)")

        self._bridge.submit(
            self._ai.complete_with_image(
                system_prompt=self._advisor_screenshot_prompt,
                user_prompt="Read all visible HUD information and provide strategic advice.",
                image_bytes=image_bytes,
            ),
            on_done=self._on_result,
            on_error=self._on_api_error,
        )
        self._start_progress_ticker(
            f"✓ Screenshot captured ({frame.shape[1]}×{frame.shape[0]}px)\nAnalyzing with {self._settings.gemini_model}"
        )

    # ── callbacks (run on tkinter main thread via AsyncBridge) ────────

    def _on_result(self, result: tuple[str, UsageStats]) -> None:
        response_text, usage = result
        self._stop_progress_ticker()
        _elapsed = time.monotonic() - self._api_call_start_time
        logger.info("AI response received in %.1fs", _elapsed)
        self._accumulate_usage(usage)
        self._busy = False

        overlay = self._canvas.winfo_toplevel()
        _use_floating = (
            getattr(self._settings, "show_floating_advice_when_hidden", True)
            and getattr(overlay, "_offscreen", False)
            and hasattr(overlay, "show_floating_advice")
        )

        if _use_floating:
            _timeout = getattr(self._settings, "floating_advice_timeout_seconds", 12)
            overlay.show_floating_advice(  # type: ignore[union-attr]
                advice_text=response_text,
                timeout_seconds=_timeout,
            )
            logger.debug("Advisor result routed to floating window (overlay offscreen)")
        else:
            if hasattr(overlay, "auto_expand_for_result"):
                overlay.auto_expand_for_result()
            self._canvas.show_advice(response_text)

        self._start_cooldown()
        self._mode = AssistantMode.IDLE
        self._canvas.update_status("IDLE", self._input_source.value)

    def _on_placement_result(
        self,
        result: tuple[str, UsageStats],
        grid_enabled: bool,
        cols: int,
        rows: int,
    ) -> None:
        """Handle placement API response — parse cell reference when grid is on."""
        response_text, usage = result
        self._stop_progress_ticker()
        _elapsed = time.monotonic() - self._api_call_start_time
        logger.info("Placement AI response received in %.1fs", _elapsed)
        self._accumulate_usage(usage)
        self._busy = False
        overlay = self._canvas.winfo_toplevel()
        if hasattr(overlay, "auto_expand_for_result"):
            overlay.auto_expand_for_result()

        if not grid_enabled:
            # no grid — plain text response, same as advisor
            self._canvas.show_advice(response_text)
            self._start_cooldown()
            self._mode = AssistantMode.IDLE
            self._canvas.update_status("IDLE", self._input_source.value)
            return

        # grid enabled — response is JSON {cell, advice}
        result = _parse_placement_response(response_text)

        if result.cell_reference:
            monitor_rect = self._region_provider.get_monitor_rect()
            footprint = _lookup_footprint(
                result.advice_text, self._manifest.building_footprints
            )
            pixel_rect = cell_to_screen_pixels(
                result.cell_reference, monitor_rect, cols, rows,
                footprint=footprint,
            )
            if pixel_rect:
                logger.info(
                    "Placement cell %s footprint=%s → screen rect %s",
                    result.cell_reference, footprint, pixel_rect,
                )
                overlay = self._canvas.winfo_toplevel()
                if hasattr(overlay, "show_placement_highlight"):
                    auto_dismiss_ms = int(
                        getattr(self._settings, "placement_highlight_seconds", 8) * 1000
                    )
                    overlay.show_placement_highlight(
                        pixel_rect=pixel_rect,
                        cell_ref=result.cell_reference,
                        monitor_rect=monitor_rect,
                        auto_dismiss_ms=auto_dismiss_ms,
                        footprint=footprint,
                    )
            else:
                logger.warning(
                    "Cell %s could not be mapped to screen pixels",
                    result.cell_reference,
                )

            display_text = result.advice_text
            if not display_text.strip():
                display_text = f"Recommended cell: **{result.cell_reference}**"
            elif result.cell_reference not in display_text:
                display_text += f"\n\n📍 Target cell: **{result.cell_reference}**"
        else:
            display_text = result.advice_text or response_text

        self._canvas.show_advice(display_text)
        self._start_cooldown()
        self._mode = AssistantMode.IDLE
        self._canvas.update_status("IDLE", self._input_source.value)

    def _on_api_error(self, error: Exception) -> None:
        self._stop_progress_ticker()
        self._busy = False
        logger.error("API error: %s", error)
        self._canvas.show_advice(f"Error: {error}", is_loading=False)
        self._start_cooldown()
        self._mode = AssistantMode.IDLE
        self._canvas.update_status("IDLE", self._input_source.value)

    # ── cooldown / rate limiting ──────────────────────────────────────

    def _accumulate_usage(self, usage: UsageStats) -> None:
        """Add per-call token counts to session totals and update overlay footer."""
        self._session_input_tokens += usage.input_tokens
        self._session_output_tokens += usage.output_tokens
        if usage.estimated_cost_usd is not None:
            self._session_cost_usd += usage.estimated_cost_usd

        logger.debug(
            "Session totals: in=%d out=%d cost=$%.6f",
            self._session_input_tokens,
            self._session_output_tokens,
            self._session_cost_usd,
        )

        overlay = self._canvas.winfo_toplevel()
        if hasattr(overlay, "update_token_display"):
            _in_k = self._session_input_tokens / 1000
            _out_k = self._session_output_tokens / 1000
            _cost_str = f" ~${self._session_cost_usd:.4f}" if self._session_cost_usd else ""
            overlay.update_token_display(f"↑{_in_k:.1f}k ↓{_out_k:.1f}k{_cost_str}")

    def _can_trigger(self) -> bool:
        """Check if a new query is allowed (not busy, cooldown elapsed)."""
        if self._busy:
            logger.debug("Ignored hotkey — API call in progress")
            return False

        elapsed = time.monotonic() - self._last_call_time
        remaining = self._settings.cooldown_seconds - elapsed
        if remaining > 0:
            logger.debug("Ignored hotkey — cooldown %.1fs remaining", remaining)
            return False

        return True

    def _is_game_focused(self) -> bool:
        """Return True if the game window is currently in the foreground.

        Windows-only check via pywin32. Returns True on non-Windows or
        if pywin32 is not installed (fail open — don't block the hotkey).
        Falls back to True if window_title_pattern is not set in manifest.

        Also blocks triggers when GASSI's own overlay is in the foreground
        (should not happen with overrideredirect, but guards against edge cases).
        """
        pattern = getattr(self._manifest, "window_title_pattern", "") or ""
        if not pattern:
            return True

        try:
            import win32gui  # type: ignore[import-untyped]
            hwnd = win32gui.GetForegroundWindow()
            title = win32gui.GetWindowText(hwnd)
            title_lower = title.lower()

            # block if GASSI itself is somehow in foreground
            if "gassi" in title_lower:
                logger.debug("Hotkey blocked — GASSI overlay is foreground window")
                return False

            focused = pattern.lower() in title_lower
            if not focused:
                logger.debug(
                    "Hotkey blocked — foreground: '%s' (expected pattern: '%s')",
                    title, pattern,
                )
            return focused
        except Exception:  # noqa: BLE001
            return True  # fail open on any error

    def _start_cooldown(self) -> None:
        """Record call time and start the visible countdown on the overlay."""
        self._last_call_time = time.monotonic()
        cooldown_sec = int(self._settings.cooldown_seconds)
        self._tick_cooldown(cooldown_sec)

    def _start_progress_ticker(self, base_message: str) -> None:
        """Start a periodic elapsed-time ticker while an API call is in-flight.

        Updates the canvas every 5 seconds with elapsed time so the user
        knows the call is still running. Cancels itself when _busy is False.
        """
        self._api_call_start_time = time.monotonic()
        self._stop_progress_ticker()
        self._progress_base_message = base_message
        self._tick_progress()

    def _tick_progress(self) -> None:
        """Update the canvas with elapsed time. Reschedules every 5 seconds."""
        if not self._busy:
            return
        elapsed = int(time.monotonic() - self._api_call_start_time)
        dots = "." * ((elapsed // 5) % 4 + 1)
        self._canvas.show_advice(
            f"{self._progress_base_message}{dots}\n\n⏳ Waiting for AI response ({elapsed}s)",
            is_loading=True,
        )
        logger.debug("API call in-flight: %ds elapsed", elapsed)
        self._progress_after_id = self._canvas.after(5000, self._tick_progress)

    def _stop_progress_ticker(self) -> None:
        """Cancel the in-flight progress ticker."""
        if self._progress_after_id is not None:
            try:
                self._canvas.after_cancel(self._progress_after_id)
            except Exception:  # noqa: BLE001
                pass
            self._progress_after_id = None

    def _tick_cooldown(self, remaining: int) -> None:
        """Update the cooldown display every second.

        When remaining hits zero, show a green '✓ Ready' indicator briefly
        before clearing the label entirely.
        """
        if remaining <= 0:
            self._canvas.update_cooldown("✓ Ready", fg=self._ready_colour)
            self._canvas.after(1500, lambda: self._canvas.update_cooldown(""))
            return

        self._canvas.update_cooldown(f"Ready in {remaining}s")
        self._cooldown_after_id = self._canvas.after(
            1000, self._tick_cooldown, remaining - 1
        )

    # ── helpers ───────────────────────────────────────────────────

    def _build_rag_context(self, query_text: str) -> str:
        """Retrieve relevant knowledge chunks and format as a prompt context block.

        Returns an empty string when RAG is unavailable or query yields nothing,
        so callers can safely prepend it without emitting an empty section.
        """
        if not self._rag.is_available():
            return ""

        _top_k = self._manifest.rag_top_k or 3
        _min_version = self._manifest.rag_min_game_version
        _chunks = self._rag.query(
            text=query_text,
            top_k=_top_k,
            min_game_version=_min_version,
        )

        if not _chunks:
            logger.info("rag=off (no chunks returned for query)")
            return ""

        logger.info("rag=on (%d chunks retrieved)", len(_chunks))
        _lines = "\n".join(f"- {chunk}" for chunk in _chunks)
        return f"## Retrieved Knowledge\n{_lines}\n\n"

    def _capture_without_overlay(
        self, region: tuple[int, int, int, int] | None = None
    ) -> np.ndarray:
        """Hide overlay, capture the screen region, then restore overlay.

        Args:
            region: (x, y, w, h) for a specific crop, or None for full
                    primary monitor (used by F2 placement and screenshot advisor).
        """
        overlay = self._canvas.winfo_toplevel()
        overlay.withdraw()
        overlay.update_idletasks()
        time.sleep(0.15)  # wait for compositor to hide the window

        frame = self._capture.grab(region)

        overlay.deiconify()
        overlay.attributes("-topmost", True)
        return frame

    @staticmethod
    def _resolve_hud_region(
        capture_rect: tuple[int, int, int, int], region: HudRegion
    ) -> tuple[int, int, int, int]:
        """Convert fractional HudRegion to absolute screen pixels."""
        cx, cy, cw, ch = capture_rect
        return (
            cx + int(region.x_pct * cw),
            cy + int(region.y_pct * ch),
            int(region.width_pct * cw),
            int(region.height_pct * ch),
        )

    @staticmethod
    def _frame_to_png_bytes(frame: np.ndarray) -> bytes:
        """Convert a BGR numpy frame to PNG bytes for API submission."""
        rgb = frame[:, :, ::-1]
        image = Image.fromarray(rgb)
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        return buffer.getvalue()


# ── module-level helpers (no ViewModel state needed) ────────────────────────────────

def _lookup_footprint(
    advice_text: str,
    building_footprints: dict[str, list[int]],
) -> tuple[int, int] | None:
    """Scan advice text for known building keywords and return footprint.

    Performs a simple case-insensitive substring scan of the advice text
    against the manifest's building_footprints keys. Returns the first match
    as (width_cells, height_cells), or None if no match found.

    No AI call is made — this is a local keyword scan only.
    If multiple keywords match, the longest keyword wins (more specific match).
    """
    if not building_footprints or not advice_text:
        return None

    text_lower = advice_text.lower()
    best_key: str | None = None
    best_len = 0

    for keyword in building_footprints:
        if keyword.lower() in text_lower and len(keyword) > best_len:
            best_key = keyword
            best_len = len(keyword)

    if best_key is None:
        return None

    dims = building_footprints[best_key]
    if len(dims) >= 2:
        return (int(dims[0]), int(dims[1]))
    return None


def _build_placement_schema() -> types.Schema:
    """Build Gemini response_schema for structured placement response.

    Enforces: {"cell": "<letter><number>", "advice": "<markdown text>"}
    """
    return types.Schema(
        type=types.Type.OBJECT,
        properties={
            "cell": types.Schema(
                type=types.Type.STRING,
                description="Single best grid cell reference, e.g. 'D5'.",
            ),
            "advice": types.Schema(
                type=types.Type.STRING,
                description=(
                    "Markdown placement advice. 1 ## heading + 1–2 bullets. "
                    "Include the cell reference in the heading."
                ),
            ),
        },
        required=["cell", "advice"],
    )


def _parse_placement_response(response_text: str) -> PlacementResult:
    """Parse a structured JSON placement response from Gemini.

    Expected shape: {"cell": "D5", "advice": "## ..."}

    Falls back gracefully: if JSON is malformed or fields are missing,
    returns PlacementResult with advice_text set to raw response_text
    and cell_reference=None so the caller can still display something.
    """
    try:
        data = json.loads(response_text)
        raw_cell = str(data.get("cell") or "").strip()
        advice = str(data.get("advice") or "").strip()

        validated_cell = None
        if raw_cell:
            parsed = parse_cell_reference(raw_cell)
            if parsed is not None:
                validated_cell = raw_cell.upper()
            else:
                logger.warning(
                    "Gemini returned unparseable cell reference: '%s'", raw_cell
                )

        return PlacementResult(
            advice_text=advice or response_text,
            cell_reference=validated_cell,
        )

    except (json.JSONDecodeError, ValueError, TypeError) as exc:
        logger.warning("Failed to parse placement JSON response: %s", exc)
        return PlacementResult(advice_text=response_text, cell_reference=None)
