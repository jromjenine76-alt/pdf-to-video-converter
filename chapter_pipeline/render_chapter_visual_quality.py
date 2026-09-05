from __future__ import annotations

import argparse
import sys
from pathlib import Path

import render_chapter as rc
from asset_ingest import canonicalize_asset

ASSET_DIR = Path('chapter_pipeline/source_assets')
PREFLIGHT_DIR = Path('.chapter_asset_preflight')
REQUIRED = {
    'lo_scarabeo_tools.jpg',
    'wyspell_candle_colors.jpg',
    'wyspell_guide_pages.jpg',
    'wyspell_in_action.jpg',
    'wyspell_kit_box.jpg',
}


def install_user_assets() -> list[str]:
    """Fully decode/salvage required visuals before scene 1 so a bad JPEG cannot fail mid-render."""
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    good: list[str] = []
    bad: list[str] = []
    for name in sorted(REQUIRED):
        target = ASSET_DIR / name
        if not target.exists():
            bad.append(name)
            print(f'preflight missing source visual: {name}', flush=True)
            continue
        clean = canonicalize_asset(target, PREFLIGHT_DIR)
        if clean:
            good.append(name)
            print(f'preflight OK: {name} -> {clean.name}', flush=True)
        else:
            bad.append(name)
            print(f'preflight rejected source visual: {name}', flush=True)

    # The workflow gate requires at least three real user visuals. Detect that immediately,
    # before TTS and video rendering consume minutes/hours.
    if len(good) < 3:
        raise SystemExit(
            f'Visual asset preflight stopped before render: only {len(good)} usable source visuals; bad/missing={bad}'
        )
    print(f'asset preflight passed before render: {len(good)}/{len(REQUIRED)} usable', flush=True)
    return good


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
