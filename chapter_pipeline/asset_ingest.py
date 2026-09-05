from __future__ import annotations

import hashlib
import math
from pathlib import Path

from PIL import Image, ImageFile

SUPPORTED = {'.jpg', '.jpeg', '.png', '.webp'}


def _fingerprint(path: Path) -> str:
    st = path.stat()
    payload = f'{path.resolve()}|{st.st_size}|{st.st_mtime_ns}'.encode('utf-8')
    return hashlib.sha1(payload).hexdigest()[:16]


def visual_health(image: Image.Image) -> tuple[bool, str]:
    """Reject images that decode but are effectively blank/corrupt.

    Some damaged JPEGs are technically readable when Pillow salvages truncated data,
    yet their pixels collapse into a nearly black rectangle.  A decode-only preflight
    therefore is not enough for a visual production pipeline.  This check deliberately
    uses conservative thresholds so legitimate dark black/gold Spellcraft artwork still
    passes because it retains real tonal variation.
    """
    probe = image.convert('L').copy()
    probe.thumbnail((128, 128), Image.Resampling.LANCZOS)
    pixels = list(probe.getdata())
    if not pixels:
        return False, 'no pixels after decode'

    n = len(pixels)
    mean = sum(pixels) / n
    variance = sum((p - mean) ** 2 for p in pixels) / n
    stddev = math.sqrt(variance)
    near_black = sum(p < 18 for p in pixels) / n
    very_dark = sum(p < 32 for p in pixels) / n

    # Truly blank/salvaged-black images have almost no usable tonal structure.
    if mean < 14 and stddev < 24:
        return False, f'visually blank/corrupt mean={mean:.1f} std={stddev:.1f}'
    if near_black > 0.965 and stddev < 30:
        return False, f'visually blank/corrupt near_black={near_black:.3f} std={stddev:.1f}'
    if very_dark > 0.985 and mean < 24:
        return False, f'visually blank/corrupt very_dark={very_dark:.3f} mean={mean:.1f}'

    return True, f'mean={mean:.1f} std={stddev:.1f} near_black={near_black:.3f}'


def canonicalize_asset(path: Path | None, cache_dir: Path) -> Path | None:
    """Fully decode a source image, validate pixels, then rewrite a clean PNG.

    The returned file is safe for the renderer to reopen. A bad source asset never crashes
    or silently becomes a black rectangle; callers receive None and can fall back to a
    source-specific reconstruction/cinematic scene instead.
    """
    if not path or not path.exists() or path.suffix.lower() not in SUPPORTED:
        return None

    cache_dir.mkdir(parents=True, exist_ok=True)
    out = cache_dir / f'{path.stem}_{_fingerprint(path)}.png'

    if out.exists() and out.stat().st_size > 1000:
        try:
            with Image.open(out) as im:
                im.load()
                if im.width >= 64 and im.height >= 64:
                    healthy, detail = visual_health(im)
                    if healthy:
                        return out
                    print(f'asset rejected before render: {path.name}: {detail}', flush=True)
                    out.unlink(missing_ok=True)
                    return None
        except Exception:
            out.unlink(missing_ok=True)

    old_flag = ImageFile.LOAD_TRUNCATED_IMAGES
    try:
        # This flag is used only in the ingestion/sanitizing boundary. The renderer itself
        # receives a newly written PNG and never needs to tolerate malformed source bytes.
        ImageFile.LOAD_TRUNCATED_IMAGES = True
        with Image.open(path) as im:
            im.load()  # force complete pixel decode now, before any long render starts
            if im.width < 64 or im.height < 64:
                return None
            clean = im.convert('RGB').copy()

        healthy, detail = visual_health(clean)
        if not healthy:
            print(f'asset rejected before render: {path.name}: {detail}', flush=True)
            return None

        clean.save(out, format='PNG', optimize=True)
        with Image.open(out) as verify:
            verify.load()
            if verify.width < 64 or verify.height < 64:
                out.unlink(missing_ok=True)
                return None
            healthy, detail = visual_health(verify)
            if not healthy:
                print(f'asset rejected after rewrite: {path.name}: {detail}', flush=True)
                out.unlink(missing_ok=True)
                return None

        print(f'asset visual health OK: {path.name}: {detail}', flush=True)
        return out
    except Exception as exc:
        print(f'asset rejected before render: {path.name}: {exc}', flush=True)
        out.unlink(missing_ok=True)
        return None
    finally:
        ImageFile.LOAD_TRUNCATED_IMAGES = old_flag


def preflight_asset_directory(asset_dir: Path, cache_dir: Path) -> dict[str, Path]:
    """Sanitize every supported image in an asset directory before scene rendering begins."""
    sanitized: dict[str, Path] = {}
    if not asset_dir.exists():
        return sanitized
    for path in sorted(asset_dir.iterdir()):
        if path.suffix.lower() not in SUPPORTED:
            continue
        clean = canonicalize_asset(path, cache_dir)
        if clean:
            sanitized[path.name.lower()] = clean
    return sanitized
