from __future__ import annotations

import argparse
import base64
import sys
from pathlib import Path

import render_chapter as rc

ASSET_DIR = Path('chapter_pipeline/source_assets')
REQUIRED = {
    'lo_scarabeo_tools.jpg',
    'wyspell_candle_colors.jpg',
    'wyspell_guide_pages.jpg',
    'wyspell_in_action.jpg',
    'wyspell_kit_box.jpg',
}


def install_user_assets() -> list[str]:
    """Decode each recovered source visual directly from its companion .b64 file."""
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    installed: list[str] = []
    for name in sorted(REQUIRED):
        target = ASSET_DIR / name
        encoded_path = ASSET_DIR / f'{name}.b64'
        if not encoded_path.exists():
            raise SystemExit(f'Missing recovered source visual payload: {encoded_path}')
        encoded = ''.join(encoded_path.read_text(encoding='utf-8').split())
        encoded += '=' * (-len(encoded) % 4)
        try:
            raw = base64.b64decode(encoded, validate=True)
        except Exception as exc:
            raise SystemExit(f'Recovered source visual Base64 decode failed for {name}: {exc}') from exc
        if not raw.startswith(b'\xff\xd8\xff'):
            raise SystemExit(f'Recovered source visual is not a JPEG: {name}')
        target.write_bytes(raw)
        installed.append(name)
    print('installed recovered user source visuals:', ', '.join(installed), flush=True)
    return installed


_original_choose = rc.choose_source_asset


def choose_visual_quality_asset(text: str, asset_dir: Path) -> Path | None:
    """Prefer the user's real extracted kit imagery, then fall back to the clean/manual routing."""
    t = text.lower()
    files = {p.name.lower(): p for p in asset_dir.glob('*') if p.suffix.lower() in {'.jpg', '.jpeg', '.png', '.webp'}}

    def pick(name: str) -> Path | None:
        return files.get(name.lower())

    if any(k in t for k in ('lo scarabeo', 'calligraphic', 'calligraphy', 'quill', 'ink pot', 'sealing wax', 'wax seal')):
        p = pick('lo_scarabeo_tools.jpg')
        if p:
            return p

    wyspell_context = any(k in t for k in ('wyspell', 'colored spell candle', '36 candle', '36-candle', 'twelve colors', '12 colors'))
    if wyspell_context:
        if any(k in t for k in ('meaning', 'reference', 'guide', 'correspondence')):
            p = pick('wyspell_guide_pages.jpg')
            if p:
                return p
        if any(k in t for k in ('color', 'white', 'black', 'red', 'pink', 'orange', 'yellow', 'green', 'blue', 'purple', 'brown', 'gold', 'silver')):
            p = pick('wyspell_candle_colors.jpg')
            if p:
                return p
        if any(k in t for k in ('light', 'burn', 'flame', 'working', 'ritual', 'in action')):
            p = pick('wyspell_in_action.jpg')
            if p:
                return p
        p = pick('wyspell_kit_box.jpg')
        if p:
            return p

    return _original_choose(text, asset_dir)


def main() -> None:
    install_user_assets()
    rc.choose_source_asset = choose_visual_quality_asset
    rc.VISUAL_VERSION = 'user_source_visuals_v4'
    rc.main()


if __name__ == '__main__':
    main()
