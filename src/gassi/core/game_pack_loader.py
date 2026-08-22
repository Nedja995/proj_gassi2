"""Game pack loader — reads manifest.yaml and prompt files from disk.

No dynamic plugin system. Just a folder convention + pydantic parse.
"""

import logging
from pathlib import Path

import yaml

from gassi.models.game_pack import GamePackManifest

logger = logging.getLogger(__name__)

_GAME_PACKS_DIR = Path(__file__).resolve().parents[3] / "game_packs"


class GamePackLoader:
    """Load a game pack by game_id from the game_packs/ directory."""

    def __init__(self, packs_dir: Path | None = None) -> None:
        self._packs_dir = packs_dir or _GAME_PACKS_DIR

    def load_manifest(self, game_id: str) -> GamePackManifest:
        """Parse manifest.yaml for the given game pack."""
        manifest_path = self._packs_dir / game_id / "manifest.yaml"
        if not manifest_path.exists():
            raise FileNotFoundError(f"Game pack manifest not found: {manifest_path}")

        with open(manifest_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        manifest = GamePackManifest(**data)
        logger.info("Loaded game pack: %s (v%s)", manifest.display_name, manifest.game_version)
        return manifest

    def load_prompt(self, game_id: str, prompt_name: str) -> str:
        """Load a prompt template file from game_packs/<game_id>/prompts/.

        Args:
            game_id: e.g. "timberborn"
            prompt_name: e.g. "advisor_ocr" (without .txt extension)

        Returns:
            Prompt text content.
        """
        prompt_path = self._packs_dir / game_id / "prompts" / f"{prompt_name}.txt"
        if not prompt_path.exists():
            raise FileNotFoundError(f"Prompt file not found: {prompt_path}")

        return prompt_path.read_text(encoding="utf-8")
