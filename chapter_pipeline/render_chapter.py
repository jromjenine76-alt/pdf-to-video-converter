from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

from kokoro_onnx import Kokoro
from kokoro_tts import clean, digest_for, synthesize


def run(*args: str) -> None:
    subprocess.run(list(args), check=True)


def chunks(text: str, limit: int = 2200) -> list[str]:
    import re

    sents = re.split(r'(?<=[.!?])\s+', clean(text))
    out, cur = [], ''
    for s in sents:
        if not s:
            continue
        candidate = (cur + ' ' + s).strip()
        if len(candidate) <= limit:
            cur = candidate
            continue
        if cur:
            out.append(cur)
        while len(s) > limit:
            cut = s.rfind(' ', 0, limit)
            cut = cut if cut > 200 else limit
            out.append(s[:cut].strip())
            s = s[cut:].strip()
        cur = s
    if cur:
        out.append(cur)
    return out


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


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--catalog', type=Path, default=Path('chapter_pipeline/catalog.json'))
    ap.add_argument('--chapter', type=int, required=True)
    ap.add_argument('--output-dir', type=Path, default=Path('chapter_output'))
    ap.add_argument('--cache-dir', type=Path, default=Path('.chapter_cache'))
    ap.add_argument('--voice-config', type=Path, default=Path('chapter_pipeline/VOICE_CONFIG.json'))
    ap.add_argument('--kokoro-model', type=Path, default=Path('.kokoro/kokoro-v1.0.onnx'))
    ap.add_argument('--kokoro-voices', type=Path, default=Path('.kokoro/voices-v1.0.bin'))
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
    parts = chunks(text)
    print(f'chapter {args.chapter}: {len(parts)} resumable Sarah narration/render chunks', flush=True)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    audio_dir = args.cache_dir / 'audio'
    video_dir = args.cache_dir / 'video'
    audio_dir.mkdir(parents=True, exist_ok=True)
    video_dir.mkdir(parents=True, exist_ok=True)

    kokoro = Kokoro(str(args.kokoro_model), str(args.kokoro_voices))
    available = set(kokoro.get_voices())
    if voice not in available:
        raise SystemExit(f'Locked voice {voice!r} is not available in this Kokoro voice pack')

    videos: list[Path] = []
    audio_files: list[str] = []
    for i, text_part in enumerate(parts, 1):
        digest = digest_for(text_part, voice, speed)
        wav = audio_dir / f'c{args.chapter:03d}_{i:03d}_{voice}_{digest}.wav'
        mp4 = video_dir / f'c{args.chapter:03d}_{i:03d}_{voice}_{digest}.mp4'

        synthesize(kokoro, text_part, wav, voice=voice, speed=speed, lang=lang)
        audio_files.append(wav.name)

        if not (mp4.exists() and mp4.stat().st_size > 10000):
            manifest = args.cache_dir / f'manifest_c{args.chapter:03d}_{i:03d}_{voice}_{digest}.json'
            manifest.write_text(json.dumps({'episode': args.chapter, 'units': [{
                'episode': args.chapter,
                'unit': i,
                'text': text_part,
                'heading': title,
                'source_pages': chapter.get('source_pages', []),
                'audio': wav.name,
            }]}, indent=2), encoding='utf-8')
            run('python', 'spellcraft_animated_renderer.py',
                '--manifest', str(manifest),
                '--audio-dir', str(audio_dir),
                '--episode', str(args.chapter),
                '--output', str(mp4))
        videos.append(mp4)
        print(f'checkpoint {i}/{len(parts)} complete with locked voice {voice}', flush=True)

    final = args.output_dir / f'chapter_{args.chapter:03d}.mp4'
    concat(videos, final)
    probe = subprocess.check_output([
        'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1', str(final)
    ], text=True).strip()
    meta = {
        'chapter': args.chapter,
        'title': title,
        'chunks': len(parts),
        'duration_seconds': float(probe),
        'video': final.name,
        'voice_provider': 'kokoro',
        'voice': voice,
        'voice_speed': speed,
        'voice_locked': True,
        'audio_files': audio_files,
        'source_pages': chapter.get('source_pages', []),
    }
    (args.output_dir / f'chapter_{args.chapter:03d}.json').write_text(json.dumps(meta, indent=2), encoding='utf-8')
    print(json.dumps(meta, indent=2))


if __name__ == '__main__':
    main()
