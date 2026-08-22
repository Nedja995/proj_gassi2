"""Main assistant ViewModel — owns mode FSM, dispatches AI calls, updates overlay.

This is the central orchestrator. It connects:
  - CaptureBackend + CaptureRegionProvider (screen grabs)
  - RapidOcrEngine (text extraction from HUD crops)
  - AiBackend (Gemini calls)
  - GamePackLoader (prompts, manifest, hud_regions)
  - OverlayCanvas (visual output)
  - AsyncBridge (threading)
"""

import io
import logging

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
from gassi.models.results import AdvisorResult, PlacementQuery

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
        self._polling_active = False
        self._consecutive_api_failures = 0

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

    def toggle_advisor(self) -> None:
        """F1: toggle Advisor mode polling on/off."""
        if self._mode == AssistantMode.ADVISOR:
            self._stop_advisor()
        else:
            self._start_advisor()

    def switch_advisor_source(self) -> None:
        """Shift+F1: cycle advisor input source (OCR <-> SCREENSHOT)."""
        if self._input_source == AdvisorInputSource.OCR:
            self._input_source = AdvisorInputSource.SCREENSHOT
        else:
            self._input_source = AdvisorInputSource.OCR

        self._canvas.draw_status_bar(
            self._mode.value, self._input_source.value
        )
        logger.info("Advisor source switched to: %s", self._input_source.value)

    def trigger_placement(self, user_prompt: str) -> None:
        """F2: one-shot placement advice from full window screenshot."""
        self._mode = AssistantMode.PLACEMENT
        capture_rect = self._region_provider.get_capture_rect()
        frame = self._capture.grab(capture_rect)
        image_bytes = self._frame_to_png_bytes(frame)

        query = PlacementQuery(
            user_prompt=user_prompt,
            capture_rect=capture_rect,
            scale_factor=1.0,
        )

        combined_prompt = f"{user_prompt}"

        self._bridge.submit(
            self._ai.complete_with_image(
                system_prompt=self._placement_prompt,
                user_prompt=combined_prompt,
                image_bytes=image_bytes,
            ),
            on_done=self._on_placement_result,
            on_error=self._on_api_error,
        )

    # ── advisor internals ─────────────────────────────────────────────

    def _start_advisor(self) -> None:
        self._mode = AssistantMode.ADVISOR
        self._polling_active = True
        self._consecutive_api_failures = 0
        self._canvas.draw_status_bar("ADVISOR", self._input_source.value)
        self._advisor_poll_cycle()

    def _stop_advisor(self) -> None:
        self._mode = AssistantMode.IDLE
        self._polling_active = False
        self._canvas.clear_all_layers()

    def _advisor_poll_cycle(self) -> None:
        """Execute one advisor poll; reschedule if still active."""
        if not self._polling_active:
            return

        capture_rect = self._region_provider.get_capture_rect()

        for hud_region in self._manifest.hud_regions:
            cropped_rect = self._resolve_hud_region(capture_rect, hud_region)
            frame = self._capture.grab(cropped_rect)

            if self._input_source == AdvisorInputSource.OCR:
                self._process_ocr_advisor(frame, hud_region)
            else:
                self._process_screenshot_advisor(frame, hud_region)

    def _process_ocr_advisor(self, frame: np.ndarray, region: HudRegion) -> None:
        """OCR path: extract text locally, send text-only to Gemini."""
        ocr_result = self._ocr.extract(frame, region.label)

        # confidence gate: fall back to screenshot if OCR is unreliable
        if ocr_result.confidence < self._settings.ocr_confidence_threshold:
            logger.info(
                "OCR confidence %.2f below threshold for '%s', falling back to screenshot",
                ocr_result.confidence,
                region.label,
            )
            self._process_screenshot_advisor(frame, region)
            return

        user_prompt = f"HUD region '{region.label}' reads: {ocr_result.text}"

        self._bridge.submit(
            self._ai.complete_text(
                system_prompt=self._advisor_ocr_prompt,
                user_prompt=user_prompt,
            ),
            on_done=self._on_advisor_result,
            on_error=self._on_api_error,
        )

    def _process_screenshot_advisor(self, frame: np.ndarray, region: HudRegion) -> None:
        """Screenshot path: send cropped image directly to Gemini."""
        image_bytes = self._frame_to_png_bytes(frame)
        user_prompt = f"Read this HUD region '{region.label}' and provide advice."

        self._bridge.submit(
            self._ai.complete_with_image(
                system_prompt=self._advisor_screenshot_prompt,
                user_prompt=user_prompt,
                image_bytes=image_bytes,
            ),
            on_done=self._on_advisor_result,
            on_error=self._on_api_error,
        )

    # ── callbacks (run on tkinter main thread via AsyncBridge) ────────

    def _on_advisor_result(self, response_text: str) -> None:
        self._consecutive_api_failures = 0
        self._canvas.draw_text_advice(response_text, 10, 30)
        self._schedule_next_poll()

    def _on_placement_result(self, response_text: str) -> None:
        self._consecutive_api_failures = 0
        self._canvas.draw_text_advice(response_text, 10, 30)
        self._mode = AssistantMode.IDLE

    def _on_api_error(self, error: Exception) -> None:
        self._consecutive_api_failures += 1
        logger.error("API error (#%d): %s", self._consecutive_api_failures, error)

        if self._consecutive_api_failures >= self._settings.api_max_retries:
            cooldown = self._settings.api_cooldown_seconds
            self._canvas.draw_text_advice(
                f"Gemini unreachable — retrying in {cooldown:.0f}s", 10, 30
            )
            # pause polling for cooldown, then resume
            self._polling_active = False
            # TODO: schedule resume after cooldown via root.after()
        else:
            self._schedule_next_poll()

    def _schedule_next_poll(self) -> None:
        """Reschedule the next advisor poll cycle."""
        if self._polling_active:
            interval_ms = int(self._settings.advisor_poll_interval_seconds * 1000)
            self._canvas.after(interval_ms, self._advisor_poll_cycle)

    # ── helpers ───────────────────────────────────────────────────────

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
        # BGR -> RGB for PIL
        rgb = frame[:, :, ::-1]
        image = Image.fromarray(rgb)
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        return buffer.getvalue()
