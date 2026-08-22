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
from gassi.core.game_pack_loader import GamePackLoader
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
    ) -> None:
        self._settings = settings
        self._ai = ai_backend
        self._capture = capture_backend
        self._region_provider = region_provider
        self._ocr = ocr_engine
        self._pack_loader = pack_loader
        self._canvas = canvas
        self._bridge = async_bridge

        # state
        self._mode = AssistantMode.IDLE
        self._input_source = settings.advisor_input_source
        self._busy = False
        self._last_call_time: float = 0.0
        self._cooldown_after_id: str | None = None

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

        capture_rect = self._region_provider.get_capture_rect()

        if self._input_source == AdvisorInputSource.OCR:
            self._process_ocr_advisor(capture_rect)
        else:
            self._process_screenshot_advisor(capture_rect)

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
        image_bytes = self._frame_to_png_bytes(frame)

        self._bridge.submit(
            self._ai.complete_with_image(
                system_prompt=self._placement_prompt,
                user_prompt=user_prompt,
                image_bytes=image_bytes,
            ),
            on_done=self._on_result,
            on_error=self._on_api_error,
        )

    # ── advisor internals ─────────────────────────────────────────────

    def _process_ocr_advisor(
        self, capture_rect: tuple[int, int, int, int]
    ) -> None:
        """OCR all HUD regions, combine text, send ONE call to Gemini."""
        combined_text_parts: list[str] = []
        any_low_confidence = False

        for hud_region in self._manifest.hud_regions:
            cropped_rect = self._resolve_hud_region(capture_rect, hud_region)
            frame = self._capture_without_overlay(cropped_rect)
            ocr_result = self._ocr.extract(frame, hud_region.label)

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

        # if all regions had low confidence, fall back to screenshot
        if not combined_text_parts or any_low_confidence:
            logger.info("OCR unreliable, falling back to screenshot for this cycle")
            self._process_screenshot_advisor(capture_rect)
            return

        combined_prompt = "Current HUD readings:\n" + "\n".join(combined_text_parts)

        self._bridge.submit(
            self._ai.complete_text(
                system_prompt=self._advisor_ocr_prompt,
                user_prompt=combined_prompt,
            ),
            on_done=self._on_result,
            on_error=self._on_api_error,
        )

    def _process_screenshot_advisor(
        self, capture_rect: tuple[int, int, int, int]
    ) -> None:
        """Capture full screen, send ONE image call to Gemini."""
        # Full screen capture — Gemini needs to see the entire HUD,
        # not just the overlay region which may be small/mispositioned
        frame = self._capture_without_overlay(region=None)
        image_bytes = self._frame_to_png_bytes(frame)

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
        """Check if a new query is allowed (not busy, cooldown elapsed)."""
        if self._busy:
            logger.debug("Ignored hotkey — API call in progress")
            return False

        elapsed = time.monotonic() - self._last_call_time
        remaining = self._settings.cooldown_seconds - elapsed

        if remaining > 0:
            logger.debug("Ignored hotkey — cooldown %.1fs remaining", remaining)
            self._canvas.show_advice(
                f"Cooldown: {remaining:.0f}s remaining", is_loading=True
            )
            return False

        return True

    def _start_cooldown(self) -> None:
        """Record call time and start the visible countdown on the overlay."""
        self._last_call_time = time.monotonic()
        cooldown_sec = int(self._settings.cooldown_seconds)
        self._tick_cooldown(cooldown_sec)

    def _tick_cooldown(self, remaining: int) -> None:
        """Update the cooldown display every second."""
        if remaining <= 0:
            self._canvas.update_cooldown("")
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
