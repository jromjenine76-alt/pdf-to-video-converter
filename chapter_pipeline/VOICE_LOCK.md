# Approved Voice Lock

Production rule for long-form book/manual films:

1. Narration is generated and approved before final picture rendering.
2. The approved narration audio becomes an immutable source asset.
3. Renderers must read the approved narration file and must never regenerate or overwrite it.
4. Scene timing is derived from the approved voice, not the other way around.
5. If the preferred TTS provider fails, stop narration generation for that unit rather than silently changing voices in a final build.
6. Fallback voices may only be used for disposable technical previews and must be labeled as previews.
7. Preserve sentence/chapter timestamps alongside the approved narration so picture cuts remain locked to speech.

For Spellcraft, Marin remains the preferred approved target voice. A build that silently falls back to Edge/Ava is not a final narration build.
