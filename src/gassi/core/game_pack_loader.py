"""Game pack loader — reads manifest.yaml and prompt files from disk.

No dynamic plugin system. Just a folder convention + pydantic parse.

Region loading priority:
  1. game_packs/<id>/hud_regions_user.yaml  (auto-calibration result)
  2. game_packs/<id>/manifest.yaml          (developer defaults)
"""

import logging
from pathlib import Path

import yaml

from gassi.models.game_pack import GamePackManifest, HudRegion

logger = logging.getLogger(__name__)

_GAME_PACKS_DIR = Path(__file__).resolve().parents[3] / "game_packs"
_USER_REGIONS_FILENAME = "hud_regions_user.yaml"


class GamePackLoader:
    """Load a game pack by game_id from the game_packs/ directory."""

    def __init__(self, packs_dir: Path | None = None) -> None:
        self._packs_dir = packs_dir or _GAME_PACKS_DIR

    def load_manifest(self, game_id: str) -> GamePackManifest:
        """Parse manifest.yaml, then override hud_regions from user calibration if present."""
        manifest_path = self._packs_dir / game_id / "manifest.yaml"
        if not manifest_path.exists():
            raise FileNotFoundError(f"Game pack manifest not found: {manifest_path}")

        with open(manifest_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        manifest = GamePackManifest(**data)

        # override hud_regions with user calibration if available
        user_regions = self._load_user_regions(game_id)
        if user_regions:
            manifest = manifest.model_copy(update={"hud_regions": user_regions})
            logger.info(
                "Loaded game pack: %s (v%s) — using user-calibrated HUD regions (%d regions)",
                manifest.display_name,
                manifest.game_version,
                len(user_regions),
            )
        else:
            logger.info(
                "Loaded game pack: %s (v%s) — using manifest HUD regions (%d regions)",
                manifest.display_name,
                manifest.game_version,
                len(manifest.hud_regions),
            )

        return manifest

    def _load_user_regions(self, game_id: str) -> list[HudRegion] | None:
        """Load user-calibrated HUD regions if hud_regions_user.yaml exists."""
        user_path = self._packs_dir / game_id / _USER_REGIONS_FILENAME
        if not user_path.exists():
            return None

        try:
            with open(user_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)

            regions = [HudRegion(**r) for r in data.get("hud_regions", [])]
            if not regions:
                logger.warning("User calibration file exists but contains no regions: %s", user_path)
                return None

            calibrated_at = data.get("calibrated_at", "unknown")
            logger.info("User calibration loaded from %s (calibrated: %s)", user_path, calibrated_at)
            return regions

        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to load user calibration file %s: %s — using defaults", user_path, exc)
            return None

    def has_user_calibration(self, game_id: str) -> bool:
        """Return True if a user calibration file exists for this game."""
        return (self._packs_dir / game_id / _USER_REGIONS_FILENAME).exists()

    def list_available_packs(self) -> list[tuple[str, str]]:
        """Return list of (game_id, display_name) for all installed game packs.

        A valid pack is any subdirectory of game_packs/ that contains a
        manifest.yaml. Sorted alphabetically by display_name.
        """
        result: list[tuple[str, str]] = []
        if not self._packs_dir.exists():
            return result

        for entry in sorted(self._packs_dir.iterdir()):
            if not entry.is_dir():
                continue
            manifest_path = entry / "manifest.yaml"
            if not manifest_path.exists():
                continue
            try:
                with open(manifest_path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                game_id = data.get("game_id", entry.name)
                display_name = data.get("display_name", game_id)
                result.append((game_id, display_name))
            except Exception as exc:  # noqa: BLE001
                logger.warning("Skipping invalid pack at %s: %s", entry, exc)

        return sorted(result, key=lambda x: x[1])

    def load_prompt(self, game_id: str, prompt_name: str) -> str:
        """Load a prompt template file from game_packs/<game_id>/prompts/."""
        prompt_path = self._packs_dir / game_id / "prompts" / f"{prompt_name}.txt"
        if not prompt_path.exists():
            raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
        return prompt_path.read_text(encoding="utf-8")
