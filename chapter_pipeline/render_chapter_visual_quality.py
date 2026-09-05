from __future__ import annotations

import argparse
import base64
import io
import sys
import zipfile
from pathlib import Path

import render_chapter as rc

PACK = Path('chapter_pipeline/source_assets/user_visual_pack.zip.b64')
ASSET_DIR = Path('chapter_pipeline/source_assets')


def install_user_assets() -> list[str]:
    """Decode the user-extracted source pack into the runtime asset directory."""
    if not PACK.exists():
        raise SystemExit(f'Missing visual-quality asset pack: {PACK}')
    encoded = ''.join(PACK.read_text(encoding='utf-8').split())
    encoded += '=' * (-len(encoded) % 4)
    try:
        raw = base64.b64decode(encoded, validate=True)
    except Exception as exc:
        raise SystemExit(f'Visual asset pack Base64 decode failed: {exc}') from exc
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as zf:
            bad = zf.testzip()
            if bad:
                raise SystemExit(f'Visual asset pack ZIP integrity check failed at: {bad}')
            zf.extractall(ASSET_DIR)
    except zipfile.BadZipFile as exc:
        raise SystemExit(f'Visual asset pack decoded but is not a valid ZIP: {exc}') from exc
    names = sorted(p.name for p in ASSET_DIR.glob('*.jpg') if p.name.startswith(('wyspell_', 'lo_scarabeo_')))
    required = {
        'lo_scarabeo_tools.jpg',
        'wyspell_candle_colors.jpg',
        'wyspell_guide_pages.jpg',
        'wyspell_in_action.jpg',
        'wyspell_kit_box.jpg',
    }
    missing = sorted(required - set(names))
    if missing:
        raise SystemExit(f'Visual asset pack decoded but required files are missing: {missing}')
    print('installed user-extracted visual assets:', ', '.join(names), flush=True)
    return names


_original_choose = rc.choose_source_asset


def choose_visual_quality_asset(text: str, asset_dir: Path) -> Path | None:
    """Prefer the user's real extracted kit imagery, then fall back to the clean/manual routing."""
    t = text.lower()
    files = {p.name.lower(): p for p in asset_dir.glob('*') if p.suffix.lower() in {'.jpg', '.jpeg', '.png', '.webp'}}

    def pick(name: str) -> Path | None:
        return files.get(name.lower())

    # Lo Scarabeo: use the actual extracted tools when the narration discusses the kit,
    # quill, ink, seal, calligraphy, or wax tools.
    if any(k in t for k in ('lo scarabeo', 'calligraphic', 'calligraphy', 'quill', 'ink pot', 'sealing wax', 'wax seal')):
        p = pick('lo_scarabeo_tools.jpg')
        if p:
            return p

    # Wyspell: rotate real extracted product visuals according to the teaching beat.
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
