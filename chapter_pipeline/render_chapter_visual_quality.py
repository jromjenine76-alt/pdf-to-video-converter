from __future__ import annotations

import subprocess
from pathlib import Path

import render_chapter as rc
import cinematic_scene_renderer_v3 as v6
from asset_ingest import canonicalize_asset

ASSET_DIR = Path('chapter_pipeline/source_assets')
PREFLIGHT_DIR = Path('.chapter_asset_preflight_v6')
REQUIRED = {
    'lo_scarabeo_tools.jpg',
    'wyspell_candle_colors.jpg',
    'wyspell_guide_pages.jpg',
    'wyspell_in_action.jpg',
    'wyspell_kit_box.jpg',
}

_USABLE_ASSETS: set[str] = set()


def install_user_assets() -> list[str]:
    """Decode and visually validate the user-source pack before spending render time."""
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
    _USABLE_ASSETS.clear()
    _USABLE_ASSETS.update(good)
    print(f'asset preflight passed before render: {len(good)}/{len(REQUIRED)} visually usable; rejected={bad}', flush=True)
    return good


_original_choose = rc.choose_source_asset
_original_concat = rc.concat
_vq_scene_number = 0

# Only force an anchor if it passed pixel-health preflight. This prevents a known-bad
# image from being selected just to satisfy coverage bookkeeping.
SHOWCASE_ANCHORS = {
    3: 'wyspell_kit_box.jpg',
    15: 'wyspell_in_action.jpg',
    52: 'wyspell_guide_pages.jpg',
    69: 'wyspell_candle_colors.jpg',
    77: 'lo_scarabeo_tools.jpg',
}


def choose_visual_quality_asset(text: str, asset_dir: Path) -> Path | None:
    """Prefer the best matching clean source visual and fall back to the established router."""
    global _vq_scene_number
    _vq_scene_number += 1

    t = text.lower()
    files = {p.name.lower(): p for p in asset_dir.glob('*') if p.suffix.lower() in {'.jpg', '.jpeg', '.png', '.webp'}}

    def pick(name: str) -> Path | None:
        if name not in _USABLE_ASSETS:
            return None
        return files.get(name.lower())

    forced = SHOWCASE_ANCHORS.get(_vq_scene_number)
    if forced:
        p = pick(forced)
        if p:
            print(f'visual coverage anchor: scene {_vq_scene_number} -> {forced}', flush=True)
            return p

    # Writing, petitions, sigils, wax seals, and calligraphy should use the real
    # Lo Scarabeo kit when that source photo is healthy.
    if any(k in t for k in (
        'lo scarabeo', 'calligraphic', 'calligraphy', 'quill', 'ink pot', 'inkwell',
        'petition', 'write your intention', 'write the intention', 'sealing wax', 'wax seal', 'sigil', 'scribe'
    )):
        p = pick('lo_scarabeo_tools.jpg')
        if p:
            return p

    wyspell_context = any(k in t for k in (
        'wyspell', 'colored spell candle', '36 candle', '36-candle', 'twelve colors', '12 colors',
        'candle set', 'spell candle set'
    ))
    if wyspell_context:
        if any(k in t for k in ('meaning', 'reference', 'guide', 'correspondence', 'instruction', 'manual')):
            p = pick('wyspell_guide_pages.jpg')
            if p:
                return p
        if any(k in t for k in (
            'color', 'white', 'black', 'red', 'pink', 'orange', 'yellow', 'green', 'blue',
            'purple', 'brown', 'gold', 'silver', 'correspondence'
        )):
            p = pick('wyspell_candle_colors.jpg')
            if p:
                return p
        if any(k in t for k in ('light', 'burn', 'flame', 'working', 'ritual', 'in action', 'altar')):
            p = pick('wyspell_in_action.jpg')
            if p:
                return p
        p = pick('wyspell_kit_box.jpg')
        if p:
            return p

    # Generic candle-reference discussion can use the best matching WYSPELL source
    # without requiring the brand name to appear in the narration sentence.
    if any(k in t for k in ('color meaning', 'candle color', 'candle correspondence', 'colors correspond')):
        p = pick('wyspell_candle_colors.jpg')
        if p:
            return p
    if any(k in t for k in ('guide', 'manual', 'reference chart', 'reference guide')):
        p = pick('wyspell_guide_pages.jpg')
        if p:
            return p
    if any(k in t for k in ('flame', 'burning candle', 'light the candle', 'candle working', 'ritual working')):
        p = pick('wyspell_in_action.jpg')
        if p:
            return p
    if any(k in t for k in ('candle kit', 'spell kit', 'holder', 'kit contains', 'tools in the kit')):
        p = pick('wyspell_kit_box.jpg')
        if p:
            return p

    return _original_choose(text, asset_dir)


def concat_mastered(files: list[Path], target: Path) -> None:
    """Concatenate the scene files, then apply a conservative final loudness master."""
    raw = target.with_name(target.stem + '_premaster.mp4')
    _original_concat(files, raw)
    subprocess.run([
        'ffmpeg', '-y', '-v', 'error', '-i', str(raw),
        '-c:v', 'copy',
        '-af', 'loudnorm=I=-16:TP=-1.5:LRA=11',
        '-c:a', 'aac', '-b:a', '192k',
        '-movflags', '+faststart', str(target)
    ], check=True)
    raw.unlink(missing_ok=True)


def main() -> None:
    install_user_assets()

    # Keep Sarah and the chapter text pipeline untouched. Only replace the visual,
    # subtitle, motion-presentation, and final mastering layers.
    rc.choose_source_asset = choose_visual_quality_asset
    rc.make_scene = v6.make_scene
    rc.render_ken_burns = v6.render_ken_burns
    rc.render_tentpole = v6.render_tentpole
    rc.MOVES = v6.MOVES
    rc.concat = concat_mastered
    rc.VISUAL_VERSION = 'user_source_visuals_v6_render_surgery'
    rc.main()


if __name__ == '__main__':
    main()
