"""RapidOCR-based text extraction engine."""

import logging

import numpy as np
from rapidocr_onnxruntime import RapidOCR

from gassi.models.results import OcrResult

logger = logging.getLogger(__name__)


class RapidOcrEngine:
    """Local OCR using RapidOCR (ONNX runtime, CPU-only, no PyTorch).

    Designed to run on small pre-calibrated HUD region crops,
    not full screenshots — keeps CPU load negligible on low-end hardware.
    """

    def __init__(self) -> None:
        self._engine = RapidOCR()

    def extract(self, image: np.ndarray, region_label: str) -> OcrResult:
        """Run OCR on a cropped HUD region image.

        Args:
            image: BGR numpy array of the cropped region.
            region_label: identifier from the game pack's hud_regions config.

        Returns:
            OcrResult with extracted text and average confidence.
        """
        result, elapse = self._engine(image)

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

        logger.debug(
            "OCR region '%s': confidence=%.2f text='%s'",
            region_label,
            average_confidence,
            combined_text[:80],
        )

        return OcrResult(
            text=combined_text,
            confidence=average_confidence,
            region_label=region_label,
        )
