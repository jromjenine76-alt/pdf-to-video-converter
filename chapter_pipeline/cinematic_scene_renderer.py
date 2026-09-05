from __future__ import annotations

import argparse
import json
import math
import os
import re
import shlex
import subprocess
from pathlib import Path


def run(cmd: list[str]) -> None:
    print('+', ' '.join(shlex.quote(x) for x in cmd), flush=True)
    subprocess.run(cmd, check=True)


def ffprobe_duration(path: Path) -> float:
    out = subprocess.check_output([
        'ffprobe','-v','error','-show_entries','format=duration',
        '-of','default=noprint_wrappers=1:nokey=1',str(path)
    ], text=True).strip()
    return float(out)


def sentence_beats(text: str) -> list[str]:
    parts = re.split(r'(?<=[.!?])\s+', re.sub(r'\s+', ' ', text).strip())
    return [p.strip() for p in parts if p.strip()]


def srt_time(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    h, rem = divmod(ms, 3600000)
    m, rem = divmod(rem, 60000)
    s, milli = divmod(rem, 1000)
    return f'{h:02d}:{m:02d}:{s:02d},{milli:03d}'


def write_srt(beats: list[str], durations: list[float], target: Path) -> None:
    t = 0.0
    lines = []
    for i, (beat, dur) in enumerate(zip(beats, durations), 1):
        lines += [str(i), f'{srt_time(t)} --> {srt_time(t+dur)}', beat, '']
        t += dur
    target.write_text('\n'.join(lines), encoding='utf-8')


def choose_assets(assets: list[Path], count: int) -> list[Path]:
    if not assets:
        raise SystemExit('No visual assets found. Supply --assets-dir with clean extracted/generated 16:9 or source images.')
    out = []
    for i in range(count):
        out.append(assets[i % len(assets)])
    return out


def motion_filter(index: int, duration: float, fps: int = 30) -> str:
    frames = max(1, int(duration * fps))
    # Rotate four Ken Burns moves so the same motion never repeats consecutively.
    mode = index % 4
    if mode == 0:  # slow zoom in
        z = "min(zoom+0.0007,1.12)"; x = "iw/2-(iw/zoom/2)"; y = "ih/2-(ih/zoom/2)"
    elif mode == 1:  # slow zoom out
        z = "if(lte(on,1),1.12,max(zoom-0.0007,1.0))"; x = "iw/2-(iw/zoom/2)"; y = "ih/2-(ih/zoom/2)"
    elif mode == 2:  # pan left to right
        z = "1.07"; x = f"(iw-iw/zoom)*on/{frames}"; y = "ih/2-(ih/zoom/2)"
    else:  # pan right to left
        z = "1.07"; x = f"(iw-iw/zoom)*(1-on/{frames})"; y = "ih/2-(ih/zoom/2)"
    return (
        f"scale=2304:1296:force_original_aspect_ratio=increase,crop=2304:1296,"
        f"zoompan=z='{z}':x='{x}':y='{y}':d={frames}:s=1920x1080:fps={fps},"
        "format=yuv420p"
    )


def render_still_scene(asset: Path, out: Path, duration: float, index: int) -> None:
    run([
        'ffmpeg','-y','-v','error','-loop','1','-i',str(asset),
        '-vf',motion_filter(index, duration),'-t',f'{duration:.3f}',
        '-an','-c:v','libx264','-preset','veryfast','-crf','20','-pix_fmt','yuv420p',str(out)
    ])


def main() -> None:
    ap = argparse.ArgumentParser(description='Voice-first cinematic chapter renderer: one visual beat per sentence, real assets first, Ken Burns motion, subtitle burn-in.')
    ap.add_argument('--text-file', type=Path, required=True)
    ap.add_argument('--voice', type=Path, required=True, help='Approved narration audio. This file is read-only and never overwritten.')
    ap.add_argument('--assets-dir', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--work-dir', type=Path, default=Path('.cinematic_work'))
    args = ap.parse_args()

    text = args.text_file.read_text(encoding='utf-8')
    beats = sentence_beats(text)
    if not beats:
        raise SystemExit('No narration beats found')
    voice_duration = ffprobe_duration(args.voice)

    # Weight timing by character count, with a minimum scene duration, then normalize to exact voice length.
    weights = [max(36, len(b)) for b in beats]
    raw = [max(2.8, voice_duration * w / sum(weights)) for w in weights]
    scale = voice_duration / sum(raw)
    durations = [d * scale for d in raw]

    assets = sorted([p for p in args.assets_dir.rglob('*') if p.suffix.lower() in {'.jpg','.jpeg','.png','.webp'}])
    chosen = choose_assets(assets, len(beats))

    scene_dir = args.work_dir / 'scenes'
    scene_dir.mkdir(parents=True, exist_ok=True)
    scenes = []
    for i, (asset, dur) in enumerate(zip(chosen, durations)):
        out = scene_dir / f'scene_{i:04d}.mp4'
        if not out.exists() or out.stat().st_size < 10000:
            render_still_scene(asset, out, dur, i)
        scenes.append(out)
        print(f'scene {i+1}/{len(beats)} ready: {dur:.2f}s {asset.name}', flush=True)

    concat_txt = args.work_dir / 'scenes.txt'
    concat_txt.write_text(''.join(f"file '{p.resolve().as_posix()}'\n" for p in scenes), encoding='utf-8')
    silent = args.work_dir / 'silent_master.mp4'
    run(['ffmpeg','-y','-v','error','-f','concat','-safe','0','-i',str(concat_txt),'-c','copy',str(silent)])

    srt = args.work_dir / 'subtitles.srt'
    write_srt(beats, durations, srt)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    # Voice first, picture second. Burn subtitles and preserve approved voice file unchanged.
    run([
        'ffmpeg','-y','-v','error','-i',str(silent),'-i',str(args.voice),
        '-vf',f"subtitles={srt.as_posix()}:force_style='FontName=DejaVu Sans,FontSize=24,PrimaryColour=&H00FFFFFF,OutlineColour=&H80000000,BorderStyle=3,Outline=1,Shadow=0,MarginV=46,Alignment=2'",
        '-c:v','libx264','-preset','medium','-crf','19','-pix_fmt','yuv420p',
        '-c:a','aac','-b:a','192k','-shortest','-movflags','+faststart',str(args.output)
    ])

    meta = {
        'beats': len(beats), 'duration': ffprobe_duration(args.output),
        'voice_source': str(args.voice), 'voice_overwritten': False,
        'assets_used': [p.name for p in chosen], 'output': str(args.output),
    }
    (args.output.with_suffix('.json')).write_text(json.dumps(meta, indent=2), encoding='utf-8')
    print(json.dumps(meta, indent=2), flush=True)


if __name__ == '__main__':
    main()
