"""Application enumerations."""

from enum import Enum


class AssistantMode(Enum):
    """Top-level operating mode of the assistant."""

    IDLE = "idle"
    ADVISOR = "advisor"        # periodic polling — OCR or screenshot
    PLACEMENT = "placement"    # on-demand — full window screenshot + user prompt


class AdvisorInputSource(Enum):
    """Input method for Advisor mode."""

    OCR = "ocr"                # local RapidOCR -> text -> Gemini
    SCREENSHOT = "screenshot"  # cropped hud_region image -> Gemini directly
