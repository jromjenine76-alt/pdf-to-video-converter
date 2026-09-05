# Approved Voice Lock

Production rule for long-form book/manual films:

1. Narration is generated and approved before final picture rendering.
2. The approved narration audio becomes an immutable source asset.
3. Renderers must read the approved narration file and must never regenerate or overwrite it.
4. Scene timing is derived from the approved voice, not the other way around.
5. If the approved TTS engine fails, stop narration generation for that unit rather than silently changing voices in a final build.
6. Fallback voices may only be used for disposable technical previews and must be labeled as previews.
7. Preserve sentence/chapter timestamps alongside the approved narration so picture cuts remain locked to speech.

## Spellcraft approved voice

- Provider: Kokoro local/offline TTS
- Voice ID: `af_sarah`
- Speed: `0.96`
- Language: `en-us`
- Status: APPROVED AND LOCKED by the user

For final Spellcraft production, `af_sarah` is the narration voice. Do not substitute Marin, Edge/Ava, or any other voice unless the user explicitly changes this approval.
