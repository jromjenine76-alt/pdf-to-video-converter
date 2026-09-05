from __future__ import annotations

import argparse
from pathlib import Path

import soundfile as sf
from kokoro_onnx import Kokoro

DEFAULT_TEXT = (
    "Welcome to the Complete Manifestation and Spellcraft Manual. "
    "In this walkthrough, we will move carefully through the tools, symbols, rituals, and safety guidance, "
    "showing each idea visually while keeping the narration calm, natural, and easy to follow. "
    "Wyspell is pronounced Why-spell. Lo Scarabeo is pronounced loh skah rah BEH oh. "
    "Ceromancy is pronounced seer oh man see, and pyromancy is pronounced pie roh man see."
)

PREFERRED_VOICES = [
    "af_sarah",
    "af_nicole",
    "af_bella",
    "af_heart",
]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", type=Path, default=Path(".kokoro/kokoro-v1.0.onnx"))
    ap.add_argument("--voices", type=Path, default=Path(".kokoro/voices-v1.0.bin"))
    ap.add_argument("--output-dir", type=Path, default=Path("kokoro_voice_tests"))
    ap.add_argument("--text", default=DEFAULT_TEXT)
    args = ap.parse_args()

    if not args.model.exists():
        raise SystemExit(f"Missing Kokoro model: {args.model}")
    if not args.voices.exists():
        raise SystemExit(f"Missing Kokoro voices file: {args.voices}")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    kokoro = Kokoro(str(args.model), str(args.voices))
    available = set(kokoro.get_voices())
    chosen = [voice for voice in PREFERRED_VOICES if voice in available]
    if not chosen:
        chosen = sorted(v for v in available if v.startswith("af_"))[:4]
    if not chosen:
        raise SystemExit("No American-English female Kokoro voices found")

    lines = []
    for voice in chosen:
        samples, sample_rate = kokoro.create(
            args.text,
            voice=voice,
            speed=0.96,
            lang="en-us",
        )
        target = args.output_dir / f"kokoro_{voice}.wav"
        sf.write(target, samples, sample_rate)
        lines.append(f"{voice}\t{target.name}\t{sample_rate}")
        print(f"created {target}")

    (args.output_dir / "VOICE_CHOICES.txt").write_text(
        "Free local Kokoro voice candidates for Spellcraft\n\n" + "\n".join(lines) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
