# Animated Educational Walkthrough Pipeline Template

This template preserves the production architecture used for the Spellcraft animated walkthrough so it can be reused for future long-form PDF-to-video projects.

## Core rule

**The PDF is the content map and asset source. It is never the presentation.**

Do not render full PDF pages as scenes. Do not turn pages into static cards with narration. Every narration unit must be translated into a sequence of visual teaching beats.

## Visual standard

A finished video should feel like an illustrated educational film, not a slideshow.

- Use original illustrated scenes, isolated source imagery, diagrams, objects, labels, close-ups, and cinematic transitions.
- Use continuous motion: camera pushes, pans, parallax, object entrances, drawn lines/arrows, reveals, transformations, animated diagrams, flame/smoke/wax motion, and scene changes.
- One narration unit should normally contain multiple visual beats, not one static composition.
- On-screen text is limited to headings, short labels, callouts, measurements, and essential quotations. Never dump narration paragraphs onto the screen.
- Keep all text inside protected safe margins and verify it at 1920x1080 before final encoding.
- Maintain one consistent visual world across the entire project. Do not mix unrelated backgrounds, fonts, illustration styles, or color systems.

## Source-image handling

1. Inspect the PDF page and identify useful photographs, diagrams, product pictures, charts, symbols, and illustrations.
2. Extract standalone image objects when they are clean.
3. Reject any extraction where page text overlaps or contaminates the image region.
4. If a useful visual is flattened into the page or contaminated by text, clean/reconstruct it or create an original replacement.
5. Never use a rectangular screenshot of a whole page merely because extraction is difficult.
6. Supporting web imagery must be appropriately licensed or used only as reference for an original reconstruction.

The current renderer includes `CleanAssetExtractor`, which rejects PDF image objects when text overlaps the image bounding box.

## Narration

Use a warm, natural, human-like educational voice with connected phrasing and restrained expression. Avoid robotic cadence, excessive pauses, and announcer delivery.

Maintain a project pronunciation dictionary for names, technical terms, acronyms, foreign words, and unusual terminology. Verify pronunciation before rendering the full series.

For the Spellcraft build, Marin is the preferred voice with neural fallback only when necessary. Future projects can change the voice while retaining the same narration QA rules.

## Long-form coverage

For manuals and books, maintain a coverage ledger so every source page or section is accounted for.

Recommended fields:
- source page / page range
- chapter / section
- narration unit
- episode
- source visuals available
- original visuals required
- scene type
- rendered status
- narration verified
- visual QA passed

A long manual may be divided into episodes for rendering and delivery, but the combined series must still cover the full source from first page to last page.

## Scene grammar

Each narration unit becomes 3-8 timed visual beats depending on length and complexity. Typical sequence:

1. establish the scene
2. introduce the object or diagram
3. move/highlight the relevant component
4. draw an arrow, path, label, or relationship
5. change state or demonstrate the process
6. cut or push into a close-up
7. transition into the next visual environment

Examples:
- candle layout: candles animate into position, petition moves into the center, lighting order is traced, flames flicker
- herbs: botanical assets reveal one at a time, labels draw in, ingredients move toward the working area
- petitions/seals: paper enters, folds, wax appears, seal presses, close-up reveals result
- diagrams: lines draw themselves, nodes illuminate, arrows trace sequence, camera follows the explanation
- flame/wax interpretation: the flame and wax physically change state while short interpretation labels appear

## Current implementation

The Spellcraft implementation is stored in:
- `spellcraft_animated_renderer.py`
- `.github/workflows/spellcraft-animated-autobuild.yml`
- `.github/workflows/spellcraft-animated-walkthrough-v2.yml`

The renderer uses PyMuPDF, Pillow, and FFmpeg and is designed for GitHub Actions / Google Colab. It is deliberately separate from the legacy page-frame renderer.

## Production stages

1. Verify source PDF and exact page count.
2. Build the full coverage ledger.
3. Split narration into coherent units and episodes without losing source coverage.
4. Generate and QA human-like narration.
5. Extract clean source assets.
6. Create original illustrated assets for missing/contaminated visuals.
7. Assign scene types and visual beats to each narration unit.
8. Render episodes in parallel.
9. Verify MP4 readability, dimensions, duration, audio, text safety, and visual motion.
10. Review representative clips from the beginning, middle, and end of every episode.
11. Upload episode artifacts.
12. Stitch a full master only after every episode passes QA.

## Hard QA gates

A build is not complete until all of these pass:
- every intended source section is covered
- no full-page slideshow presentation
- no clipped or off-screen text
- no contaminated image crops
- no silent or missing narration units
- pronunciation checks pass
- no frozen/static scene held for long narration without purposeful animation
- episode MP4 opens successfully and has expected video/audio streams
- consistent visual style across episodes
- all episode artifacts uploaded successfully

## Reusing this template

For a new manual/book:
1. keep this file as the production checklist
2. duplicate the animated renderer into a project-specific renderer if custom scene types are needed
3. create a new project branch
4. replace source/narration paths and project terminology
5. build a new pronunciation dictionary
6. preserve the clean-asset rules and visual QA gates
7. render in episodes, then assemble the final master after QA
