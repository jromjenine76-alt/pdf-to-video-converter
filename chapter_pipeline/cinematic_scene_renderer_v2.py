from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

from cinematic_scene_renderer import (
    MOVES,
    W,
    H,
    kind_for,
    make_scene as _legacy_make_scene,
    render_ken_burns,
    render_tentpole,
)


def _cover_fit(im: Image.Image, size: tuple[int, int]) -> Image.Image:
    tw, th = size
    scale = max(tw / im.width, th / im.height)
    r = im.resize((max(1, int(im.width*scale)), max(1, int(im.height*scale))), Image.Resampling.LANCZOS)
    x = max(0, (r.width-tw)//2)
    y = max(0, (r.height-th)//2)
    return r.crop((x, y, x+tw, y+th))


def _contain(im: Image.Image, size: tuple[int, int]) -> Image.Image:
    tw, th = size
    scale = min(tw / im.width, th / im.height)
    return im.resize((max(1, int(im.width*scale)), max(1, int(im.height*scale))), Image.Resampling.LANCZOS)


def make_scene(text: str, index: int, out_image: Path, asset: Path | None = None) -> str:
    """Use a clean source/reconstruction as the visual field; never let a bad image kill a render."""
    if not asset or not asset.exists():
        return _legacy_make_scene(text, index, out_image, asset=None)

    kind = kind_for(text)
    try:
        with Image.open(asset) as opened:
            opened.load()
            source = opened.convert('RGB').copy()
    except Exception as exc:
        print(f'cinematic asset fallback at scene {index}: {asset.name}: {exc}', flush=True)
        return _legacy_make_scene(text, index, out_image, asset=None)

    bg = _cover_fit(source, (W, H)).filter(ImageFilter.GaussianBlur(42)).convert('RGBA')
    shade = Image.new('RGBA', (W, H), (3, 5, 12, 92))
    bg = Image.alpha_composite(bg, shade)

    hero = _contain(source, (1500, 880)).convert('RGBA')
    x = (W-hero.width)//2
    y = (H-hero.height)//2 - 22

    shadow = Image.new('RGBA', (W,H), (0,0,0,0))
    sd = ImageDraw.Draw(shadow, 'RGBA')
    sd.rounded_rectangle((x-25,y-25,x+hero.width+25,y+hero.height+25), radius=32, fill=(0,0,0,150))
    shadow = shadow.filter(ImageFilter.GaussianBlur(25))
    bg = Image.alpha_composite(bg, shadow)

    bg.alpha_composite(hero, (x,y))
    d = ImageDraw.Draw(bg, 'RGBA')
    d.rounded_rectangle((x-4,y-4,x+hero.width+4,y+hero.height+4), radius=24, outline=(218,180,96,92), width=2)

    vignette = Image.new('RGBA',(W,H),(0,0,0,0))
    vd = ImageDraw.Draw(vignette,'RGBA')
    vd.rectangle((0,0,W,H), outline=(0,0,0,150), width=95)
    vignette = vignette.filter(ImageFilter.GaussianBlur(45))
    bg = Image.alpha_composite(bg, vignette)

    out_image.parent.mkdir(parents=True, exist_ok=True)
    bg.convert('RGB').save(out_image, quality=94, subsampling=0)
    return kind
