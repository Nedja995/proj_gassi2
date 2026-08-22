"""Tests for the game pack loader."""

from pathlib import Path

import pytest

from gassi.core.game_pack_loader import GamePackLoader


GAME_PACKS_DIR = Path(__file__).resolve().parents[1] / "game_packs"


class TestGamePackLoader:
    def test_load_timberborn_manifest(self) -> None:
        loader = GamePackLoader(packs_dir=GAME_PACKS_DIR)
        manifest = loader.load_manifest("timberborn")
        assert manifest.game_id == "timberborn"
        assert manifest.display_name == "Timberborn"
        assert len(manifest.hud_regions) > 0

    def test_load_prompt_file(self) -> None:
        loader = GamePackLoader(packs_dir=GAME_PACKS_DIR)
        prompt = loader.load_prompt("timberborn", "advisor_ocr")
        assert "Timberborn" in prompt
        assert len(prompt) > 100

    def test_missing_manifest_raises(self) -> None:
        loader = GamePackLoader(packs_dir=GAME_PACKS_DIR)
        with pytest.raises(FileNotFoundError):
            loader.load_manifest("nonexistent_game")

    def test_missing_prompt_raises(self) -> None:
        loader = GamePackLoader(packs_dir=GAME_PACKS_DIR)
        with pytest.raises(FileNotFoundError):
            loader.load_prompt("timberborn", "nonexistent_prompt")
