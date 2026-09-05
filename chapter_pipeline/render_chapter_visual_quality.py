from __future__ import annotations

import argparse
import sys
from pathlib import Path

import render_chapter as rc
from asset_ingest import canonicalize_asset

ASSET_DIR = Path('chapter_pipeline/source_assets')
PREFLIGHT_DIR = Path('.chapter_asset_preflight_v5')
REQUIRED = {
    'lo_scarabeo_tools.jpg',
    'wyspell_candle_colors.jpg',
    'wyspell_guide_pages.jpg',
    'wyspell_in_action.jpg',
    'wyspell_kit_box.jpg',
}


def install_user_assets() -> list[str]:
    """Decode and visually validate required visuals before scene 1.

    A JPEG can be structurally readable while its recovered pixels are effectively a
    black rectangle.  v5 uses canonicalize_asset's pixel-health check so those files
    are rejected before the long render and the normal source-specific reconstruction
    path can take over instead of putting an empty card on screen.
    """
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
            print(f'preflight visual-health OK: {name} -> {clean.name}', flush=True)
        else:
            bad.append(name)
            print(f'preflight visually rejected source visual: {name}', flush=True)

    if len(good) < 3:
        raise SystemExit(
            f'Visual asset preflight stopped before render: only {len(good)} usable source visuals; bad/missing={bad}'
        )
    print(f'asset preflight passed before render: {len(good)}/{len(REQUIRED)} visually usable; rejected={bad}', flush=True)
    return good


_original_choose = rc.choose_source_asset
_vq_scene_number = 0

# Deterministic Chapter 1 showcase anchors.  They test the same representative beats
# as v4, but v5 no longer lets a merely decodable black/corrupt image pass through.
SHOWCASE_ANCHORS = {
    3: 'wyspell_kit_box.jpg',
    15: 'wyspell_in_action.jpg',
    52: 'wyspell_guide_pages.jpg',
}


def choose_visual_quality_asset(text: str, asset_dir: Path) -> Path | None:
    """Prefer real user kit imagery and guarantee representative Chapter 1 coverage."""
    global _vq_scene_number
    _vq_scene_number += 1

    t = text.lower()
    files = {p.name.lower(): p for p in asset_dir.glob('*') if p.suffix.lower() in {'.jpg', '.jpeg', '.png', '.webp'}}

    def pick(name: str) -> Path | None:
        return files.get(name.lower())

    forced = SHOWCASE_ANCHORS.get(_vq_scene_number)
    if forced:
        p = pick(forced)
        if p:
            print(f'visual coverage anchor: scene {_vq_scene_number} -> {forced}', flush=True)
            return p

    if any(k in t for k in ('lo scarabeo', 'calligraphic', 'calligraphy', 'quill', 'ink pot', 'sealing wax', 'wax seal')):
        p = pick('lo_scarabeo_tools.jpg')
        if p:
            return p

    wyspell_context = any(k in t for k in ('wyspell', 'colored spell candle', '36 candle', '36-candle', 'twelve colors', '12 colors'))
    if wyspell_context:
        if any(k in t for k in ('meaning', 'reference', 'guide', 'correspondence', 'instruction')):
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

    if any(k in t for k in ('guide', 'manual', 'reference', 'meaning', 'correspondence', 'instruction')):
        p = pick('wyspell_guide_pages.jpg')
        if p:
            return p
    if any(k in t for k in ('flame', 'burn', 'light the candle', 'candle working', 'ritual working')):
        p = pick('wyspell_in_action.jpg')
        if p:
            return p
    if any(k in t for k in ('candle kit', 'spell kit', 'candle set', 'holder', 'kit contains', 'tools in the kit')):
        p = pick('wyspell_kit_box.jpg')
        if p:
            return p

    return _original_choose(text, asset_dir)


def main() -> None:
    install_user_assets()
    rc.choose_source_asset = choose_visual_quality_asset
    rc.VISUAL_VERSION = 'user_source_visuals_v5'
    rc.main()


if __name__ == '__main__':
    main()
