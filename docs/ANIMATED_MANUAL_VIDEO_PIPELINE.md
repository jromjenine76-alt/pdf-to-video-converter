# Animated Manual Video Pipeline Template v1

This branch preserves the long-form manual-to-video architecture developed for the Spellcraft project so it can be reused for future books and manuals without reverting to a static slideshow workflow.

## Core rule

The PDF is the content map and asset source, not the screen design.

Do not render full PDF pages as the primary presentation. Extract or reconstruct individual visual assets, create original illustrations where needed, and animate those assets into educational scenes synchronized to narration.

## Production architecture

1. Source audit
   - Verify the full page count.
   - Build a page-to-unit coverage ledger.
   - Preserve chapter order, terminology, safety notes, corrections, and source-specific wording.
   - Never silently omit pages because they are visually sparse.

2. Narration manifest
   - Convert the full manual into narration units.
   - Each unit contains episode, unit number, source-page range, heading, narration text, and optional target duration.
   - Keep pronunciation substitutions in a dedicated dictionary rather than rewriting source text.

3. Voice
   - Preferred voice: Marin where available.
   - Delivery target: warm, natural, human-like feminine educational narration; smooth connected phrasing; calm storytelling pace; clear pronunciation; expressive but restrained emphasis; no robotic cadence; no choppy pauses; no announcer tone.
   - Keep a fallback neural voice only for service/API failures.

4. Asset extraction
   - Use PyMuPDF/Pillow to inspect and extract imagery.
   - Never use blind rectangular crops when surrounding text overlaps the visual.
   - Reject contaminated crops.
   - For contaminated or low-quality source art, reconstruct, clean, find a legitimate cleaner reference, or generate an original replacement.
   - Preserve source attribution/licensing where relevant.

5. Scene design
   - One narration unit should contain multiple visual beats, not one frame held for the whole unit.
   - Typical beat language:
     - establish illustrated scene
     - object enters or assembles
     - camera pushes/pans
     - annotation draws on
     - diagram changes state
     - object highlights or transforms
     - close-up reveals detail
     - transition to next composition
   - Use short callouts rather than paragraphs on screen.

6. Motion language
   - Animate candle placement, flame flicker, wax flow, smoke drift, petition folding, seals, arrows, traced paths, diagrams, botanical reveals, celestial maps, labels, highlighting, camera push-ins, parallax, and object rearrangement.
   - Motion must teach the narration, not merely decorate it.

7. Typography and safe areas
   - Protect all text with title/action safe margins.
   - No clipped words, edge-hugging captions, or text behind imagery.
   - Dynamically wrap and resize labels where needed.
   - Prefer concise labels and visual demonstration over text-heavy screens.

8. Render stack
   - FFmpeg: assembly, encoding, transitions, audio muxing, verification.
   - Pillow: compositing, masks, graphic elements, text layout.
   - PyMuPDF: PDF inspection/extraction.
   - Optional OpenCV: object/camera motion and image processing.
   - Optional Manim: diagrams, geometry, animated paths, instructional callouts.

9. Parallel episode workflow
   - Split long manuals into multiple episodes only for rendering/distribution efficiency, not to reduce coverage.
   - Keep one master coverage ledger proving the full source is represented.
   - Render episodes in parallel when runners are available.
   - Every episode must pass ffprobe verification before upload.

10. Quality gate
    - No full-page slideshow sequence.
    - No static card held for long narration.
    - No text clipped or overlapped.
    - No contaminated extracted assets.
    - No invented chapter names or unsupported content.
    - Voice pronunciation spot-checks for specialized terms.
    - Verify every episode artifact and final concatenation.

## Reuse workflow

For a new project:

1. Copy this branch or the renderer/workflow files into a new project branch.
2. Replace the project-specific narration manifest and source asset folder.
3. Update pronunciation substitutions.
4. Define the project art direction in a config file.
5. Run a short representative motion test covering text, diagrams, source images, and original illustrations.
6. After the style test passes, launch the full parallel render.

## Spellcraft reference implementation

The source implementation lives on `spellcraft-animated-walkthrough-v2` and includes the animated renderer, long-form narration handling, pronunciation fixes, GitHub Actions parallel rendering, and artifact verification.

This template branch is intentionally separate so future reuse does not disturb an active production build.
