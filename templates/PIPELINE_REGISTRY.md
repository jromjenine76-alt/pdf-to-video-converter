# Video Pipeline Registry

Purpose: keep approved production pipelines in GitHub so they can be reused without backtracking through old conversations.

## Standing rule
Whenever a production pipeline, rendering workflow, narration workflow, visual benchmark process, or reusable media-assembly method is approved by the user, save a named reference under `templates/` on this reusable template branch rather than relying only on chat history.

Each saved pipeline should record:
- pipeline name
- intended use
- source handling rules
- narration/voice rules
- image/asset rules
- motion rules
- assembly/export settings
- QA gates
- player/delivery behavior if applicable
- any user-approved non-negotiables

## Registered pipelines

### Animated Educational Walkthrough Pipeline
Location: `templates/animated_walkthrough/README.md`
Use: deep illustrated educational/manual walkthroughs with object-level motion, diagrams, source-image isolation, and full-source coverage.

### Grok Terra Infinita Cinematic Storytelling Pipeline
Location: `templates/cinematic_storytelling/GROK_TERRA_INFINITA_PIPELINE.md`
Use: cinematic book films using narration-first timing, real PDF images, one visual beat per sentence, cinematic stills, limited tentpole motion clips, subtitles, and a player.

## Preservation rule
Do not silently replace or rewrite a saved approved pipeline. Create a new version or clearly documented variant when requirements change.