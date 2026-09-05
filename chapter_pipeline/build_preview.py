from __future__ import annotations

import argparse
import html
import json
import shutil
from pathlib import Path


def _number(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _integer(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def _load_items(chapters_dir: Path, media: Path) -> tuple[list[dict], list[str]]:
    items: list[dict] = []
    warnings: list[str] = []

    for meta_path in sorted(chapters_dir.glob('chapter_*.json')):
        try:
            meta = json.loads(meta_path.read_text(encoding='utf-8'))
        except Exception as exc:
            warnings.append(f'{meta_path.name}: unreadable metadata ({exc})')
            continue

        chapter = _integer(meta.get('chapter', meta.get('id', 0)))
        title = str(meta.get('title') or f'Chapter {chapter or "?"}')
        video_name = str(meta.get('video') or '')
        if not video_name:
            warnings.append(f'{meta_path.name}: no video field; card will be marked unavailable')
        else:
            src = chapters_dir / video_name
            if src.exists() and src.is_file() and src.stat().st_size > 0:
                dst = media / src.name
                if not dst.exists() or dst.stat().st_size != src.stat().st_size:
                    shutil.copy2(src, dst)
                meta['video_url'] = f'media/{dst.name}'
            else:
                warnings.append(f'{meta_path.name}: referenced video missing: {video_name}')

        # Normalize current and legacy metadata into one preview contract.
        meta['chapter'] = chapter
        meta['title'] = title
        meta['scene_count'] = _integer(meta.get('scenes', meta.get('chunks', meta.get('segments', 0))))
        meta['duration_seconds_normalized'] = _number(meta.get('duration_seconds', meta.get('duration', 0.0)))
        meta['unit_label'] = 'cinematic scenes' if 'scenes' in meta else 'checkpointed segments'
        items.append(meta)

    return items, warnings


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--chapters-dir', type=Path, default=Path('chapter_output'))
    ap.add_argument('--output-dir', type=Path, default=Path('preview_app'))
    args = ap.parse_args()

    if not args.chapters_dir.exists():
        raise SystemExit(f'Chapter directory does not exist: {args.chapters_dir}')

    args.output_dir.mkdir(parents=True, exist_ok=True)
    media = args.output_dir / 'media'
    media.mkdir(exist_ok=True)

    items, warnings = _load_items(args.chapters_dir, media)
    if not items:
        raise SystemExit('No readable chapter metadata files were found; preview cannot be built')

    cards = []
    for item in items:
        pages = item.get('source_pages') or []
        try:
            page_text = '' if not pages else f"Pages {pages[0]}–{pages[-1]}"
        except Exception:
            page_text = ''

        chapter = _integer(item.get('chapter'))
        title = html.escape(str(item.get('title') or f'Chapter {chapter or "?"}'))
        video_url = str(item.get('video_url') or '')
        scene_count = _integer(item.get('scene_count'))
        duration_seconds = _number(item.get('duration_seconds_normalized'))
        unit_label = str(item.get('unit_label') or 'scenes')
        voice = str(item.get('voice') or '')
        voice_note = f' · voice: {html.escape(voice)}' if voice else ''

        if video_url:
            player = f'<video controls preload="metadata" src="{html.escape(video_url)}"></video>'
            download = f'<a class="download" href="{html.escape(video_url)}" download>Download chapter MP4</a>'
        else:
            player = '<div class="missing">Video artifact unavailable for this chapter.</div>'
            download = ''

        cards.append(f'''
        <article class="card">
          <div class="eyebrow">CHAPTER {chapter:02d} {html.escape(page_text)}</div>
          <h2>{title}</h2>
          {player}
          <div class="meta">{scene_count} {html.escape(unit_label)} · {duration_seconds/60:.1f} min{voice_note}</div>
          {download}
        </article>''')

    warning_html = ''
    if warnings:
        warning_html = '<div class="warnings"><strong>Preview warnings:</strong><ul>' + ''.join(
            f'<li>{html.escape(w)}</li>' for w in warnings
        ) + '</ul></div>'

    doc = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Spellcraft Video Preview</title>
<style>
:root{{color-scheme:dark}} body{{margin:0;background:#070914;color:#f4ebd6;font-family:system-ui,sans-serif}} .hero{{padding:42px 24px 20px;max-width:1100px;margin:auto}} h1{{font-family:Georgia,serif;font-size:clamp(34px,7vw,72px);margin:0;color:#d4ae56}} .sub{{color:#b8ad9e;max-width:800px}} .grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:20px;max-width:1100px;margin:0 auto;padding:20px 24px 60px}} .card{{border:1px solid #6f5a2c;border-radius:18px;padding:18px;background:#0c1020;box-shadow:0 18px 50px #0007}} .eyebrow{{font-size:12px;letter-spacing:.12em;color:#d4ae56}} h2{{font-family:Georgia,serif;font-weight:500}} video{{width:100%;border-radius:12px;background:black}} .meta{{font-size:13px;color:#aaa;margin:12px 0}} .download{{display:inline-block;padding:10px 14px;border:1px solid #d4ae56;border-radius:999px;color:#f4ebd6;text-decoration:none}} .status{{margin-top:18px;padding:12px 14px;border-radius:12px;background:#11172c;color:#c8d2ea}} .warnings{{margin-top:14px;padding:12px 14px;border-radius:12px;background:#2a1c12;color:#f2c895}} .missing{{aspect-ratio:16/9;display:grid;place-items:center;border-radius:12px;background:#05060a;color:#aaa;padding:16px;text-align:center}}
</style></head><body>
<section class="hero"><div class="eyebrow">CHECKPOINTED LONG-FORM BUILD</div><h1>Spellcraft Manual Preview</h1><p class="sub">Chapter-by-chapter player for reviewing narration, visuals, timing, and completed MP4s before the final master is assembled.</p><div class="status">{len(items)} chapter records currently available in this preview.</div>{warning_html}</section>
<main class="grid">{''.join(cards)}</main></body></html>'''
    (args.output_dir / 'index.html').write_text(doc, encoding='utf-8')
    (args.output_dir / 'catalog.json').write_text(json.dumps(items, indent=2), encoding='utf-8')
    print(f'preview built with {len(items)} chapters; warnings={len(warnings)}')
    for warning in warnings:
        print(f'WARNING: {warning}')


if __name__ == '__main__':
    main()
