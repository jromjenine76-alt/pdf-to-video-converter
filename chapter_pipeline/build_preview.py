from __future__ import annotations

import argparse
import html
import json
import shutil
from pathlib import Path


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--chapters-dir', type=Path, default=Path('chapter_output'))
    ap.add_argument('--output-dir', type=Path, default=Path('preview_app'))
    args = ap.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    media = args.output_dir / 'media'
    media.mkdir(exist_ok=True)

    items = []
    for meta_path in sorted(args.chapters_dir.glob('chapter_*.json')):
        meta = json.loads(meta_path.read_text(encoding='utf-8'))
        src = args.chapters_dir / meta['video']
        if src.exists():
            dst = media / src.name
            if not dst.exists():
                shutil.copy2(src, dst)
            meta['video_url'] = f'media/{dst.name}'
        items.append(meta)

    cards = []
    for item in items:
        pages = item.get('source_pages') or []
        page_text = '' if not pages else f"Pages {pages[0]}–{pages[-1]}"
        scene_count = item.get('scenes', item.get('chunks', 0))
        duration_seconds = float(item.get('duration_seconds', item.get('duration', 0.0)))
        unit_label = 'cinematic scenes' if 'scenes' in item else 'checkpointed segments'
        cards.append(f'''
        <article class="card">
          <div class="eyebrow">CHAPTER {item['chapter']:02d} {html.escape(page_text)}</div>
          <h2>{html.escape(item['title'])}</h2>
          <video controls preload="metadata" src="{html.escape(item.get('video_url',''))}"></video>
          <div class="meta">{scene_count} {unit_label} · {duration_seconds/60:.1f} min</div>
          <a class="download" href="{html.escape(item.get('video_url',''))}" download>Download chapter MP4</a>
        </article>''')

    doc = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Spellcraft Video Preview</title>
<style>
:root{{color-scheme:dark}} body{{margin:0;background:#070914;color:#f4ebd6;font-family:system-ui,sans-serif}} .hero{{padding:42px 24px 20px;max-width:1100px;margin:auto}} h1{{font-family:Georgia,serif;font-size:clamp(34px,7vw,72px);margin:0;color:#d4ae56}} .sub{{color:#b8ad9e;max-width:800px}} .grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:20px;max-width:1100px;margin:0 auto;padding:20px 24px 60px}} .card{{border:1px solid #6f5a2c;border-radius:18px;padding:18px;background:#0c1020;box-shadow:0 18px 50px #0007}} .eyebrow{{font-size:12px;letter-spacing:.12em;color:#d4ae56}} h2{{font-family:Georgia,serif;font-weight:500}} video{{width:100%;border-radius:12px;background:black}} .meta{{font-size:13px;color:#aaa;margin:12px 0}} .download{{display:inline-block;padding:10px 14px;border:1px solid #d4ae56;border-radius:999px;color:#f4ebd6;text-decoration:none}} .status{{margin-top:18px;padding:12px 14px;border-radius:12px;background:#11172c;color:#c8d2ea}}
</style></head><body>
<section class="hero"><div class="eyebrow">CHECKPOINTED LONG-FORM BUILD</div><h1>Spellcraft Manual Preview</h1><p class="sub">Chapter-by-chapter player for reviewing narration, visuals, timing, and completed MP4s before the final master is assembled.</p><div class="status">{len(items)} chapter videos currently available in this preview.</div></section>
<main class="grid">{''.join(cards)}</main></body></html>'''
    (args.output_dir / 'index.html').write_text(doc, encoding='utf-8')
    (args.output_dir / 'catalog.json').write_text(json.dumps(items, indent=2), encoding='utf-8')
    print(f'preview built with {len(items)} chapters')


if __name__ == '__main__':
    main()
