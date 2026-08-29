"""GASSI application entry point.

Wires all components together and starts the tkinter mainloop.
"""

import logging
from importlib.metadata import version as _pkg_version, PackageNotFoundError


def _get_version() -> str:
    """Return package version, with fallback for PyInstaller frozen builds."""
    try:
        return _pkg_version("gassi")
    except PackageNotFoundError:
        return "0.9.7"  # keep in sync with pyproject.toml
from typing import Any

import keyring  # noqa: F401 — kept for type reference; actual key retrieval via factory

from gassi.core.ai.factory import build_ai_backend, get_api_key as _factory_get_api_key
from gassi.core.async_bridge import AsyncBridge
from gassi.core.calibration_service import CalibrationService
from gassi.core.capture.mss_backend import MssCaptureBackend
from gassi.core.capture.native_window_provider import NativeWindowRegionProvider
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
from gassi.models.enums import AiProvider
from gassi.viewmodels.assistant_viewmodel import AssistantViewModel
from gassi.views.main_overlay import MainOverlay

_KEYRING_USERNAME_GEMINI = "gemini_api_key"
_KEYRING_USERNAME_CLAUDE = "claude_api_key"


def _get_api_key(provider: AiProvider) -> str:
    """Retrieve API key for the active provider from OS keyring.

    Returns empty string if no key is stored — caller handles absence
    by showing an overlay message and opening Settings (v0.8.1.1).
    No longer exits on missing key so the app stays running for first-run.
    """
    return _factory_get_api_key(provider) or ""


def main() -> None:
    """Application entry point — compose and start."""
    # -- logging setup --------------------------------------------------------
    overlay_log_handler = OverlayLogHandler(max_lines=200)
    overlay_log_handler.setLevel(logging.DEBUG)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(),
            overlay_log_handler,
        ],
    )
    logger = logging.getLogger(__name__)

    # -- settings -------------------------------------------------------------
    saved = load_saved_settings()
    try:
        settings = AppSettings(
            **{k: v for k, v in saved.items() if not k.startswith("_")}
        )
    except Exception as exc:  # noqa: BLE001
        # Corrupted or incompatible settings.json — start with defaults
        logging.getLogger(__name__).warning(
            "Failed to load settings (using defaults): %s", exc
        )
        settings = AppSettings()

    theme = THEMES.get(settings.theme_name, FOREST_THEME)

    # -- API keys -------------------------------------------------------------
    api_key = _get_api_key(settings.active_ai_provider)
    # Retrieve Claude key silently for the settings dialog (may be empty string).
    # Not used at runtime unless the provider is switched to Claude.
    _claude_api_key: str = _factory_get_api_key(AiProvider.CLAUDE) or ""

    # -- core components ------------------------------------------------------
    ai_backend = build_ai_backend(settings=settings, api_key=api_key)
    capture_backend = MssCaptureBackend()
    ocr_engine = RapidOcrEngine()
    pack_loader = GamePackLoader()
    debug_manager = DebugManager()

    # -- game pack + RAG service ----------------------------------------------
    _active_manifest = pack_loader.load_manifest(settings.active_game_id)
    _game_pack_path = pack_loader._packs_dir / settings.active_game_id

    # log preferred_backend hint if set — informational only; Settings wins
    if _active_manifest.preferred_backend:
        logger.info(
            "Pack '%s' preferred_backend hint: '%s' (current: '%s' — Settings wins)",
            settings.active_game_id,
            _active_manifest.preferred_backend,
            settings.active_ai_provider.value,
        )

    rag_service = RagServiceFactory.for_game_pack(
        game_pack_path=_game_pack_path,
        collection_name=_active_manifest.rag_collection_name,
    )

    # CalibrationService always uses Gemini (multimodal + response_schema)
    _gemini_api_key_for_calib = (
        api_key
        if settings.active_ai_provider == AiProvider.GEMINI
        else (_factory_get_api_key(AiProvider.GEMINI) or "")
    )
    calibration_service = CalibrationService(
        api_key=_gemini_api_key_for_calib,
        model=settings.gemini_model,
        capture_backend=capture_backend,
        ocr_engine=ocr_engine,
        ocr_confidence_threshold=settings.ocr_confidence_threshold,
    )

    # -- UI -------------------------------------------------------------------
    overlay = MainOverlay(theme=theme, log_handler=overlay_log_handler)

    from gassi.core.settings_manager import load_window_geometry  # noqa: PLC0415
    saved_geometry = load_window_geometry()
    if saved_geometry:
        overlay.geometry(saved_geometry)

    async_bridge = AsyncBridge(overlay)
    if settings.use_native_window_detection:
        region_provider = NativeWindowRegionProvider(
            overlay=overlay,
            title_pattern=_active_manifest.window_title_pattern,
            window_class=_active_manifest.window_class,
        )
        logger.info(
            "Region provider: NativeWindowRegionProvider (title='%s', class=%r)",
            _active_manifest.window_title_pattern,
            _active_manifest.window_class,
        )
    else:
        region_provider = OverlayAnchoredRegionProvider(overlay)
        logger.info("Region provider: OverlayAnchoredRegionProvider (manual positioning)")

    # -- ViewModel ------------------------------------------------------------
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

    # -- hotkeys --------------------------------------------------------------
    hotkey_manager = HotkeyManager()
    hotkey_manager.register(settings.hotkey_advisor_toggle, viewmodel.trigger_advisor)
    hotkey_manager.register(
        settings.hotkey_advisor_source_switch, viewmodel.switch_advisor_source
    )

    def _open_placement() -> None:
        suggestions = viewmodel.get_prompt_suggestions()
        if getattr(overlay, "_offscreen", False):
            overlay.after(
                0,
                lambda: overlay.show_floating_placement_dialog(
                    suggestions, viewmodel.trigger_placement
                ),
            )
        else:
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

    # -- settings save handler ------------------------------------------------
    def _on_settings_saved(new_settings: dict[str, Any]) -> None:
        prev_game = settings.active_game_id
        new_game = new_settings.get("active_game_id", prev_game)

        if new_game != prev_game:
            logger.info(
                "Active game changed: %s -> %s — restart GASSI to apply",
                prev_game,
                new_game,
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

        # provider or backend change also requires restart
        new_provider = new_settings.get(
            "active_ai_provider", settings.active_ai_provider.value
        )
        if new_provider != settings.active_ai_provider.value:
            logger.info(
                "AI provider changed: %s -> %s — restart GASSI to apply",
                settings.active_ai_provider.value,
                new_provider,
            )
            overlay.after(
                0,
                lambda: overlay.canvas.show_advice(
                    f"## Restart required\n"
                    f"- AI provider changed to **{new_provider}**.\n"
                    f"- Restart GASSI to switch backends.",
                    is_loading=False,
                ),
            )

        if "cooldown_seconds" in new_settings:
            viewmodel._settings = AppSettings(
                **{k: v for k, v in new_settings.items() if not k.startswith("_")}
            )

        # hide_from_capture toggle: apply immediately, no restart needed (v0.8.2)
        new_hide = new_settings.get("hide_from_capture", settings.hide_from_capture)
        if new_hide != settings.hide_from_capture:
            overlay.after(
                0, lambda hide=new_hide: overlay.apply_capture_affinity_to_all(hide)
            )
            logger.info(
                "hide_from_capture toggled: %s", "on" if new_hide else "off"
            )

    overlay.set_settings_handler(_on_settings_saved)
    overlay.set_calibration_service(
        calibration_service, settings.active_game_id, _gemini_api_key_for_calib
    )
    overlay.set_claude_api_key(_claude_api_key)
    overlay.set_pack_loader(pack_loader)
    overlay.set_anticheat_note(_active_manifest.anticheat_note or "")

    # -- cleanup on close -----------------------------------------------------
    def _on_close() -> None:
        save_window_geometry(overlay.geometry())
        hotkey_manager.stop()
        async_bridge.shutdown()
        overlay.destroy()

    # v0.8.2: apply SetWindowDisplayAffinity to all overlay windows at startup.
    # Must run after mainloop starts so the HWND is mapped and winfo_id() is valid.
    overlay.after(
        200,
        lambda: overlay.apply_capture_affinity_to_all(settings.hide_from_capture),
    )

    overlay.set_close_handler(_on_close)

    logger.info(
        "GASSI v%s started — provider: %s | game: %s (%s) | rag: %s | debug: %s",
        _get_version(),
        settings.active_ai_provider.value,
        _active_manifest.display_name,
        settings.active_game_id,
        "on" if rag_service.is_available() else "off",
        debug_manager.get_debug_dir(),
    )

    # v0.8.1.1: if no API key is stored for the active provider, show overlay
    # message and auto-open Settings. Ollama is local (no key needed) — skip.
    # App continues running — no exit.
    if not api_key and settings.active_ai_provider in AiProvider.cloud_providers():
        logger.warning(
            "No API key found for provider '%s' — prompting user via Settings",
            settings.active_ai_provider.value,
        )
        overlay.after(
            0,
            lambda: overlay.canvas.show_advice(
                f"## No API key set\n"
                f"- Open Settings (\u2699) and paste your "
                f"{settings.active_ai_provider.value.capitalize()} API key.\n"
                f"- Save and restart GASSI to apply.",
                is_loading=False,
            ),
        )
        overlay.after(500, overlay._open_settings)

    overlay.mainloop()


if __name__ == "__main__":
    main()
