"""Main assistant ViewModel — owns mode FSM, dispatches AI calls, updates overlay.

All queries are single-shot (on-demand). No automatic polling.
User presses a hotkey → one capture → one API call → one response.
A cooldown timer prevents rapid re-triggering (rate limit protection).
"""

import io
import logging
import tkinter as tk
import time

import numpy as np
from PIL import Image

from gassi.core.ai.protocol import AiBackend
from gassi.core.async_bridge import AsyncBridge
from gassi.core.capture.protocol import CaptureBackend, CaptureRegionProvider
from gassi.core.debug_manager import DebugManager
from gassi.core.game_pack_loader import GamePackLoader
from gassi.core.ocr.preprocessor import config_for_label, preprocess
from gassi.core.ocr.rapid_ocr_engine import RapidOcrEngine
from gassi.core.overlay.overlay_canvas import OverlayCanvas
from gassi.models.config import AppSettings
from gassi.models.enums import AdvisorInputSource, AssistantMode
from gassi.models.game_pack import GamePackManifest, HudRegion

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

        # state
        self._mode = AssistantMode.IDLE
        self._input_source = settings.advisor_input_source
        self._busy = False
        self._last_call_time: float = 0.0
        self._cooldown_after_id: str | None = None
        # resolve ready-indicator colour from canvas theme at construction time
        self._ready_colour: str = getattr(canvas._theme, "fg_accent", "#00ff88")

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

    # ── public commands (bound to hotkeys / UI buttons) ───────────────

    def trigger_advisor(self) -> None:
        """F1: single-shot advisor query."""
        if not self._can_trigger():
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
            self._process_ocr_advisor()
        else:
            logger.info(
                "Advisor: Screenshot mode — model=%s game=%s",
                self._settings.gemini_model,
                self._settings.active_game_id,
            )
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
        """F2: single-shot placement advice from FULL SCREEN screenshot."""
        if not self._can_trigger():
            return

        self._mode = AssistantMode.PLACEMENT
        self._busy = True
        self._canvas.update_status("PLACEMENT")
        self._canvas.show_advice("Capturing full screen...", is_loading=True)

        # capture full primary monitor, not just the overlay region
        frame = self._capture_without_overlay(region=None)
        self._debug.store_frame(frame, label="placement")
        image_bytes = self._frame_to_png_bytes(frame)

        logger.info(
            "Placement: Screenshot mode — model=%s game=%s",
            self._settings.gemini_model,
            self._settings.active_game_id,
        )

        self._bridge.submit(
            self._ai.complete_with_image(
                system_prompt=self._placement_prompt,
                user_prompt=user_prompt,
                image_bytes=image_bytes,
            ),
            on_done=self._on_result,
            on_error=self._on_api_error,
        )

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
            self._process_screenshot_advisor()
            return

        combined_prompt = "Current HUD readings:\n" + "\n".join(combined_text_parts)

        logger.info(
            "Advisor OCR → Gemini %s (%d regions, %d chars)",
            self._settings.gemini_model,
            len(combined_text_parts),
            len(combined_prompt),
        )
        self._bridge.submit(
            self._ai.complete_text(
                system_prompt=self._advisor_ocr_prompt,
                user_prompt=combined_prompt,
            ),
            on_done=self._on_result,
            on_error=self._on_api_error,
        )

    def _process_screenshot_advisor(self) -> None:
        """Capture full screen, send ONE image call to Gemini."""
        # Full screen capture — Gemini needs to see the entire HUD,
        # not just the overlay region which may be small/mispositioned
        frame = self._capture_without_overlay(region=None)
        self._debug.store_frame(frame, label="advisor_screenshot")
        image_bytes = self._frame_to_png_bytes(frame)

        logger.info(
            "Advisor screenshot → Gemini %s (%dx%d px)",
            self._settings.gemini_model,
            frame.shape[1], frame.shape[0],
        )
        self._bridge.submit(
            self._ai.complete_with_image(
                system_prompt=self._advisor_screenshot_prompt,
                user_prompt="Read all visible HUD information and provide strategic advice.",
                image_bytes=image_bytes,
            ),
            on_done=self._on_result,
            on_error=self._on_api_error,
        )

    # ── callbacks (run on tkinter main thread via AsyncBridge) ────────

    def _on_result(self, response_text: str) -> None:
        self._busy = False
        # auto-expand overlay if collapsed
        overlay = self._canvas.winfo_toplevel()
        if hasattr(overlay, "auto_expand_for_result"):
            overlay.auto_expand_for_result()
        self._canvas.show_advice(response_text)
        self._start_cooldown()
        self._mode = AssistantMode.IDLE
        self._canvas.update_status("IDLE", self._input_source.value)

    def _on_api_error(self, error: Exception) -> None:
        self._busy = False
        logger.error("API error: %s", error)
        self._canvas.show_advice(f"Error: {error}", is_loading=False)
        self._start_cooldown()
        self._mode = AssistantMode.IDLE
        self._canvas.update_status("IDLE", self._input_source.value)

    # ── cooldown / rate limiting ──────────────────────────────────────

    def _can_trigger(self) -> bool:
        """Check if a new query is allowed (not busy, cooldown elapsed,
        and the game window is in the foreground)."""
        if self._busy:
            logger.debug("Ignored hotkey — API call in progress")
            return False

        elapsed = time.monotonic() - self._last_call_time
        remaining = self._settings.cooldown_seconds - elapsed
        if remaining > 0:
            logger.debug("Ignored hotkey — cooldown %.1fs remaining", remaining)
            return False

        if not self._is_game_focused():
            logger.info(
                "Ignored hotkey — game window '%s' not in foreground",
                self._manifest.window_title_pattern,
            )
            return False

        return True

    def _is_game_focused(self) -> bool:
        """Return True if the game window is currently in the foreground.

        Windows-only check via pywin32. Returns True on non-Windows or
        if pywin32 is not installed (fail open — don't block the hotkey).
        Falls back to True if window_title_pattern is not set in manifest.
        """
        pattern = getattr(self._manifest, "window_title_pattern", "") or ""
        if not pattern:
            return True

        try:
            import win32gui  # type: ignore[import-untyped]
            hwnd = win32gui.GetForegroundWindow()
            title = win32gui.GetWindowText(hwnd)
            focused = pattern.lower() in title.lower()
            if not focused:
                logger.debug(
                    "Foreground window: '%s' (expected pattern: '%s')",
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
