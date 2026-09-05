# Grok Terra Infinita Cinematic Storytelling Pipeline

Canonical reusable reference supplied by the user for future PDF-to-video projects.

## Prompt

Build a cinematic storytelling narrative motion film from the PDF I upload.

## PIPELINE

Do not skip steps. Do not swap the voice after I approve it.

### 1. SOURCE
- Use the uploaded PDF as the book.
- If I also upload a script/SRT, that is the narration bible. Do not rewrite it.
- If no script, condense the book into a 4–6 minute cinematic narration: short paragraphs, one image-beat per sentence, blank line between beats.

### 2. EXTRACT
- Pull real images from the PDF (cover, maps, plates, illustrations).
- Keep maps/plates in the film. Do not replace them with AI.
- Skip full-page body-text scans as hero shots.

### 3. VOICE
- Convert the narration text to audio with a human-like generated documentary voice.
- Use the same voice for the whole film. Do not change it after I say the voice is good.
- Keep character/sentence timestamps so picture cuts land on sentences.

### 4. STILLS
- One cinematic 16:9 still per narration beat.
- Photoreal, anamorphic, film grain, no text, no watermark, no logo.
- Mix in the real PDF plates for maps/diagrams.

### 5. MOTION
- Generate 3–5 short 16:9 video clips only for tentpole beats (opening, the big reveal, the ending).
- All other beats: Ken Burns on the still (slow zoom in/out or pan left/right). Never two of the same move in a row.

### 6. ASSEMBLE
- Cut list: one scene per sentence, timed to the voice.
- Ken Burns stills + loop/letterbox the clips to scene length.
- Mux the approved voice. Burn subtitles into the picture.
- Export 1920×1080 H.264 + AAC, faststart.
- Do not overwrite the approved narration file.

### 7. PLAYER
- 16:9 film player, play/pause, chapter rail, live subtitles, Open button.

## RULES
- Voice first, picture second.
- Real book images stay. AI fills gaps only.
- Do not use a solid-color canvas or a slideshow.
- Do not regenerate the voice unless I ask.
- Same pipeline for any book I upload next.

## Terra Infinita implementation notes from the reference
1. Used the supplied 6-page SRT script as narration bible, not a rewrite of the 382-page book.
2. Extracted real PDF cover, maps, and plates.
3. Used Atlas documentary voice with timestamps.
4. Created one 16:9 cinematic still per sentence.
5. Used 3 motion clips for tentpole beats: ice wall, El Arca, World Tree.
6. Built a 30-scene timeline locked to the voice.
7. Combined Ken Burns motion, clip inserts, burned subtitles, and exported one MP4.

## Reuse instruction
For a future book, use this pipeline as the base unless the user explicitly requests a different production style or runtime. Preserve any separately approved voice, visual benchmark, or source-specific coverage requirements.