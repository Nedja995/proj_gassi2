"""RapidOCR-based text extraction engine with preprocessing pipeline."""

import logging

import numpy as np
from rapidocr_onnxruntime import RapidOCR

from gassi.core.ocr.preprocessor import OcrPreprocessConfig, config_for_label, preprocess
from gassi.models.results import OcrResult

logger = logging.getLogger(__name__)


class RapidOcrEngine:
    """Local OCR using RapidOCR (ONNX runtime, CPU-only, no PyTorch).

    Applies a preprocessing pipeline before OCR to handle small text,
    icon noise, and gradient backgrounds common in game HUDs.

    Designed to run on small pre-calibrated HUD region crops,
    not full screenshots — keeps CPU load negligible on low-end hardware.
    """

    def __init__(self) -> None:
        self._engine = RapidOCR()

    def extract(
        self,
        image: np.ndarray,
        region_label: str,
        preprocess_config: OcrPreprocessConfig | None = None,
    ) -> OcrResult:
        """Run preprocessing + OCR on a cropped HUD region image.

        Args:
            image: BGR numpy array of the cropped region.
            region_label: identifier from the game pack's hud_regions config.
                Used to look up the default preprocessing config for this
                region type if preprocess_config is not supplied.
            preprocess_config: explicit preprocessing config. If None,
                looks up by region_label, falls back to DEFAULT_CONFIG.

        Returns:
            OcrResult with extracted text and average confidence.
        """
        cfg = preprocess_config or config_for_label(region_label)
        processed = preprocess(image, cfg)

        result, elapse = self._engine(processed)

        if result is None or len(result) == 0:
            logger.debug("OCR returned empty for region '%s'", region_label)
            return OcrResult(text="", confidence=0.0, region_label=region_label)

        # result is list of [bbox, text, confidence]
        texts: list[str] = []
        confidences: list[float] = []
        for detection in result:
            _bbox, text, conf = detection
            texts.append(text)
            confidences.append(conf)

        combined_text = " ".join(texts)
        average_confidence = sum(confidences) / len(confidences) if confidences else 0.0

        # elapse is a list of per-stage timings from RapidOCR
        total_ms = sum(elapse) * 1000 if elapse else 0.0

        logger.info(
            "OCR region '%s': conf=%.2f text='%s' (%.0fms)",
            region_label,
            average_confidence,
            combined_text[:80],
            total_ms,
        )

        return OcrResult(
            text=combined_text,
            confidence=average_confidence,
            region_label=region_label,
        )
