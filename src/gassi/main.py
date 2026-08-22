"""GASSI application entry point.

Wires all components together and starts the tkinter mainloop.
"""

import logging
import sys

import keyring

from gassi.core.ai.gemini_backend import GeminiBackend
from gassi.core.async_bridge import AsyncBridge
from gassi.core.capture.mss_backend import MssCaptureBackend
from gassi.core.capture.region_provider import OverlayAnchoredRegionProvider
from gassi.core.game_pack_loader import GamePackLoader
from gassi.core.hotkey_manager import HotkeyManager
from gassi.core.ocr.rapid_ocr_engine import RapidOcrEngine
from gassi.models.config import AppSettings
from gassi.viewmodels.assistant_viewmodel import AssistantViewModel
from gassi.views.main_overlay import MainOverlay

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

_KEYRING_SERVICE = "gassi"
_KEYRING_USERNAME = "gemini_api_key"


def _get_api_key() -> str:
    """Retrieve Gemini API key from OS keyring."""
    api_key = keyring.get_password(_KEYRING_SERVICE, _KEYRING_USERNAME)
    if not api_key:
        logger.error(
            "No API key found in keyring. Store one with:\n"
            "  python -c \"import keyring; "
            "keyring.set_password('gassi', 'gemini_api_key', 'YOUR_KEY')\""
        )
        sys.exit(1)
    return api_key


def main() -> None:
    """Application entry point — compose and start."""
    settings = AppSettings()

    # retrieve API key from OS credential store
    api_key = _get_api_key()

    # core components
    ai_backend = GeminiBackend(api_key=api_key, model=settings.gemini_model)
    capture_backend = MssCaptureBackend()
    ocr_engine = RapidOcrEngine()
    pack_loader = GamePackLoader()

    # UI
    overlay = MainOverlay()
    async_bridge = AsyncBridge(overlay)
    region_provider = OverlayAnchoredRegionProvider(overlay)

    # ViewModel
    viewmodel = AssistantViewModel(
        settings=settings,
        ai_backend=ai_backend,
        capture_backend=capture_backend,
        region_provider=region_provider,
        ocr_engine=ocr_engine,
        pack_loader=pack_loader,
        canvas=overlay.canvas,
        async_bridge=async_bridge,
    )

    # hotkeys
    hotkey_manager = HotkeyManager()
    hotkey_manager.register(settings.hotkey_advisor_toggle, viewmodel.toggle_advisor)
    hotkey_manager.register(settings.hotkey_advisor_source_switch, viewmodel.switch_advisor_source)
    # placement hotkey opens a simple prompt — for v1 we use a fixed test prompt
    # TODO: replace with a small input dialog or text entry widget
    hotkey_manager.register(
        settings.hotkey_placement,
        lambda: viewmodel.trigger_placement("Where should I build next?"),
    )
    hotkey_manager.start()

    # cleanup on close
    def _on_close() -> None:
        hotkey_manager.stop()
        async_bridge.shutdown()
        overlay.destroy()

    overlay.protocol("WM_DELETE_WINDOW", _on_close)

    logger.info("GASSI started — game: %s", settings.active_game_id)
    overlay.mainloop()


if __name__ == "__main__":
    main()
