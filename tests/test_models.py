"""Tests for pydantic models — validation, defaults, edge cases."""

import pytest

from gassi.models.config import AppSettings
from gassi.models.enums import AdvisorInputSource, AssistantMode
from gassi.models.game_pack import GamePackManifest, HudRegion
from gassi.models.results import AdvisorResult, OcrResult, PlacementQuery, PlacementResult


class TestHudRegion:
    def test_valid_fractional_coords(self) -> None:
        region = HudRegion(label="bar", x_pct=0.1, y_pct=0.0, width_pct=0.8, height_pct=0.05)
        assert region.label == "bar"
        assert region.width_pct == 0.8

    def test_rejects_out_of_range(self) -> None:
        with pytest.raises(ValueError):
            HudRegion(label="bad", x_pct=1.5, y_pct=0.0, width_pct=0.5, height_pct=0.05)


class TestGamePackManifest:
    def test_minimal_manifest(self) -> None:
        manifest = GamePackManifest(
            game_id="test",
            display_name="Test Game",
            window_title_pattern="TestGame",
            game_version="1.0",
        )
        assert manifest.hud_regions == []
        assert manifest.rag_collection_name is None

    def test_with_hud_regions(self, sample_manifest: GamePackManifest) -> None:
        assert len(sample_manifest.hud_regions) == 1
        assert sample_manifest.hud_regions[0].label == "top_resource_bar"


class TestAppSettings:
    def test_defaults(self, default_settings: AppSettings) -> None:
        assert default_settings.gemini_model == "gemini-2.5-flash"
        assert default_settings.advisor_input_source == AdvisorInputSource.OCR
        assert default_settings.active_game_id == "timberborn"
        assert default_settings.tts_enabled is False

    def test_poll_interval_bounds(self) -> None:
        with pytest.raises(ValueError):
            AppSettings(advisor_poll_interval_seconds=0.5)


class TestAdvisorResult:
    def test_defaults(self) -> None:
        result = AdvisorResult()
        assert result.day is None
        assert result.resources == {}
        assert result.alerts == []
        assert result.advice == ""

    def test_populated(self) -> None:
        result = AdvisorResult(
            day=15, season="drought",
            resources={"water": 120, "food": 45},
            alerts=["low water"],
            advice="Build another water tank",
        )
        assert result.resources["water"] == 120


class TestOcrResult:
    def test_low_confidence(self) -> None:
        result = OcrResult(text="w4ter: ???", confidence=0.3, region_label="bar")
        assert result.confidence < 0.6


class TestPlacementQuery:
    def test_scale_factor_default(self) -> None:
        query = PlacementQuery(
            user_prompt="Where to build?",
            capture_rect=(0, 0, 1920, 1080),
        )
        assert query.scale_factor == 1.0


class TestPlacementResult:
    def test_v2_fields_default_none(self) -> None:
        result = PlacementResult(advice_text="Build east of the dam")
        assert result.target_direction is None
        assert result.target_offset_pct is None
        assert result.confidence == 1.0


class TestEnums:
    def test_mode_values(self) -> None:
        assert AssistantMode.IDLE.value == "idle"
        assert AssistantMode.ADVISOR.value == "advisor"
        assert AssistantMode.PLACEMENT.value == "placement"

    def test_source_values(self) -> None:
        assert AdvisorInputSource.OCR.value == "ocr"
        assert AdvisorInputSource.SCREENSHOT.value == "screenshot"
