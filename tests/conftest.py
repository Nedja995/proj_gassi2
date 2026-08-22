"""Shared pytest fixtures."""

import pytest

from gassi.models.config import AppSettings
from gassi.models.game_pack import GamePackManifest, HudRegion


@pytest.fixture
def default_settings() -> AppSettings:
    """AppSettings with defaults — no env vars, no keyring."""
    return AppSettings()


@pytest.fixture
def sample_hud_region() -> HudRegion:
    return HudRegion(
        label="top_resource_bar",
        x_pct=0.15,
        y_pct=0.0,
        width_pct=0.70,
        height_pct=0.04,
    )


@pytest.fixture
def sample_manifest(sample_hud_region: HudRegion) -> GamePackManifest:
    return GamePackManifest(
        game_id="timberborn",
        display_name="Timberborn",
        window_title_pattern="Timberborn",
        game_version="0.6",
        hud_regions=[sample_hud_region],
    )
