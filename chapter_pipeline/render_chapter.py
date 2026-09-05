from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

from kokoro_onnx import Kokoro
from kokoro_tts import clean, digest_for, synthesize
from cinematic_scene_renderer import MOVES, make_scene, render_ken_burns, render_tentpole


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
    """Prefer clean real-book assets when present; procedural illustration fills only the gaps."""
    if not asset_dir.exists():
        return None
    files = {p.name.lower(): p for p in asset_dir.iterdir() if p.suffix.lower() in {'.jpg', '.jpeg', '.png', '.webp'}}
    t = text.lower()
    rules = [
        (('soul sticks', 'gambling manifesting intention kit'), 'page019_soul_sticks_kit.jpg'),
        (('traditional', 'folk associations'), 'page020_traditional_indications.jpg'),
        (('wyspell', '12 colors', 'colored spell candle'), 'page021_wyspell_color_chart.jpg'),
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
    if count <= 3:
        return set(range(count))
    return {0, count // 2, count - 1}


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
    print(f'chapter {args.chapter}: {len(beats)} Sarah-locked sentence scenes', flush=True)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    audio_dir = args.cache_dir / 'audio'
    still_dir = args.cache_dir / 'stills'
    video_dir = args.cache_dir / 'video'
    for d in (audio_dir, still_dir, video_dir):
        d.mkdir(parents=True, exist_ok=True)

    kokoro = Kokoro(str(args.kokoro_model), str(args.kokoro_voices))
    available = set(kokoro.get_voices())
    if voice not in available:
        raise SystemExit(f'Locked voice {voice!r} is not available in this Kokoro voice pack')

    tents = tentpole_indices(len(beats))
    videos: list[Path] = []
    audio_files: list[str] = []
    scene_kinds: list[str] = []
    assets_used: list[str] = []

    for i, beat in enumerate(beats):
        scene_no = i + 1
        digest = digest_for(beat, voice, speed)
        stem = f'c{args.chapter:03d}_s{scene_no:04d}_{voice}_{digest}'
        wav = audio_dir / f'{stem}.wav'
        still = still_dir / f'{stem}.jpg'
        mp4 = video_dir / f'{stem}.mp4'

        synthesize(kokoro, beat, wav, voice=voice, speed=speed, lang=lang)
        audio_files.append(wav.name)

        asset = choose_source_asset(beat, args.asset_dir)
        if asset:
            assets_used.append(asset.name)
        kind = make_scene(beat, scene_no, still, asset=asset)
        scene_kinds.append(kind)

        if not (mp4.exists() and mp4.stat().st_size > 10000):
            if i in tents:
                render_tentpole(still, wav, beat, mp4, kind, seed=args.chapter*1000 + scene_no)
            else:
                render_ken_burns(still, wav, beat, mp4, move=MOVES[i % len(MOVES)])

        videos.append(mp4)
        motion = 'tentpole motion' if i in tents else MOVES[i % len(MOVES)]
        print(f'scene {scene_no}/{len(beats)} complete: {kind} / {motion} / locked {voice}', flush=True)

    final = args.output_dir / f'chapter_{args.chapter:03d}.mp4'
    concat(videos, final)
    probe = subprocess.check_output([
        'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1', str(final)
    ], text=True).strip()

    meta = {
        'chapter': args.chapter,
        'title': title,
        'scenes': len(beats),
        'tentpole_motion_scenes': len(tents),
        'duration_seconds': float(probe),
        'video': final.name,
        'voice_provider': 'kokoro',
        'voice': voice,
        'voice_speed': speed,
        'voice_locked': True,
        'audio_files': audio_files,
        'source_pages': chapter.get('source_pages', []),
        'real_source_assets_used': sorted(set(assets_used)),
        'scene_kinds': scene_kinds,
        'pipeline': 'voice-first sentence scene -> real source asset if available -> cinematic fill -> alternating Ken Burns -> three tentpole motion scenes -> burned subtitles',
    }
    (args.output_dir / f'chapter_{args.chapter:03d}.json').write_text(json.dumps(meta, indent=2), encoding='utf-8')
    print(json.dumps(meta, indent=2))


if __name__ == '__main__':
    main()
