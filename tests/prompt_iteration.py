"""Prompt iteration tool — run advisor/placement prompts against saved screenshots.

NOT a pytest test. Run directly with uv:

    uv run python tests/prompt_iteration.py --mode advisor_screenshot --image path/to/frame.png
    uv run python tests/prompt_iteration.py --mode advisor_ocr --hud "Day 14, water: 320/500, food: 48, pop: 12"
    uv run python tests/prompt_iteration.py --mode placement --image path/to/frame.png --question "Where should I put my next water pump?"

Reads prompts live from game_packs/timberborn/prompts/ — no restart needed after prompt edits.
Uses the same GeminiBackend as the app. API key must be in OS keyring.

Exit codes: 0 = success, 1 = error.
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

import keyring

# allow running from repo root without install
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from gassi.core.ai.gemini_backend import GeminiBackend
from gassi.core.game_pack_loader import GamePackLoader
from gassi.models.config import AppSettings

logging.basicConfig(level=logging.WARNING)

_KEYRING_SERVICE = "gassi"
_KEYRING_USERNAME = "gemini_api_key"
_GAME_ID = "timberborn"


def _load_image_bytes(image_path: str) -> bytes:
    path = Path(image_path)
    if not path.exists():
        print(f"ERROR: image not found: {path}", file=sys.stderr)
        sys.exit(1)
    return path.read_bytes()


async def _run_advisor_ocr(
    backend: GeminiBackend,
    pack_loader: GamePackLoader,
    hud_text: str,
) -> str:
    system_prompt = pack_loader.load_prompt(_GAME_ID, "advisor_ocr")
    user_prompt = f"Current HUD readings:\n{hud_text}"
    return await backend.complete_text(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
    )


async def _run_advisor_screenshot(
    backend: GeminiBackend,
    pack_loader: GamePackLoader,
    image_bytes: bytes,
) -> str:
    system_prompt = pack_loader.load_prompt(_GAME_ID, "advisor_screenshot")
    return await backend.complete_with_image(
        system_prompt=system_prompt,
        user_prompt="Read all visible HUD information and provide strategic advice.",
        image_bytes=image_bytes,
    )


async def _run_placement(
    backend: GeminiBackend,
    pack_loader: GamePackLoader,
    image_bytes: bytes,
    question: str,
) -> str:
    system_prompt = pack_loader.load_prompt(_GAME_ID, "placement")
    return await backend.complete_with_image(
        system_prompt=system_prompt,
        user_prompt=question,
        image_bytes=image_bytes,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="GASSI prompt iteration tool")
    parser.add_argument(
        "--mode",
        choices=["advisor_ocr", "advisor_screenshot", "placement"],
        required=True,
    )
    parser.add_argument("--image", help="Path to PNG/JPG screenshot")
    parser.add_argument("--hud", help="OCR HUD text (for advisor_ocr mode)")
    parser.add_argument(
        "--question",
        default="Where should I place my next building?",
        help="Placement question (for placement mode)",
    )
    parser.add_argument("--model", default="gemini-3.6-flash")
    args = parser.parse_args()

    # validate args
    if args.mode in ("advisor_screenshot", "placement") and not args.image:
        parser.error(f"--image required for mode '{args.mode}'")
    if args.mode == "advisor_ocr" and not args.hud:
        parser.error("--hud required for mode 'advisor_ocr'")

    api_key = keyring.get_password(_KEYRING_SERVICE, _KEYRING_USERNAME)
    if not api_key:
        print("ERROR: No API key in keyring.", file=sys.stderr)
        sys.exit(1)

    backend = GeminiBackend(api_key=api_key, model=args.model)
    pack_loader = GamePackLoader()

    print(f"\n{'='*60}")
    print(f"  Mode   : {args.mode}")
    print(f"  Model  : {args.model}")
    if args.image:
        print(f"  Image  : {args.image}")
    if args.hud:
        print(f"  HUD    : {args.hud[:80]}{'...' if len(args.hud) > 80 else ''}")
    if args.mode == "placement":
        print(f"  Q      : {args.question}")
    print(f"{'='*60}\n")

    try:
        if args.mode == "advisor_ocr":
            result = asyncio.run(_run_advisor_ocr(backend, pack_loader, args.hud))
        elif args.mode == "advisor_screenshot":
            image_bytes = _load_image_bytes(args.image)
            result = asyncio.run(_run_advisor_screenshot(backend, pack_loader, image_bytes))
        else:  # placement
            image_bytes = _load_image_bytes(args.image)
            result = asyncio.run(_run_placement(backend, pack_loader, image_bytes, args.question))

        print("RESPONSE:")
        print("-" * 60)
        print(result)
        print("-" * 60)
        line_count = len([l for l in result.strip().splitlines() if l.strip()])
        print(f"\nLines: {line_count}  |  Chars: {len(result)}")

    except KeyboardInterrupt:
        print("\nAborted.")
        sys.exit(0)
    except Exception as exc:
        print(f"\nERROR: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
