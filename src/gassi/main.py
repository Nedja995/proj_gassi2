"""GASSI application entry point.

Wires all components together and starts the tkinter mainloop.
"""

import logging
import sys
from importlib.metadata import version as _pkg_version
from typing import Any

import keyring

from gassi.core.ai.gemini_backend import GeminiBackend
from gassi.core.async_bridge import AsyncBridge
from gassi.core.calibration_service import CalibrationService
from gassi.core.capture.mss_backend import MssCaptureBackend
from gassi.core.capture.region_provider import OverlayAnchoredRegionProvider
from gassi.core.debug_manager import DebugManager
from gassi.core.game_pack_loader import GamePackLoader
from gassi.core.hotkey_manager import HotkeyManager
from gassi.core.log_handler import OverlayLogHandler
from gassi.core.ocr.rapid_ocr_engine import RapidOcrEngine
from gassi.core.settings_manager import load_saved_settings, save_window_geometry
from gassi.core.theme.theme import THEMES, FOREST_THEME
from gassi.models.config import AppSettings
from gassi.viewmodels.assistant_viewmodel import AssistantViewModel
from gassi.views.dialogs import PlacementPromptDialog
from gassi.views.main_overlay import MainOverlay

_KEYRING_SERVICE = "gassi"
_KEYRING_USERNAME = "gemini_api_key"


def _get_api_key() -> str:
    """Retrieve Gemini API key from OS keyring."""
    api_key = keyring.get_password(_KEYRING_SERVICE, _KEYRING_USERNAME)
    if not api_key:
        logging.getLogger(__name__).error(
            "No API key found in keyring. Store one with:\n"
            "  python -c \"import keyring; "
            "keyring.set_password('gassi', 'gemini_api_key', 'YOUR_KEY')\""
        )
        sys.exit(1)
    return api_key


def main() -> None:
    """Application entry point — compose and start."""
    # ── logging setup ─────────────────────────────────────────────────
    # OverlayLogHandler must be attached BEFORE basicConfig so it captures
    # all records including those from import-time module loggers.
    overlay_log_handler = OverlayLogHandler(max_lines=200)
    overlay_log_handler.setLevel(logging.DEBUG)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            overlay_log_handler,
        ],
    )
    logger = logging.getLogger(__name__)

    # ── settings ──────────────────────────────────────────────────────
    saved = load_saved_settings()
    settings = AppSettings(**{k: v for k, v in saved.items() if not k.startswith("_")})

    theme = THEMES.get(settings.theme_name, FOREST_THEME)

    # ── API key ───────────────────────────────────────────────────────
    api_key = _get_api_key()

    # ── core components ───────────────────────────────────────────────
    ai_backend = GeminiBackend(api_key=api_key, model=settings.gemini_model)
    capture_backend = MssCaptureBackend()
    ocr_engine = RapidOcrEngine()
    pack_loader = GamePackLoader()
    debug_manager = DebugManager()
    calibration_service = CalibrationService(
        api_key=api_key,
        model=settings.gemini_model,
        capture_backend=capture_backend,
        ocr_engine=ocr_engine,
        ocr_confidence_threshold=settings.ocr_confidence_threshold,
    )

    # ── UI ────────────────────────────────────────────────────────────
    overlay = MainOverlay(theme=theme, log_handler=overlay_log_handler)

    from gassi.core.settings_manager import load_window_geometry
    saved_geometry = load_window_geometry()
    if saved_geometry:
        overlay.geometry(saved_geometry)

    async_bridge = AsyncBridge(overlay)
    region_provider = OverlayAnchoredRegionProvider(overlay)

    # ── ViewModel ─────────────────────────────────────────────────────
    viewmodel = AssistantViewModel(
        settings=settings,
        ai_backend=ai_backend,
        capture_backend=capture_backend,
        region_provider=region_provider,
        ocr_engine=ocr_engine,
        pack_loader=pack_loader,
        canvas=overlay.canvas,
        async_bridge=async_bridge,
        debug_manager=debug_manager,
    )

    # ── hotkeys ───────────────────────────────────────────────────────
    hotkey_manager = HotkeyManager()
    hotkey_manager.register(settings.hotkey_advisor_toggle, viewmodel.trigger_advisor)
    hotkey_manager.register(
        settings.hotkey_advisor_source_switch, viewmodel.switch_advisor_source
    )

    def _open_placement_dialog() -> None:
        overlay.auto_expand_for_result()
        PlacementPromptDialog(overlay, on_submit=viewmodel.trigger_placement)

    hotkey_manager.register(settings.hotkey_placement, _open_placement_dialog)
    hotkey_manager.register(settings.hotkey_lock_overlay, overlay.toggle_click_through)
    hotkey_manager.register(
        settings.hotkey_debug_save_frame, viewmodel.save_debug_frame
    )
    hotkey_manager.start()

    # ── settings save handler ─────────────────────────────────────────
    def _on_settings_saved(new_settings: dict[str, Any]) -> None:
        logger.info("Settings saved — restart required for hotkey changes")
        if "cooldown_seconds" in new_settings:
            viewmodel._settings = AppSettings(
                **{k: v for k, v in new_settings.items() if not k.startswith("_")}
            )

    overlay.set_settings_handler(_on_settings_saved)
    overlay.set_calibration_service(calibration_service, settings.active_game_id)

    # ── cleanup on close ──────────────────────────────────────────────
    def _on_close() -> None:
        save_window_geometry(overlay.geometry())
        hotkey_manager.stop()
        async_bridge.shutdown()
        overlay.destroy()

    overlay.set_close_handler(_on_close)

    logger.info(
        "GASSI v%s started — game: %s | debug frames: %s",
        _pkg_version("gassi"),
        settings.active_game_id,
        debug_manager.get_debug_dir(),
    )
    overlay.mainloop()


if __name__ == "__main__":
    main()
