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
from gassi.core.rag.factory import RagServiceFactory
from gassi.core.settings_manager import load_saved_settings, save_window_geometry
from gassi.core.theme.theme import THEMES, FOREST_THEME
from gassi.models.config import AppSettings
from gassi.viewmodels.assistant_viewmodel import AssistantViewModel
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

    # ── RAG service ───────────────────────────────────────────
    _active_manifest = pack_loader.load_manifest(settings.active_game_id)
    _game_pack_path = pack_loader._packs_dir / settings.active_game_id
    rag_service = RagServiceFactory.for_game_pack(
        game_pack_path=_game_pack_path,
        collection_name=_active_manifest.rag_collection_name,
    )
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
        rag_service=rag_service,
    )

    # ── hotkeys ───────────────────────────────────────────────────────
    hotkey_manager = HotkeyManager()
    hotkey_manager.register(settings.hotkey_advisor_toggle, viewmodel.trigger_advisor)
    hotkey_manager.register(
        settings.hotkey_advisor_source_switch, viewmodel.switch_advisor_source
    )

    def _open_placement() -> None:
        suggestions = viewmodel.get_prompt_suggestions()
        overlay.after(0, lambda: overlay.toggle_placement_strip(suggestions))

    hotkey_manager.register(settings.hotkey_placement, _open_placement)
    hotkey_manager.register(
        settings.hotkey_lock_overlay,
        lambda: overlay.after(0, overlay.toggle_click_through),
    )
    hotkey_manager.register(
        settings.hotkey_debug_save_frame,
        lambda: overlay.after(0, viewmodel.save_debug_frame),
    )
    overlay.set_placement_handler(viewmodel.trigger_placement)
    hotkey_manager.start()

    # ── settings save handler ─────────────────────────────────────────
    def _on_settings_saved(new_settings: dict[str, Any]) -> None:
        prev_game = settings.active_game_id
        new_game = new_settings.get("active_game_id", prev_game)

        if new_game != prev_game:
            logger.info(
                "Active game changed: %s -> %s — restart GASSI to apply",
                prev_game, new_game,
            )
            overlay.after(
                0,
                lambda: overlay.canvas.show_advice(
                    f"## Restart required\n"
                    f"- Active game changed to **{new_game}**.\n"
                    f"- Save settings and restart GASSI to load the new pack.",
                    is_loading=False,
                ),
            )
        else:
            _hotkey_keys = {
                "hotkey_advisor_toggle",
                "hotkey_advisor_source_switch",
                "hotkey_placement",
                "hotkey_lock_overlay",
                "hotkey_debug_save_frame",
            }
            _old_hotkeys = {k: getattr(settings, k, None) for k in _hotkey_keys}
            # use old value as fallback when key absent from new_settings
            _new_hotkeys = {
                k: new_settings.get(k, getattr(settings, k, None))
                for k in _hotkey_keys
            }
            logger.debug("hotkey diff — old: %s new: %s", _old_hotkeys, _new_hotkeys)
            if _old_hotkeys != _new_hotkeys:
                logger.info("Settings saved — restart required for hotkey changes")
                overlay.after(
                    0,
                    lambda: overlay.canvas.show_advice(
                        "## Restart required\n"
                        "- Hotkey changes will take effect after restarting GASSI.",
                        is_loading=False,
                    ),
                )
            else:
                logger.info("Settings saved")

        if "cooldown_seconds" in new_settings:
            viewmodel._settings = AppSettings(
                **{k: v for k, v in new_settings.items() if not k.startswith("_")}
            )

    overlay.set_settings_handler(_on_settings_saved)
    overlay.set_calibration_service(calibration_service, settings.active_game_id, api_key)
    overlay.set_pack_loader(pack_loader)

    # ── cleanup on close ──────────────────────────────────────────────
    def _on_close() -> None:
        save_window_geometry(overlay.geometry())
        hotkey_manager.stop()
        async_bridge.shutdown()
        overlay.destroy()

    overlay.set_close_handler(_on_close)

    logger.info(
        "GASSI v%s started — game: %s (%s) | rag: %s | debug frames: %s",
        _pkg_version("gassi"),
        _active_manifest.display_name,
        settings.active_game_id,
        "on" if rag_service.is_available() else "off",
        debug_manager.get_debug_dir(),
    )
    overlay.mainloop()


if __name__ == "__main__":
    main()
