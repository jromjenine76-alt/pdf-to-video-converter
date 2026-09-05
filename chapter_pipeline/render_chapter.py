from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import edge_tts

MAX_TTS_CHARS = 2200
VOICE = 'en-US-AvaMultilingualNeural'

REPLACEMENTS = [
    (r'\bI[\s-]*T[\s-]*C\b', 'eye tee see'),
    (r'\bWyspell\b', 'Why-spell'),
    (r'\bLo\s+Scarabeo\b', 'loh skah rah BEH oh'),
    (r'\b[Cc]eromancy\b', 'seer oh man see'),
    (r'\b[Pp]yromancy\b', 'pie roh man see'),
    (r'\b[Ll]ychnomancy\b', 'lick noh man see'),
    (r'\b[Cc]apnomancy\b', 'cap noh man see'),
    (r'\b[Mm]agistellus\b', 'mag iss TELL us'),
]


def run(*args: str) -> None:
    subprocess.run(list(args), check=True)


def clean(text: str) -> str:
    for a, b in REPLACEMENTS:
        text = re.sub(a, b, text)
    return re.sub(r'\s+', ' ', text).strip()


def chunks(text: str, limit: int = MAX_TTS_CHARS) -> list[str]:
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


def key_for(text: str) -> str:
    return hashlib.sha256(text.encode('utf-8')).hexdigest()[:20]


async def edge_speech(text: str, target: Path) -> None:
    tmp = target.with_suffix('.mp3')
    await edge_tts.Communicate(text, voice=VOICE, rate='-4%').save(str(tmp))
    run('ffmpeg', '-y', '-v', 'error', '-i', str(tmp), '-ar', '48000', '-ac', '1', '-c:a', 'pcm_s16le', str(target))
    tmp.unlink(missing_ok=True)


def speech(text: str, target: Path) -> str:
    if target.exists() and target.stat().st_size > 1000:
        return 'cache'
    target.parent.mkdir(parents=True, exist_ok=True)
    key = os.environ.get('OPENAI_API_KEY', '').strip()
    if key:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=key)
            with client.audio.speech.with_streaming_response.create(
                model='gpt-4o-mini-tts',
                voice='marin',
                input=text,
                instructions='Warm natural human-like feminine educational narration; smooth connected phrasing; calm, expressive, no robotic cadence or announcer tone.',
                response_format='wav',
            ) as r:
                r.stream_to_file(target)
            if target.exists() and target.stat().st_size > 1000:
                return 'marin'
        except Exception as exc:
            print(f'Marin unavailable: {exc}', flush=True)
            target.unlink(missing_ok=True)
    asyncio.run(edge_speech(text, target))
    return 'edge'


def concat(files: list[Path], target: Path) -> None:
    listing = target.with_suffix('.concat.txt')
    listing.write_text(''.join(f"file '{p.resolve().as_posix()}'\n" for p in files), encoding='utf-8')
    run('ffmpeg', '-y', '-v', 'error', '-f', 'concat', '-safe', '0', '-i', str(listing), '-c', 'copy', '-movflags', '+faststart', str(target))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--catalog', type=Path, default=Path('chapter_pipeline/catalog.json'))
    ap.add_argument('--chapter', type=int, required=True)
    ap.add_argument('--output-dir', type=Path, default=Path('chapter_output'))
    ap.add_argument('--cache-dir', type=Path, default=Path('.chapter_cache'))
    args = ap.parse_args()

    data = json.loads(args.catalog.read_text(encoding='utf-8'))
    chapter = next(c for c in data['chapters'] if int(c['id']) == args.chapter)
    title = chapter['title']
    text = '\n\n'.join(s['text'] for s in chapter['sections'])
    parts = chunks(text)
    print(f'chapter {args.chapter}: {len(parts)} resumable narration/render chunks', flush=True)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    audio_dir = args.cache_dir / 'audio'
    video_dir = args.cache_dir / 'video'
    audio_dir.mkdir(parents=True, exist_ok=True)
    video_dir.mkdir(parents=True, exist_ok=True)

    videos = []
    voice_modes = []
    for i, text_part in enumerate(parts, 1):
        digest = key_for(text_part)
        wav = audio_dir / f'c{args.chapter:03d}_{i:03d}_{digest}.wav'
        mp4 = video_dir / f'c{args.chapter:03d}_{i:03d}_{digest}.mp4'
        mode = speech(text_part, wav)
        voice_modes.append(mode)

        if not (mp4.exists() and mp4.stat().st_size > 10000):
            manifest = args.cache_dir / f'manifest_c{args.chapter:03d}_{i:03d}.json'
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
        print(f'checkpoint {i}/{len(parts)} complete', flush=True)

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
        'voice_modes': sorted(set(voice_modes)),
        'source_pages': chapter.get('source_pages', []),
    }
    (args.output_dir / f'chapter_{args.chapter:03d}.json').write_text(json.dumps(meta, indent=2), encoding='utf-8')
    print(json.dumps(meta, indent=2))


if __name__ == '__main__':
    main()
