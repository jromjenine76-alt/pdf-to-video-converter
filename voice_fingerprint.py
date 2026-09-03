from pathlib import Path
from openai import OpenAI
import json

MODEL = "gpt-4o-mini-tts"
VOICES = [
    "marin", "cedar", "coral", "sage", "shimmer", "nova",
    "alloy", "ash", "ballad", "echo", "fable", "onyx", "verse",
]
TEXT = (
    "Welcome to The Complete Manifestation and Spellcraft Manual, Master Edition. "
    "This is Episode One of an eight-part guided series. "
    "We begin where responsible practice must begin: with safety, clear interpretation, "
    "and a working knowledge of the tools."
)
INSTRUCTIONS = (
    "Speak as a warm, calm educational guide. Use a natural pace, clear pronunciation, "
    "gentle emphasis, and brief pauses between ideas."
)

client = None
client_error = None
try:
    client = OpenAI()
except Exception as exc:
    client_error = f"{type(exc).__name__}: {exc}"
out = Path("voice_candidates")
out.mkdir(exist_ok=True)
results = []

for voice in VOICES:
    target = out / f"{voice}.wav"
    if client is None:
        results.append({"voice": voice, "status": "error", "error": (client_error or "OpenAI client unavailable")[:500]})
        print(f"VOICE_ERROR={voice}: {client_error or 'OpenAI client unavailable'}")
        continue
    try:
        with client.audio.speech.with_streaming_response.create(
            model=MODEL,
            voice=voice,
            input=TEXT,
            instructions=INSTRUCTIONS,
            response_format="wav",
        ) as response:
            response.stream_to_file(target)
        results.append({"voice": voice, "status": "ok", "file": target.name})
        print(f"VOICE_OK={voice}")
    except Exception as exc:
        results.append({"voice": voice, "status": "error", "error": str(exc)[:500]})
        print(f"VOICE_ERROR={voice}: {type(exc).__name__}: {exc}")

(out / "manifest.json").write_text(json.dumps({
    "model": MODEL,
    "text": TEXT,
    "instructions": INSTRUCTIONS,
    "results": results,
}, indent=2), encoding="utf-8")

if not any(item["status"] == "ok" for item in results):
    print("No voice candidates were generated")
