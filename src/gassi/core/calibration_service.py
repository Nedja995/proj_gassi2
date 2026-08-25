"""HUD auto-calibration service.

One-shot Gemini multimodal call that detects HUD region bounding boxes
from a full screenshot and validates them via immediate OCR confidence check.

Result is persisted to game_packs/<game_id>/hud_regions_user.yaml,
which GamePackLoader checks before manifest.yaml defaults.

Design notes (AD-22):
- Uses response_schema for deterministic JSON — no regex parsing of free text.
- Each returned region is immediately OCR-validated; rejected if confidence
  below threshold or if the region is geometrically invalid.
- User calibration never overwrites manifest.yaml (developer defaults preserved).
- CalibrationService is stateless — can be called multiple times; each call
  overwrites the previous hud_regions_user.yaml.
"""

import asyncio
import io
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import yaml
from PIL import Image
from google import genai
from google.genai import types

from gassi.core.capture.mss_backend import MssCaptureBackend
from gassi.core.ocr.rapid_ocr_engine import RapidOcrEngine
from gassi.models.game_pack import HudRegion

logger = logging.getLogger(__name__)

_CALIBRATION_PROMPT = """\
You are a HUD region detector for a game assistant tool.

Analyze the screenshot and identify all distinct HUD (Heads-Up Display) regions
that contain readable text values — resource counts, population numbers, timers,
status indicators, or any numerical/textual game state information.

Exclude: decorative borders, map area, game world, tooltips, buttons without values.
Include: resource bars, population panels, day/cycle/time indicators, status panels.

For each region, return:
- label: short snake_case descriptor matching the region type. Prefer these standard
  labels when they match: top_resource_bar, population_panel, cycle_time_panel,
  objectives_panel, status_bar, resource_bar, notification_log.
  Use a descriptive custom label only if none of the above fit.
- x_pct: left edge as a DECIMAL FRACTION of total image width. MUST be between 0.0 and 1.0. NOT a percentage.
- y_pct: top edge as a DECIMAL FRACTION of total image height. MUST be between 0.0 and 1.0. NOT a percentage.
- width_pct: region width as a DECIMAL FRACTION of total image width. MUST be between 0.0 and 1.0.
- height_pct: region height as a DECIMAL FRACTION of total image height. MUST be between 0.0 and 1.0.

CRITICAL: All coordinate values MUST be decimal fractions in range 0.0–1.0.
Do NOT return percentages (e.g. 82.5 is WRONG, 0.825 is CORRECT).
Do NOT return pixel coordinates (e.g. 1200 is WRONG, 0.625 is CORRECT for a 1920px wide image).
Every region MUST have non-zero width_pct (>= 0.05) and height_pct (>= 0.02).

Add 1–2% margin (0.01–0.02) around each region so OCR has breathing room.
Return only regions you are confident contain text. Prefer fewer high-quality regions over many uncertain ones.
"""

# Gemini response schema — enforces structured JSON output
_REGION_SCHEMA = types.Schema(
    type=types.Type.OBJECT,
    properties={
        "regions": types.Schema(
            type=types.Type.ARRAY,
            items=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "label": types.Schema(type=types.Type.STRING),
                    "x_pct": types.Schema(type=types.Type.NUMBER),
                    "y_pct": types.Schema(type=types.Type.NUMBER),
                    "width_pct": types.Schema(type=types.Type.NUMBER),
                    "height_pct": types.Schema(type=types.Type.NUMBER),
                },
                required=["label", "x_pct", "y_pct", "width_pct", "height_pct"],
            ),
        )
    },
    required=["regions"],
)

_USER_REGIONS_FILENAME = "hud_regions_user.yaml"
_GAME_PACKS_DIR = Path(__file__).resolve().parents[3] / "game_packs"


@dataclass
class RegionCalibrationResult:
    """Result for a single detected region."""
    region: HudRegion
    accepted: bool
    ocr_confidence: float
    rejection_reason: str = ""


@dataclass
class CalibrationResult:
    """Full result of one calibration run."""
    game_id: str
    accepted: list[RegionCalibrationResult] = field(default_factory=list)
    rejected: list[RegionCalibrationResult] = field(default_factory=list)
    error: str = ""
    duration_seconds: float = 0.0

    @property
    def success(self) -> bool:
        return not self.error and len(self.accepted) > 0

    @property
    def summary(self) -> str:
        if self.error:
            return f"Calibration failed: {self.error}"
        return (
            f"{len(self.accepted)} regions accepted, "
            f"{len(self.rejected)} rejected "
            f"({self.duration_seconds:.1f}s)"
        )


class CalibrationService:
    """Detects and validates HUD regions via Gemini + OCR, persists result."""

    def __init__(
        self,
        api_key: str,
        model: str,
        capture_backend: MssCaptureBackend,
        ocr_engine: RapidOcrEngine,
        ocr_confidence_threshold: float = 0.3,
        packs_dir: Path | None = None,
    ) -> None:
        self._client = genai.Client(api_key=api_key)
        self._model = model
        self._capture = capture_backend
        self._ocr = ocr_engine
        self._ocr_threshold = ocr_confidence_threshold
        self._packs_dir = packs_dir or _GAME_PACKS_DIR

    def run(self, game_id: str) -> CalibrationResult:
        """Synchronous entry point — wraps async logic for tkinter callers."""
        return asyncio.run(self._run_async(game_id))

    async def _run_async(self, game_id: str) -> CalibrationResult:
        t_start = time.monotonic()
        result = CalibrationResult(game_id=game_id)

        try:
            # 1. capture full primary monitor
            logger.info("Calibration: capturing full screen for game '%s'", game_id)
            frame = self._capture.grab(region=None)
            img_h, img_w = frame.shape[:2]
            image_bytes = self._frame_to_png_bytes(frame)

            # 2. ask Gemini to detect HUD regions
            logger.info("Calibration: sending screenshot to Gemini (%dx%d)", img_w, img_h)
            raw_regions = await self._detect_regions(image_bytes)
            logger.info("Calibration: Gemini returned %d candidate regions", len(raw_regions))

            # 3. validate each region via OCR
            for raw in raw_regions:
                region_result = self._validate_region(raw, frame, img_w, img_h)
                if region_result.accepted:
                    result.accepted.append(region_result)
                    logger.info(
                        "Calibration: accepted '%s' (conf=%.2f)",
                        region_result.region.label,
                        region_result.ocr_confidence,
                    )
                else:
                    result.rejected.append(region_result)
                    logger.warning(
                        "Calibration: rejected '%s' — %s",
                        region_result.region.label,
                        region_result.rejection_reason,
                    )

            # 4. merge any manifest regions Gemini missed, then persist
            if result.accepted:
                self._save_user_regions(
                    game_id,
                    [r.region for r in result.accepted],
                )
            else:
                result.error = "No regions passed OCR validation — screenshot may not show the game HUD"

        except Exception as exc:  # noqa: BLE001
            logger.error("Calibration failed: %s", exc)
            result.error = str(exc)

        result.duration_seconds = time.monotonic() - t_start
        return result

    async def _detect_regions(self, image_bytes: bytes) -> list[dict]:
        """Send screenshot to Gemini with structured response schema."""
        image_part = types.Part.from_bytes(data=image_bytes, mime_type="image/png")
        text_part = types.Part.from_text(text="Detect all HUD regions containing readable text values.")

        response = await self._client.aio.models.generate_content(
            model=self._model,
            contents=[image_part, text_part],
            config=types.GenerateContentConfig(
                system_instruction=_CALIBRATION_PROMPT,
                response_mime_type="application/json",
                response_schema=_REGION_SCHEMA,
            ),
        )

        import json
        data = json.loads(response.text or "{}")
        return data.get("regions", [])

    def _validate_region(
        self,
        raw: dict,
        frame: np.ndarray,
        img_w: int,
        img_h: int,
    ) -> RegionCalibrationResult:
        """Validate a raw region dict via geometry check + OCR confidence.

        Handles three coordinate scales Gemini may return:
        - 0.0–1.0 decimal fractions (correct, no normalisation needed)
        - 0–100 percentages (divided by 100)
        - pixel coordinates (divided by img_w/img_h)
        Scale is determined by the maximum value across all four fields.
        After normalisation all values are clamped to [0.0, 1.0] and the
        region is passed to OCR confidence gating — no hard geometry rejection.
        """
        label = str(raw.get("label", "unknown"))

        x_pct = float(raw.get("x_pct", 0.0))
        y_pct = float(raw.get("y_pct", 0.0))
        w_pct = float(raw.get("width_pct", 0.0))
        h_pct = float(raw.get("height_pct", 0.0))

        logger.debug(
            "Calibration raw '%s': x=%.4f y=%.4f w=%.4f h=%.4f",
            label, x_pct, y_pct, w_pct, h_pct,
        )

        # Gemini may return coordinates in mixed or inconsistent scales:
        #   - pure 0.0–1.0 fractions (correct)
        #   - pure 0–100 percentages (divide all by 100)
        #   - pixel coordinates (e.g. x=1200, w=320 on a 1920px image)
        # Strategy: if ANY value looks like a percentage/pixel (> 1.0), treat
        # ALL positional values as the same scale and normalise together.
        # Use the largest value to determine the assumed scale:
        #   max > 100  → likely pixel coords, divide by img dimension
        #   max > 1.0  → likely percentage, divide by 100
        max_val = max(x_pct, y_pct, w_pct, h_pct)
        if max_val > 1.0:
            if max_val > 100.0:
                # pixel coordinates — normalise by image dimensions
                logger.debug(
                    "Calibration: normalising '%s' from pixel coords (max=%.1f)",
                    label, max_val,
                )
                x_pct = x_pct / img_w
                y_pct = y_pct / img_h
                w_pct = w_pct / img_w
                h_pct = h_pct / img_h
            else:
                # percentage scale (0–100)
                logger.debug(
                    "Calibration: normalising '%s' from 0–100 scale (max=%.1f)",
                    label, max_val,
                )
                x_pct /= 100.0
                y_pct /= 100.0
                w_pct /= 100.0
                h_pct /= 100.0

        # clamp all values to valid range — Gemini may return slightly out-of-bounds
        # coords even after normalisation (e.g. x=1.02); clamp and let OCR decide
        x_pct = max(0.0, min(x_pct, 1.0))
        y_pct = max(0.0, min(y_pct, 1.0))
        w_pct = max(0.0, min(w_pct, 1.0))
        h_pct = max(0.0, min(h_pct, 1.0))

        # ensure region fits within image bounds
        x_pct = min(x_pct, 1.0 - w_pct)
        y_pct = min(y_pct, 1.0 - h_pct)

        if w_pct < 0.01 or h_pct < 0.005:
            return RegionCalibrationResult(
                region=HudRegion(label=label, x_pct=x_pct, y_pct=y_pct,
                                 width_pct=w_pct, height_pct=h_pct),
                accepted=False, ocr_confidence=0.0,
                rejection_reason=f"region too small (w={w_pct:.3f} h={h_pct:.3f})",
            )

        # crop and OCR
        x = int(x_pct * img_w)
        y = int(y_pct * img_h)
        w = int(w_pct * img_w)
        h = int(h_pct * img_h)
        crop = frame[y: y + h, x: x + w]

        ocr_result = self._ocr.extract(crop, label)
        region = HudRegion(
            label=label, x_pct=x_pct, y_pct=y_pct,
            width_pct=w_pct, height_pct=h_pct,
        )

        if ocr_result.confidence < self._ocr_threshold:
            return RegionCalibrationResult(
                region=region, accepted=False,
                ocr_confidence=ocr_result.confidence,
                rejection_reason=(
                    f"OCR confidence {ocr_result.confidence:.2f} "
                    f"< threshold {self._ocr_threshold:.2f}"
                ),
            )

        return RegionCalibrationResult(
            region=region, accepted=True,
            ocr_confidence=ocr_result.confidence,
        )

    def _save_user_regions(self, game_id: str, regions: list[HudRegion]) -> None:
        """Write accepted regions to hud_regions_user.yaml."""
        output_path = self._packs_dir / game_id / _USER_REGIONS_FILENAME
        data = {
            "calibrated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "hud_regions": [
                {
                    "label": r.label,
                    "x_pct": round(r.x_pct, 4),
                    "y_pct": round(r.y_pct, 4),
                    "width_pct": round(r.width_pct, 4),
                    "height_pct": round(r.height_pct, 4),
                }
                for r in regions
            ],
        }
        with open(output_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True)
        logger.info("Calibration saved to: %s", output_path)

    def clear_user_calibration(self, game_id: str) -> None:
        """Delete user calibration file, reverting to manifest.yaml defaults."""
        output_path = self._packs_dir / game_id / _USER_REGIONS_FILENAME
        if output_path.exists():
            output_path.unlink()
            logger.info("User calibration cleared for game '%s'", game_id)

    @staticmethod
    def _frame_to_png_bytes(frame: np.ndarray) -> bytes:
        rgb = frame[:, :, ::-1]
        image = Image.fromarray(rgb)
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        return buffer.getvalue()
