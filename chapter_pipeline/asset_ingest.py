from __future__ import annotations

import hashlib
from pathlib import Path

from PIL import Image, ImageFile

SUPPORTED = {'.jpg', '.jpeg', '.png', '.webp'}


def _fingerprint(path: Path) -> str:
    st = path.stat()
    payload = f'{path.resolve()}|{st.st_size}|{st.st_mtime_ns}'.encode('utf-8')
    return hashlib.sha1(payload).hexdigest()[:16]


def canonicalize_asset(path: Path | None, cache_dir: Path) -> Path | None:
    """Fully decode a source image, salvage truncated JPEGs when possible, then rewrite a clean PNG.

    The returned file is safe for the renderer to reopen. A bad source asset never crashes the
    render; callers receive None and can fall back to a reconstruction/cinematic scene instead.
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
                    return out
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
        clean.save(out, format='PNG', optimize=True)
        with Image.open(out) as verify:
            verify.load()
            if verify.width < 64 or verify.height < 64:
                out.unlink(missing_ok=True)
                return None
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
