from __future__ import annotations

import argparse
import json
from pathlib import Path

import fitz


def overlap(a, b):
    r1, r2 = fitz.Rect(a), fitz.Rect(b)
    inter = r1 & r2
    if inter.is_empty:
        return 0.0
    return inter.get_area() / max(1.0, r1.get_area())


def main():
    ap = argparse.ArgumentParser(description='Extract clean PDF image assets while rejecting text-contaminated crops and full body-text pages.')
    ap.add_argument('pdf', type=Path)
    ap.add_argument('--output-dir', type=Path, default=Path('book_assets'))
    ap.add_argument('--min-width', type=int, default=240)
    ap.add_argument('--min-height', type=int, default=180)
    ap.add_argument('--max-text-overlap', type=float, default=0.015)
    args = ap.parse_args()

    clean = args.output_dir / 'clean'
    rejected = args.output_dir / 'rejected'
    clean.mkdir(parents=True, exist_ok=True)
    rejected.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(args.pdf)
    ledger = []

    for pno, page in enumerate(doc, 1):
        text_blocks = [b[:4] for b in page.get_text('blocks') if str(b[4]).strip()]
        for idx, info in enumerate(page.get_image_info(xrefs=True), 1):
            bbox = info.get('bbox')
            xref = int(info.get('xref') or 0)
            if not bbox or not xref:
                continue
            pix = fitz.Pixmap(doc, xref)
            if pix.alpha or pix.n > 4:
                pix = fitz.Pixmap(fitz.csRGB, pix)
            w, h = pix.width, pix.height
            contaminated = max([overlap(bbox, tb) for tb in text_blocks] or [0.0])
            ok = w >= args.min_width and h >= args.min_height and contaminated <= args.max_text_overlap
            outdir = clean if ok else rejected
            target = outdir / f'p{pno:03d}_img{idx:02d}_{w}x{h}.png'
            pix.save(target)
            ledger.append({
                'page': pno, 'index': idx, 'xref': xref, 'width': w, 'height': h,
                'bbox': [round(float(x), 2) for x in bbox],
                'max_text_overlap': round(contaminated, 5),
                'accepted': ok, 'file': target.as_posix(),
            })

    (args.output_dir / 'asset_ledger.json').write_text(json.dumps(ledger, indent=2), encoding='utf-8')
    accepted = sum(1 for x in ledger if x['accepted'])
    print(json.dumps({'pages': len(doc), 'assets': len(ledger), 'accepted': accepted, 'rejected': len(ledger)-accepted}, indent=2))


if __name__ == '__main__':
    main()
