from __future__ import annotations

import argparse
import hashlib
import re
from pathlib import Path

import soundfile as sf
from kokoro_onnx import Kokoro

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


def clean(text: str) -> str:
    for pattern, replacement in REPLACEMENTS:
        text = re.sub(pattern, replacement, text)
    return re.sub(r'\s+', ' ', text).strip()


def digest_for(text: str, voice: str, speed: float) -> str:
    payload = f'{voice}|{speed:.3f}|{clean(text)}'.encode('utf-8')
    return hashlib.sha256(payload).hexdigest()[:20]


def synthesize(
    kokoro: Kokoro,
    text: str,
    target: Path,
    *,
    voice: str,
    speed: float = 0.96,
    lang: str = 'en-us',
) -> Path:
    if target.exists() and target.stat().st_size > 1000:
        return target
    target.parent.mkdir(parents=True, exist_ok=True)
    samples, sample_rate = kokoro.create(clean(text), voice=voice, speed=speed, lang=lang)
    sf.write(target, samples, sample_rate)
    if not target.exists() or target.stat().st_size <= 1000:
        raise RuntimeError(f'Kokoro failed to create usable audio: {target}')
    return target


def main() -> None:
    ap = argparse.ArgumentParser(description='Generate free local Kokoro narration without paid API calls.')
    ap.add_argument('--model', type=Path, required=True)
    ap.add_argument('--voices', type=Path, required=True)
    ap.add_argument('--voice', required=True, help='Approved Kokoro voice ID, e.g. af_sarah')
    ap.add_argument('--text', help='Narration text. Mutually exclusive with --text-file.')
    ap.add_argument('--text-file', type=Path, help='UTF-8 narration text file.')
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--speed', type=float, default=0.96)
    args = ap.parse_args()

    if bool(args.text) == bool(args.text_file):
        raise SystemExit('Provide exactly one of --text or --text-file')
    if not args.model.exists() or not args.voices.exists():
        raise SystemExit('Kokoro model or voices file is missing')

    text = args.text if args.text is not None else args.text_file.read_text(encoding='utf-8')
    kokoro = Kokoro(str(args.model), str(args.voices))
    available = set(kokoro.get_voices())
    if args.voice not in available:
        raise SystemExit(f'Voice {args.voice!r} not available. Available voices include: {sorted(available)[:20]}')

    synthesize(kokoro, text, args.output, voice=args.voice, speed=args.speed)
    print(args.output)


if __name__ == '__main__':
    main()
