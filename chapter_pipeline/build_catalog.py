from __future__ import annotations

import argparse
import gzip
import json
from pathlib import Path


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--narration-dir', type=Path, default=Path('spellcraft_narration'))
    ap.add_argument('--output', type=Path, default=Path('chapter_pipeline/catalog.json'))
    args = ap.parse_args()

    chapters = []
    for ep in range(1, 9):
        src = args.narration_dir / f'ep{ep}.tsv.gz'
        if not src.exists():
            continue
        sections = []
        with gzip.open(src, 'rt', encoding='utf-8') as fh:
            for line in fh:
                if not line.strip():
                    continue
                unit, target, text = line.rstrip('\n').split('\t', 2)
                sections.append({
                    'id': int(unit),
                    'text': text.replace('\\n', '\n'),
                    'legacy_target_seconds': float(target),
                })
        chapters.append({
            'id': ep,
            'slug': f'episode-{ep:02d}',
            'title': f'Spellcraft Manual · Episode {ep}',
            'source_pages': [],
            'sections': sections,
        })

    payload = {
        'project': 'Complete Manifestation & Spellcraft Manual',
        'catalog_version': 1,
        'note': 'Adapter catalog built from the existing narration bundles. Replace source_pages/title groupings with the audited 231-page chapter map without changing the downstream pipeline.',
        'chapters': chapters,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2), encoding='utf-8')
    print(f'wrote {args.output} with {len(chapters)} chapters')


if __name__ == '__main__':
    main()
