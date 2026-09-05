from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

from kokoro_onnx import Kokoro
from kokoro_tts import clean, digest_for, synthesize
from cinematic_scene_renderer_v2 import MOVES, make_scene, render_ken_burns, render_tentpole
from source_visual_reconstructions import reconstruct_source_visual
from asset_ingest import canonicalize_asset

VISUAL_VERSION = 'source_reconstruction_v3'


def run(*args: str) -> None:
    subprocess.run(list(args), check=True)


def concat(files: list[Path], target: Path) -> None:
    listing = target.with_suffix('.concat.txt')
    listing.write_text(''.join(f"file '{p.resolve().as_posix()}'\n" for p in files), encoding='utf-8')
    run('ffmpeg', '-y', '-v', 'error', '-f', 'concat', '-safe', '0', '-i', str(listing), '-c', 'copy', '-movflags', '+faststart', str(target))


def load_voice_config(path: Path) -> dict:
    cfg = json.loads(path.read_text(encoding='utf-8'))
    if cfg.get('provider') != 'kokoro':
        raise SystemExit('Final Spellcraft pipeline requires the locked Kokoro provider')
    if not cfg.get('approved') or not cfg.get('locked'):
        raise SystemExit('Voice configuration is not approved and locked')
    if cfg.get('voice') != 'af_sarah':
        raise SystemExit('Final Spellcraft voice is locked to af_sarah')
    return cfg


def sentence_beats(text: str) -> list[str]:
    """Keep the narration bible intact while producing one picture beat per spoken sentence."""
    text = clean(text)
    raw = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if s.strip()]
    out: list[str] = []
    pending = ''
    for s in raw:
        candidate = (pending + ' ' + s).strip() if pending else s
        if len(candidate) < 70:
            pending = candidate
            continue
        out.append(candidate)
        pending = ''
    if pending:
        if out and len(pending) < 45:
            out[-1] = (out[-1] + ' ' + pending).strip()
        else:
            out.append(pending)
    return out


def choose_source_asset(text: str, asset_dir: Path) -> Path | None:
    """Use only isolated clean source images. Never use a whole PDF page as the presentation."""
    if not asset_dir.exists():
        return None
    files = {p.name.lower(): p for p in asset_dir.iterdir() if p.suffix.lower() in {'.jpg', '.jpeg', '.png', '.webp'}}
    t = text.lower()
    rules = [
        (('complete manifestation', 'master edition', 'spellcraft manual'), 'page001_cover.jpg'),
        (('soul sticks', 'gambling manifesting intention kit'), 'page019_soul_sticks_kit.jpg'),
        (('wyspell 36', 'wyspell kit'), 'page020_wyspell_kit.jpg'),
        (('12 colors', 'color chart', 'colored spell candle', 'candle colors'), 'page021_wyspell_color_chart.jpg'),
        (('lo scarabeo', 'calligraphic ritual kit'), 'page022_lo_scarabeo_kit.jpg'),
        (('single-candle', 'single candle focus'), 'page038_single_candle_focus.jpg'),
        (('flanking pair',), 'page039_flanking_pair.jpg'),
        (('triangle',), 'page040_triangle_apex.jpg'),
        (('cross', 'cardinal alignment'), 'page041_cross_alignment.jpg'),
        (('square', 'foundation'), 'page042_square_foundation.jpg'),
        (('pentagram',), 'page043_pentagram.jpg'),
        (('hexagram', 'starseed'), 'page044_starseed_hexagram.jpg'),
        (('ring of fire', 'containment circle'), 'page045_ring_of_fire.jpg'),
    ]
    for keys, name in rules:
        if any(k in t for k in keys) and name.lower() in files:
            return files[name.lower()]
    return None


def tentpole_indices(count: int) -> set[int]:
    """More frequent motion beats than the first proof, while keeping long-form rendering practical."""
    if count <= 3:
        return set(range(count))
    out = {0, count // 2, count - 1}
    out.update(range(14, count, 15))
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--catalog', type=Path, default=Path('chapter_pipeline/catalog.json'))
    ap.add_argument('--chapter', type=int, required=True)
    ap.add_argument('--output-dir', type=Path, default=Path('chapter_output'))
    ap.add_argument('--cache-dir', type=Path, default=Path('.chapter_cache'))
    ap.add_argument('--voice-config', type=Path, default=Path('chapter_pipeline/VOICE_CONFIG.json'))
    ap.add_argument('--kokoro-model', type=Path, default=Path('.kokoro/kokoro-v1.0.onnx'))
    ap.add_argument('--kokoro-voices', type=Path, default=Path('.kokoro/voices-v1.0.bin'))
    ap.add_argument('--asset-dir', type=Path, default=Path('chapter_pipeline/source_assets'))
    args = ap.parse_args()

    cfg = load_voice_config(args.voice_config)
    voice = str(cfg['voice'])
    speed = float(cfg.get('speed', 0.96))
    lang = str(cfg.get('language', 'en-us'))

    if not args.kokoro_model.exists() or not args.kokoro_voices.exists():
        raise SystemExit('Kokoro model files are missing; final narration cannot continue')

    data = json.loads(args.catalog.read_text(encoding='utf-8'))
    chapter = next(c for c in data['chapters'] if int(c['id']) == args.chapter)
    title = chapter['title']
    text = '\n\n'.join(s['text'] for s in chapter['sections'])
    beats = sentence_beats(text)
    if not beats:
        raise SystemExit('No narration beats found for chapter')
    print(f'chapter {args.chapter}: {len(beats)} Sarah-locked sentence scenes / visual {VISUAL_VERSION}', flush=True)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    audio_dir = args.cache_dir / 'audio'
    still_dir = args.cache_dir / 'stills_v3'
    video_dir = args.cache_dir / 'video_v3'
    recon_dir = args.cache_dir / 'source_reconstructions_v3'
    sanitized_dir = args.cache_dir / 'sanitized_source_assets'
    for d in (audio_dir, still_dir, video_dir, recon_dir, sanitized_dir):
        d.mkdir(parents=True, exist_ok=True)

    kokoro = Kokoro(str(args.kokoro_model), str(args.kokoro_voices))
    available = set(kokoro.get_voices())
    if voice not in available:
        raise SystemExit(f'Locked voice {voice!r} is not available in this Kokoro voice pack')

    tents = tentpole_indices(len(beats))
    videos: list[Path] = []
    audio_files: list[str] = []
    scene_kinds: list[str] = []
    real_assets_used: list[str] = []
    rejected_source_assets: list[str] = []
    reconstructions_used: list[str] = []
    animated_reconstructions: set[str] = set()
    dynamic_scene_count = 0

    for i, beat in enumerate(beats):
        scene_no = i + 1
        digest = digest_for(beat, voice, speed)
        audio_stem = f'c{args.chapter:03d}_s{scene_no:04d}_{voice}_{digest}'
        visual_stem = f'c{args.chapter:03d}_s{scene_no:04d}_v3_{digest}'
        wav = audio_dir / f'{audio_stem}.wav'
        still = still_dir / f'{visual_stem}.jpg'
        mp4 = video_dir / f'{visual_stem}.mp4'

        if not (wav.exists() and wav.stat().st_size > 1000):
            synthesize(kokoro, beat, wav, voice=voice, speed=speed, lang=lang)
        audio_files.append(wav.name)

        source_asset = choose_source_asset(beat, args.asset_dir)
        asset: Path | None = None
        recon_key: str | None = None
        source_label = 'cinematic-fill'

        if source_asset:
            clean_asset = canonicalize_asset(source_asset, sanitized_dir)
            if clean_asset:
                asset = clean_asset
                real_assets_used.append(source_asset.name)
                source_label = f'pdf-source:{source_asset.name}'
            else:
                rejected_source_assets.append(source_asset.name)

        if not asset:
            asset, recon_key = reconstruct_source_visual(beat, recon_dir)
            if recon_key:
                reconstructions_used.append(recon_key)
                source_label = f'reconstruction:{recon_key}'

        kind = make_scene(beat, scene_no, still, asset=asset)
        scene_kinds.append(kind)

        first_reconstruction_motion = bool(recon_key and recon_key not in animated_reconstructions)
        use_dynamic_motion = i in tents or first_reconstruction_motion
        if first_reconstruction_motion and recon_key:
            animated_reconstructions.add(recon_key)

        if not (mp4.exists() and mp4.stat().st_size > 10000):
            if use_dynamic_motion:
                render_tentpole(still, wav, beat, mp4, kind, seed=args.chapter*1000 + scene_no)
            else:
                render_ken_burns(still, wav, beat, mp4, move=MOVES[i % len(MOVES)])

        if use_dynamic_motion:
            dynamic_scene_count += 1
        videos.append(mp4)
        motion = 'object-motion tentpole' if use_dynamic_motion else MOVES[i % len(MOVES)]
        print(f'scene {scene_no}/{len(beats)} complete: {kind} / {motion} / {source_label} / locked {voice}', flush=True)

    if args.chapter == 1 and not real_assets_used and not reconstructions_used:
        raise SystemExit('Chapter 1 visual QA failed: no clean source assets or source-specific reconstructions were used')

    final = args.output_dir / f'chapter_{args.chapter:03d}.mp4'
    concat(videos, final)
    probe = subprocess.check_output([
        'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1', str(final)
    ], text=True).strip()

    meta = {
        'chapter': args.chapter,
        'title': title,
        'visual_version': VISUAL_VERSION,
        'scenes': len(beats),
        'dynamic_object_motion_scenes': dynamic_scene_count,
        'tentpole_motion_scenes': len(tents),
        'duration_seconds': float(probe),
        'video': final.name,
        'voice_provider': 'kokoro',
        'voice': voice,
        'voice_speed': speed,
        'voice_locked': True,
        'audio_files': audio_files,
        'source_pages': chapter.get('source_pages', []),
        'real_source_assets_used': sorted(set(real_assets_used)),
        'rejected_source_assets': sorted(set(rejected_source_assets)),
        'source_visual_reconstructions_used': sorted(set(reconstructions_used)),
        'scene_kinds': scene_kinds,
        'pipeline': 'locked Sarah voice -> sentence scene -> isolated PDF visual -> full pixel decode/sanitize to clean PNG -> source-specific reconstruction on any bad asset -> cinematic fill only for gaps -> alternating camera motion + recurring object-motion beats -> burned subtitles',
    }
    (args.output_dir / f'chapter_{args.chapter:03d}.json').write_text(json.dumps(meta, indent=2), encoding='utf-8')
    print(json.dumps(meta, indent=2))


if __name__ == '__main__':
    main()
