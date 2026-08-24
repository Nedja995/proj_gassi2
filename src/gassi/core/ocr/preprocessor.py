"""OCR image preprocessing pipeline.

Improves RapidOCR accuracy on game HUD crops by addressing three root
problems observed in Timberborn HUD analysis:
  1. Text too small (~12px native) — upscale 3× before OCR
  2. Icon and color noise adjacent to numbers — grayscale conversion
  3. Gradient/semi-transparent backgrounds — adaptive thresholding

Pipeline is configurable per-region via OcrPreprocessConfig so games
with different HUD styles can tune independently without code changes.

All operations use OpenCV (already available via mss/numpy stack).
Pillow fallback used for upscaling if cv2 not available.
"""

import logging

import cv2
import numpy as np

logger = logging.getLogger(__name__)


class OcrPreprocessConfig:
    """Preprocessing parameters for a single HUD region.

    All parameters have defaults tuned for Timberborn's HUD style:
    small white text on dark semi-transparent backgrounds with icon noise.
    """

    def __init__(
        self,
        scale_factor: float = 3.0,
        grayscale: bool = True,
        denoise: bool = True,
        adaptive_threshold: bool = True,
        adaptive_block_size: int = 15,
        adaptive_c: int = 10,
        sharpen: bool = True,
        padding_px: int = 4,
    ) -> None:
        # upscale factor — 3.0 brings 12px text to ~36px (RapidOCR sweet spot)
        self.scale_factor = scale_factor
        # remove color noise from icons and progress bars
        self.grayscale = grayscale
        # mild Gaussian denoise before thresholding
        self.denoise = denoise
        # adaptive threshold handles gradient/semi-transparent backgrounds
        # better than global threshold
        self.adaptive_threshold = adaptive_threshold
        # must be odd; larger = handles more background variation
        self.adaptive_block_size = adaptive_block_size
        # constant subtracted from mean; higher = darker threshold
        self.adaptive_c = adaptive_c
        # unsharp mask sharpening after upscale to recover edge detail
        self.sharpen = sharpen
        # white padding around crop so text at edges isn't clipped by OCR
        self.padding_px = padding_px


# default config — tuned for Timberborn
DEFAULT_CONFIG = OcrPreprocessConfig()

# config for cycle_time_panel — cleaner background, less aggressive threshold
CYCLE_TIME_CONFIG = OcrPreprocessConfig(
    scale_factor=3.0,
    grayscale=True,
    denoise=False,        # background is cleaner, denoise adds blur
    adaptive_threshold=True,
    adaptive_block_size=11,
    adaptive_c=8,
    sharpen=True,
    padding_px=4,
)

# config for population_panel — more rows, smaller per-row text
POPULATION_CONFIG = OcrPreprocessConfig(
    scale_factor=3.0,
    grayscale=True,
    denoise=True,
    adaptive_threshold=True,
    adaptive_block_size=17,   # larger block handles the green wellness bar bg
    adaptive_c=12,
    sharpen=True,
    padding_px=6,             # extra padding — multiple rows, tight crop
)

# ── Nebuchadnezzar configs ────────────────────────────────────────────────────

# resource_bar: small white digits (~10-12px) on a dark icon strip with
# decorative separators between resource categories. Most aggressive preprocessing.
NEBU_RESOURCE_BAR_CONFIG = OcrPreprocessConfig(
    scale_factor=4.0,         # extra upscale — digits are very small
    grayscale=True,
    denoise=True,
    adaptive_threshold=True,
    adaptive_block_size=11,   # small block — tight digit spacing
    adaptive_c=6,             # lower C — digits are bright white on dark
    sharpen=True,
    padding_px=6,
)

# status_bar: treasury, month, approval%, population — medium white text on
# dark band, cleaner than resource_bar. Similar to Timberborn top_resource_bar.
NEBU_STATUS_BAR_CONFIG = OcrPreprocessConfig(
    scale_factor=3.0,
    grayscale=True,
    denoise=True,
    adaptive_threshold=True,
    adaptive_block_size=13,
    adaptive_c=8,
    sharpen=True,
    padding_px=4,
)

# objectives panel: clean white text on solid dark background, widest spacing.
# Best OCR candidate — minimal preprocessing needed.
NEBU_OBJECTIVES_CONFIG = OcrPreprocessConfig(
    scale_factor=2.5,         # slightly less upscale — text is already larger
    grayscale=True,
    denoise=False,            # background is clean, denoise adds blur unnecessarily
    adaptive_threshold=True,
    adaptive_block_size=15,
    adaptive_c=10,
    sharpen=True,
    padding_px=4,
)


def preprocess(
    image: np.ndarray,
    config: OcrPreprocessConfig | None = None,
) -> np.ndarray:
    """Apply the full preprocessing pipeline to a HUD crop.

    Args:
        image: BGR numpy array (from mss capture).
        config: preprocessing parameters. Uses DEFAULT_CONFIG if None.

    Returns:
        Preprocessed image ready for RapidOCR. Returns as BGR 3-channel
        array since RapidOCR expects BGR input regardless of content.
    """
    cfg = config or DEFAULT_CONFIG

    if image is None or image.size == 0:
        logger.warning("preprocess: received empty image")
        return image

    processed = image.copy()

    # 1. add padding so edge text isn't clipped
    if cfg.padding_px > 0:
        processed = cv2.copyMakeBorder(
            processed,
            cfg.padding_px, cfg.padding_px,
            cfg.padding_px, cfg.padding_px,
            cv2.BORDER_CONSTANT,
            value=(255, 255, 255),  # white padding
        )

    # 2. upscale — biggest single improvement for small HUD text
    if cfg.scale_factor != 1.0:
        new_w = int(processed.shape[1] * cfg.scale_factor)
        new_h = int(processed.shape[0] * cfg.scale_factor)
        processed = cv2.resize(
            processed, (new_w, new_h), interpolation=cv2.INTER_CUBIC
        )

    # 3. grayscale
    if cfg.grayscale:
        gray = cv2.cvtColor(processed, cv2.COLOR_BGR2GRAY)
    else:
        gray = cv2.cvtColor(processed, cv2.COLOR_BGR2GRAY)

    # 4. denoise
    if cfg.denoise:
        gray = cv2.GaussianBlur(gray, (3, 3), 0)

    # 5. adaptive threshold — converts to binary black/white
    if cfg.adaptive_threshold:
        block = cfg.adaptive_block_size
        # ensure odd
        if block % 2 == 0:
            block += 1
        binary = cv2.adaptiveThreshold(
            gray,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            block,
            cfg.adaptive_c,
        )
    else:
        binary = gray

    # 6. sharpen — unsharp mask to recover edge detail lost in upscale
    if cfg.sharpen:
        blurred = cv2.GaussianBlur(binary, (0, 0), sigmaX=1.0)
        binary = cv2.addWeighted(binary, 1.5, blurred, -0.5, 0)

    # convert back to BGR (RapidOCR expects 3-channel BGR)
    result = cv2.cvtColor(binary, cv2.COLOR_GRAY2BGR)

    logger.debug(
        "OCR preprocess: %s → %s (scale=%.1f)",
        image.shape[:2], result.shape[:2], cfg.scale_factor,
    )
    return result


# per-label config registry — looked up by region label at runtime
LABEL_CONFIGS: dict[str, OcrPreprocessConfig] = {
    # Timberborn
    "top_resource_bar": DEFAULT_CONFIG,
    "population_panel": POPULATION_CONFIG,
    "cycle_time_panel": CYCLE_TIME_CONFIG,
    # Nebuchadnezzar
    "resource_bar": NEBU_RESOURCE_BAR_CONFIG,
    "status_bar": NEBU_STATUS_BAR_CONFIG,
    "objectives": NEBU_OBJECTIVES_CONFIG,
}


def config_for_label(label: str) -> OcrPreprocessConfig:
    """Return the preprocessing config for a given region label.

    Falls back to DEFAULT_CONFIG for unknown labels.
    """
    return LABEL_CONFIGS.get(label, DEFAULT_CONFIG)
