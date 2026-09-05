from __future__ import annotations

import math
import re
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageOps

import cinematic_scene_renderer_v2 as v2
from cinematic_scene_renderer import W, H, FPS, GOLD, kind_for, duration

MOVES = v2.MOVES


def _ass_time(sec: float) -> str:
    sec = max(0.0, sec)
    h = int(sec // 3600)
    sec -= h * 3600
    m = int(sec // 60)
    sec -= m * 60
    s = int(sec)
    cs = int(round((sec - s) * 100))
    if cs >= 100:
        s += 1
        cs -= 100
    return f'{h}:{m:02d}:{s:02d}.{cs:02d}'


def _ass_escape(text: str) -> str:
    return text.replace('\\', '\\\\').replace('{', '\\{').replace('}', '\\}')


def _caption_lines(text: str, width: int = 54, max_lines: int = 3) -> str:
    """Mobile-first caption wrapping. Keep subtitles readable on a phone."""
    words = re.sub(r'\s+', ' ', text).strip().split()
    if not words:
        return ''
    lines: list[str] = []
    current: list[str] = []
    current_len = 0
    for word in words:
        add = len(word) + (1 if current else 0)
        if current and current_len + add > width:
            lines.append(' '.join(current))
            current = [word]
            current_len = len(word)
        else:
            current.append(word)
            current_len += add
    if current:
        lines.append(' '.join(current))

    # Sentence scenes can be long. Balance overflow into at most three readable lines.
    if len(lines) > max_lines:
        flat = ' '.join(lines)
        target = max(28, math.ceil(len(flat) / max_lines))
        words = flat.split()
        lines = []
        current = []
        current_len = 0
        for word in words:
            add = len(word) + (1 if current else 0)
            if current and current_len + add > target and len(lines) < max_lines - 1:
                lines.append(' '.join(current))
                current = [word]
                current_len = len(word)
            else:
                current.append(word)
                current_len += add
        if current:
            lines.append(' '.join(current))
    return r'\N'.join(_ass_escape(line) for line in lines)


def write_ass(text: str, dur: float, path: Path) -> None:
    wrapped = _caption_lines(text)
    content = f'''[Script Info]\nScriptType: v4.00+\nPlayResX: {W}\nPlayResY: {H}\nWrapStyle: 2\nScaledBorderAndShadow: yes\n\n[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\nStyle: Narration,DejaVu Sans,58,&H00FFF9EC,&H000000FF,&H00100D12,&HA0000000,-1,0,0,0,100,100,0,0,3,3,0,2,190,190,96,1\n\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\nDialogue: 0,0:00:00.00,{_ass_time(dur)},Narration,,0,0,0,,{wrapped}\n'''
    path.write_text(content, encoding='utf-8')


def _blurred_canvas(source: Image.Image) -> Image.Image:
    bg = ImageOps.fit(source.convert('RGB'), (W, H), method=Image.Resampling.LANCZOS)
    bg = bg.filter(ImageFilter.GaussianBlur(38)).convert('RGBA')
    shade = Image.new('RGBA', (W, H), (3, 5, 12, 105))
    return Image.alpha_composite(bg, shade)


def _smart_hero(source: Image.Image, name: str) -> Image.Image:
    """Crop text-heavy reference images less aggressively; let product photos breathe."""
    lname = name.lower()
    if any(k in lname for k in ('guide', 'color', 'chart', 'page', 'layout')):
        box = (1660, 830)
    elif source.width > source.height * 1.45:
        box = (1720, 820)
    elif source.height > source.width * 1.35:
        box = (1160, 860)
    else:
        box = (1540, 860)

    scale = min(box[0] / source.width, box[1] / source.height)
    return source.resize(
        (max(1, int(source.width * scale)), max(1, int(source.height * scale))),
        Image.Resampling.LANCZOS,
    ).convert('RGBA')


def _source_scene(text: str, index: int, out_image: Path, asset: Path) -> str:
    kind = kind_for(text)
    with Image.open(asset) as opened:
        opened.load()
        source = opened.convert('RGB').copy()

    bg = _blurred_canvas(source)
    hero = _smart_hero(source, asset.name)

    # Alternate position very slightly so hundreds of source scenes do not feel stamped.
    x = (W - hero.width) // 2
    y = (H - hero.height) // 2 - 36
    if index % 3 == 1 and hero.width < 1450:
        x -= 90
    elif index % 3 == 2 and hero.width < 1450:
        x += 90
    x = max(70, min(W - hero.width - 70, x))

    shadow = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow, 'RGBA')
    sd.rounded_rectangle((x - 24, y - 24, x + hero.width + 24, y + hero.height + 24), radius=30, fill=(0, 0, 0, 165))
    shadow = shadow.filter(ImageFilter.GaussianBlur(22))
    bg = Image.alpha_composite(bg, shadow)
    bg.alpha_composite(hero, (x, y))

    d = ImageDraw.Draw(bg, 'RGBA')
    d.rounded_rectangle((x - 4, y - 4, x + hero.width + 4, y + hero.height + 4), radius=20, outline=(232, 197, 118, 115), width=2)

    # Dark lower readability shelf behind subtitles without covering the source image.
    shelf = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    sh = ImageDraw.Draw(shelf, 'RGBA')
    sh.rectangle((0, 835, W, H), fill=(3, 4, 8, 64))
    shelf = shelf.filter(ImageFilter.GaussianBlur(18))
    bg = Image.alpha_composite(bg, shelf)

    out_image.parent.mkdir(parents=True, exist_ok=True)
    bg.convert('RGB').save(out_image, quality=95, subsampling=0)
    return kind


def _altar_variant(index: int, out_image: Path) -> str:
    """Four distinct fallback compositions to stop the default altar from repeating endlessly."""
    variant = index % 4
    palettes = [
        ((8, 10, 18), (31, 20, 36)),
        ((11, 15, 19), (42, 29, 19)),
        ((8, 17, 16), (24, 42, 34)),
        ((8, 9, 24), (30, 20, 48)),
    ]
    top, bottom = palettes[variant]
    im = Image.new('RGB', (W, H), top)
    d = ImageDraw.Draw(im)
    for yy in range(H):
        u = yy / (H - 1)
        c = tuple(int(top[i] * (1 - u) + bottom[i] * u) for i in range(3))
        d.line((0, yy, W, yy), fill=c)
    im = im.convert('RGBA')
    d = ImageDraw.Draw(im, 'RGBA')

    # Different geometry on every fallback rather than one repeated parchment altar.
    if variant == 0:
        d.ellipse((690, 260, 1230, 800), outline=GOLD + (150,), width=5)
        d.ellipse((760, 330, 1160, 730), outline=GOLD + (70,), width=3)
        d.rounded_rectangle((835, 450, 1085, 700), radius=20, fill=(214, 190, 145, 225), outline=(128, 92, 50, 180), width=3)
        for x, col in ((560, (238, 229, 212)), (1360, (93, 72, 150))):
            d.rounded_rectangle((x - 45, 590, x + 45, 900), radius=18, fill=col + (255,))
            d.polygon([(x, 515), (x - 24, 585), (x, 610), (x + 24, 585)], fill=(255, 185, 65, 245))
    elif variant == 1:
        d.rounded_rectangle((245, 260, 840, 790), radius=38, fill=(215, 192, 151, 225), outline=(140, 100, 54, 180), width=4)
        for yy in range(350, 690, 65):
            d.line((330, yy, 755, yy), fill=(100, 72, 45, 75), width=2)
        d.ellipse((1210, 300, 1610, 700), outline=GOLD + (125,), width=5)
        d.ellipse((1315, 405, 1505, 595), fill=(35, 56, 50, 205), outline=(145, 188, 145, 100), width=3)
        d.rounded_rectangle((1050, 690, 1740, 900), radius=45, fill=(18, 15, 15, 180))
    elif variant == 2:
        pts = [(960, 210), (570, 800), (1350, 800)]
        d.line(pts + [pts[0]], fill=GOLD + (155,), width=5)
        for x, y, col in ((960, 300, (240, 233, 214)), (620, 820, (58, 120, 74)), (1300, 820, (94, 72, 150))):
            d.rounded_rectangle((x - 42, y - 260, x + 42, y), radius=16, fill=col + (255,))
            d.polygon([(x, y - 335), (x - 22, y - 266), (x, y - 242), (x + 22, y - 266)], fill=(255, 179, 58, 245))
        d.ellipse((800, 470, 1120, 790), fill=(212, 188, 143, 210), outline=(134, 95, 54, 180), width=3)
    else:
        d.ellipse((260, 160, 720, 620), fill=(223, 223, 210, 225))
        d.ellipse((385, 120, 770, 575), fill=(18, 19, 36, 255))
        d.rounded_rectangle((880, 250, 1640, 790), radius=42, fill=(28, 23, 38, 190), outline=GOLD + (95,), width=3)
        for j in range(9):
            x = 980 + (j % 3) * 220
            y = 360 + (j // 3) * 150
            d.ellipse((x - 24, y - 24, x + 24, y + 24), fill=(224, 196, 119, 165))
        d.rounded_rectangle((360, 680, 760, 900), radius=28, fill=(207, 185, 144, 215))

    # subtle stars, varying by index
    for i in range(80):
        x = (i * 197 + index * 71) % W
        y = (i * 83 + index * 107) % 760
        d.ellipse((x, y, x + 2, y + 2), fill=(236, 215, 159, 45 + (i * 23) % 55))

    out_image.parent.mkdir(parents=True, exist_ok=True)
    im.convert('RGB').save(out_image, quality=94, subsampling=0)
    return 'altar'


def make_scene(text: str, index: int, out_image: Path, asset: Path | None = None) -> str:
    if asset and asset.exists():
        try:
            return _source_scene(text, index, out_image, asset)
        except Exception as exc:
            print(f'v6 source presentation fallback at scene {index}: {asset.name}: {exc}', flush=True)

    kind = kind_for(text)
    if kind == 'altar':
        return _altar_variant(index, out_image)
    return v2.make_scene(text, index, out_image, asset=None)


def render_ken_burns(still: Path, audio: Path, subtitle: str, out: Path, move: str = 'zoom_in') -> None:
    dur = duration(audio)
    frames = max(1, int(math.ceil(dur * FPS)))
    work = Path(tempfile.mkdtemp(prefix='spellcraft_v6_scene_'))
    ass = work / 'sub.ass'
    write_ass(subtitle, dur, ass)
    assf = str(ass).replace('\\', '/').replace(':', '\\:').replace("'", "\\'")
    if move == 'zoom_out':
        z = "if(eq(on,0),1.10,max(1.0,zoom-0.00065))"
        x = 'iw/2-(iw/zoom/2)'
        y = 'ih/2-(ih/zoom/2)'
    elif move == 'pan_left':
        z = '1.06'
        x = f"(iw-iw/zoom)*(1-on/{frames})"
        y = 'ih/2-(ih/zoom/2)'
    elif move == 'pan_right':
        z = '1.06'
        x = f"(iw-iw/zoom)*(on/{frames})"
        y = 'ih/2-(ih/zoom/2)'
    else:
        z = 'min(zoom+0.00065,1.10)'
        x = 'iw/2-(iw/zoom/2)'
        y = 'ih/2-(ih/zoom/2)'
    vf = f"zoompan=z='{z}':x='{x}':y='{y}':d=1:s={W}x{H}:fps={FPS},ass='{assf}',format=yuv420p"
    subprocess.run([
        'ffmpeg', '-y', '-v', 'error', '-loop', '1', '-i', str(still), '-i', str(audio),
        '-vf', vf, '-t', f'{dur:.3f}', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20',
        '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', str(out)
    ], check=True)


def render_tentpole(still: Path, audio: Path, subtitle: str, out: Path, kind: str, seed: int = 0) -> None:
    """Keep v2 object motion but burn the larger v6 mobile caption over the result."""
    dur = duration(audio)
    work = Path(tempfile.mkdtemp(prefix='spellcraft_v6_tentpole_'))
    raw = work / 'motion.mp4'
    v2.render_tentpole(still, audio, '', raw, kind, seed=seed)
    ass = work / 'sub.ass'
    write_ass(subtitle, dur, ass)
    assf = str(ass).replace('\\', '/').replace(':', '\\:').replace("'", "\\'")
    subprocess.run([
        'ffmpeg', '-y', '-v', 'error', '-i', str(raw), '-vf', f"ass='{assf}'",
        '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20', '-c:a', 'copy',
        '-movflags', '+faststart', str(out)
    ], check=True)
