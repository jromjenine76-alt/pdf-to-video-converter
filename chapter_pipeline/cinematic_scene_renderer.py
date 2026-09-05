from __future__ import annotations

import math
import re
import subprocess
import tempfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter

W, H = 1920, 1080
FPS = 24
GOLD = (211, 171, 82)


def run(*args: str) -> None:
    subprocess.run(list(args), check=True)


def duration(path: Path) -> float:
    return float(subprocess.check_output([
        'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1', str(path)
    ], text=True).strip())


def kind_for(text: str) -> str:
    t = text.lower()
    if any(k in t for k in ('safety', 'heat-resistant', 'extinguish', 'unattended', 'ventilation', 'fire extinguisher')):
        return 'safety'
    if any(k in t for k in ('wyspell', 'soul sticks', 'lo scarabeo', 'kit', 'selenite')):
        return 'kit'
    if any(k in t for k in ('triangle', 'pentagram', 'hexagram', 'ring of fire', 'layout', 'arrange', 'cardinal', 'square', 'cross')):
        return 'layout'
    if any(k in t for k in ('flame', 'wax', 'ceromancy', 'pyromancy', 'smoke', 'soot')):
        return 'flame'
    if any(k in t for k in ('sage', 'mugwort', 'palo santo', 'herb', 'botanical', 'incense')):
        return 'herb'
    if any(k in t for k in ('petition', 'quill', 'seal', 'sealing wax', 'sigil', 'scribe')):
        return 'petition'
    if any(k in t for k in ('moon', 'lunar', 'starseed', 'celestial', 'planet', 'cosmic', 'star')):
        return 'celestial'
    if any(k in t for k in ('money', 'luck', 'gambling', 'abundance', 'prosperity')):
        return 'prosperity'
    if any(k in t for k in ('dream', 'sleep', 'third eye', 'scry', 'mirror')):
        return 'dream'
    return 'altar'


def _gradient(top, bottom):
    im = Image.new('RGB', (W, H), top)
    d = ImageDraw.Draw(im)
    for y in range(H):
        u = y / max(1, H - 1)
        c = tuple(int(top[i] * (1-u) + bottom[i] * u) for i in range(3))
        d.line((0, y, W, y), fill=c)
    return im


def _glow(im: Image.Image, center, radius, color, alpha=120):
    layer = Image.new('RGBA', im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    x, y = center
    d.ellipse((x-radius, y-radius, x+radius, y+radius), fill=(*color, alpha))
    layer = layer.filter(ImageFilter.GaussianBlur(max(1, radius // 2)))
    return Image.alpha_composite(im.convert('RGBA'), layer)


def _candle(im: Image.Image, x, y, height=300, color=(235, 226, 208), flame=True, scale=1.0):
    d = ImageDraw.Draw(im, 'RGBA')
    w = int(72 * scale)
    h = int(height * scale)
    d.rounded_rectangle((x-w//2, y-h, x+w//2, y), radius=max(8, w//6), fill=(*color, 255), outline=(255, 255, 255, 45), width=2)
    d.line((x, y-h, x, y-h-25), fill=(55, 37, 25, 255), width=max(2, int(4*scale)))
    if flame:
        glow = _glow(im, (x, y-h-48), 120, (255, 157, 54), 95)
        im.paste(glow.convert('RGBA'))
        d = ImageDraw.Draw(im, 'RGBA')
        d.polygon([(x, y-h-105), (x-25, y-h-32), (x, y-h-8), (x+24, y-h-34)], fill=(255, 178, 55, 245))
        d.polygon([(x, y-h-78), (x-10, y-h-32), (x, y-h-13), (x+10, y-h-33)], fill=(255, 244, 173, 255))


def _parchment(im: Image.Image, box=(680, 390, 1240, 760), seal=True):
    d = ImageDraw.Draw(im, 'RGBA')
    x1, y1, x2, y2 = box
    d.rounded_rectangle((x1+18, y1+20, x2+18, y2+20), radius=25, fill=(0, 0, 0, 90))
    d.rounded_rectangle(box, radius=22, fill=(222, 200, 155, 245), outline=(130, 94, 52, 200), width=4)
    for yy in range(y1+70, y2-55, 55):
        d.line((x1+65, yy, x2-65, yy), fill=(106, 78, 48, 70), width=2)
    if seal:
        cx, cy = x2-95, y2-68
        d.ellipse((cx-52, cy-52, cx+52, cy+52), fill=(126, 27, 37, 245), outline=GOLD+(220,), width=4)
        d.ellipse((cx-25, cy-25, cx+25, cy+25), outline=(221, 170, 95, 180), width=3)


def _plant(im: Image.Image, x, y, scale=1.0, color=(92, 130, 78)):
    d = ImageDraw.Draw(im, 'RGBA')
    stem = int(280 * scale)
    d.line((x, y, x, y-stem), fill=(76, 104, 61, 240), width=max(3, int(6*scale)))
    for i in range(8):
        yy = y - int((i+1) * stem / 9)
        side = -1 if i % 2 == 0 else 1
        dx = int(85 * scale)
        d.line((x, yy, x+side*dx, yy-int(30*scale)), fill=(76, 104, 61, 220), width=max(2, int(4*scale)))
        ex, ey = x+side*dx, yy-int(30*scale)
        d.ellipse((ex-int(38*scale), ey-int(18*scale), ex+int(38*scale), ey+int(18*scale)), fill=(*color, 235))


def _geometry(im: Image.Image, center=(960, 600), kind='triangle'):
    d = ImageDraw.Draw(im, 'RGBA')
    cx, cy = center
    r = 310
    if kind == 'triangle':
        pts = [(cx, cy-r), (cx-int(r*.87), cy+int(r*.5)), (cx+int(r*.87), cy+int(r*.5))]
        d.line(pts+[pts[0]], fill=GOLD+(190,), width=5)
    elif kind == 'hexagram':
        p1 = [(cx, cy-r), (cx-int(r*.87), cy+int(r*.5)), (cx+int(r*.87), cy+int(r*.5))]
        p2 = [(cx, cy+r), (cx-int(r*.87), cy-int(r*.5)), (cx+int(r*.87), cy-int(r*.5))]
        d.line(p1+[p1[0]], fill=GOLD+(180,), width=4)
        d.line(p2+[p2[0]], fill=GOLD+(180,), width=4)
    elif kind == 'pentagram':
        pts = []
        for i in range(5):
            a = -math.pi/2 + i*2*math.pi/5
            pts.append((cx+int(r*math.cos(a)), cy+int(r*math.sin(a))))
        order = [0, 2, 4, 1, 3, 0]
        d.line([pts[i] for i in order], fill=GOLD+(190,), width=5)
    else:
        d.ellipse((cx-r, cy-r, cx+r, cy+r), outline=GOLD+(180,), width=5)
        d.ellipse((cx-r+55, cy-r+55, cx+r-55, cy+r-55), outline=GOLD+(95,), width=3)


def make_scene(text: str, index: int, out_image: Path, asset: Path | None = None) -> str:
    kind = kind_for(text)
    palettes = {
        'safety': ((14, 18, 24), (43, 30, 21)), 'kit': ((10, 15, 30), (35, 24, 44)),
        'layout': ((5, 8, 18), (20, 15, 34)), 'flame': ((15, 9, 8), (58, 28, 14)),
        'herb': ((8, 18, 15), (26, 44, 31)), 'petition': ((15, 11, 17), (47, 30, 24)),
        'celestial': ((5, 8, 24), (18, 13, 45)), 'prosperity': ((8, 18, 13), (29, 41, 20)),
        'dream': ((8, 10, 24), (24, 19, 44)), 'altar': ((8, 10, 18), (28, 20, 31)),
    }
    im = _gradient(*palettes[kind]).convert('RGBA')
    im = _glow(im, (1500, 260), 480, (85, 55, 145), 45)
    im = _glow(im, (470, 830), 430, (155, 95, 38), 36)
    d = ImageDraw.Draw(im, 'RGBA')
    for i in range(120):
        x = (i*197 + index*67) % W
        y = (i*83 + index*113) % H
        a = 35 + (i*29) % 55
        d.ellipse((x, y, x+2, y+2), fill=(236, 215, 159, a))
    d.polygon([(0, 760), (W, 690), (W, H), (0, H)], fill=(12, 10, 11, 170))

    if asset and asset.exists():
        a = Image.open(asset).convert('RGBA')
        maxw, maxh = 900, 820
        sc = min(maxw/a.width, maxh/a.height)
        a = a.resize((int(a.width*sc), int(a.height*sc)), Image.Resampling.LANCZOS)
        shadow = Image.new('RGBA', im.size, (0, 0, 0, 0))
        sd = ImageDraw.Draw(shadow)
        x = W-a.width-120
        y = (H-a.height)//2
        sd.rounded_rectangle((x-18, y-18, x+a.width+18, y+a.height+18), radius=28, fill=(0, 0, 0, 130))
        shadow = shadow.filter(ImageFilter.GaussianBlur(16))
        im = Image.alpha_composite(im, shadow)
        im.alpha_composite(a, (x, y))
        _candle(im, 360, 905, 330, (242, 235, 220), True, 1.0)
    elif kind == 'safety':
        d = ImageDraw.Draw(im, 'RGBA')
        d.rounded_rectangle((330, 720, 1570, 960), radius=60, fill=(55, 48, 47, 240), outline=(130, 118, 105, 160), width=4)
        _candle(im, 790, 790, 290, (238, 231, 214), True, 1.05)
        d.ellipse((1080, 770, 1370, 930), fill=(68, 95, 115, 180), outline=(190, 210, 220, 120), width=3)
        d.ellipse((1105, 785, 1345, 910), fill=(110, 160, 182, 120))
        _parchment(im, (230, 330, 670, 610), False)
        d.line((700, 590, 700, 820), fill=GOLD+(110,), width=3)
    elif kind == 'kit':
        _candle(im, 430, 860, 330, (231, 219, 199), True, 1.0)
        _plant(im, 760, 900, 1.0, (98, 132, 78))
        _parchment(im, (900, 350, 1480, 720), True)
        d = ImageDraw.Draw(im, 'RGBA')
        d.polygon([(1430, 855), (1670, 790), (1710, 825), (1465, 900)], fill=(210, 220, 226, 210), outline=(255, 255, 255, 130))
    elif kind == 'layout':
        lower = text.lower()
        gkind = 'pentagram' if 'pentagram' in lower else ('hexagram' if 'hexagram' in lower else 'triangle')
        _geometry(im, (960, 580), gkind)
        for x, y, c in [(960, 270, (245, 239, 219)), (620, 760, (225, 92, 41)), (1300, 760, (83, 99, 215))]:
            _candle(im, x, y+130, 230, c, True, .78)
        _parchment(im, (790, 470, 1130, 710), True)
    elif kind == 'flame':
        _candle(im, 960, 940, 520, (238, 224, 198), True, 1.6)
        d = ImageDraw.Draw(im, 'RGBA')
        d.ellipse((650, 875, 1270, 1015), fill=(230, 214, 185, 130))
    elif kind == 'herb':
        _plant(im, 560, 925, 1.35, (95, 131, 79))
        _plant(im, 960, 900, 1.1, (78, 117, 72))
        _plant(im, 1360, 930, 1.25, (130, 99, 62))
        d = ImageDraw.Draw(im, 'RGBA')
        for cx in (560, 960, 1360):
            d.ellipse((cx-130, 840, cx+130, 980), fill=(64, 43, 28, 230), outline=(124, 91, 57, 160), width=4)
    elif kind == 'petition':
        _parchment(im, (530, 290, 1390, 840), True)
        d = ImageDraw.Draw(im, 'RGBA')
        d.polygon([(410, 280), (460, 245), (1090, 725), (1050, 758)], fill=(32, 28, 26, 240))
        d.polygon([(405, 278), (445, 205), (475, 248)], fill=(230, 218, 190, 220))
    elif kind == 'celestial':
        im = _glow(im, (1440, 300), 390, (122, 145, 225), 80)
        d = ImageDraw.Draw(im, 'RGBA')
        d.ellipse((1260, 120, 1620, 480), fill=(224, 226, 213, 230))
        d.ellipse((1360, 115, 1650, 455), fill=(17, 18, 31, 255))
        _candle(im, 520, 900, 330, (237, 231, 217), True, 1.0)
        _geometry(im, (850, 560), 'hexagram')
    elif kind == 'prosperity':
        _candle(im, 740, 900, 370, (49, 112, 66), True, 1.1)
        _parchment(im, (900, 360, 1450, 750), True)
        d = ImageDraw.Draw(im, 'RGBA')
        for j in range(14):
            x = 1160 + (j % 5) * 70 + (j % 2) * 18
            y = 840 - (j // 5) * 32
            d.ellipse((x-28, y-14, x+28, y+14), fill=(184, 141, 53, 235), outline=(236, 195, 92, 160))
    elif kind == 'dream':
        d = ImageDraw.Draw(im, 'RGBA')
        d.rounded_rectangle((280, 720, 1420, 970), radius=60, fill=(40, 38, 55, 230))
        d.rounded_rectangle((360, 650, 810, 850), radius=35, fill=(95, 89, 116, 190))
        d.ellipse((1370, 170, 1690, 490), fill=(225, 224, 205, 235))
        d.ellipse((1450, 140, 1730, 450), fill=(19, 18, 35, 255))
        d.polygon([(1180, 815), (1470, 760), (1490, 800), (1200, 860)], fill=(220, 226, 231, 210), outline=(255, 255, 255, 100))
    else:
        _candle(im, 420, 910, 360, (238, 229, 212), True, 1.05)
        _candle(im, 1500, 900, 320, (92, 68, 143), True, .95)
        _parchment(im, (690, 390, 1260, 760), True)
        _plant(im, 570, 930, .85, (90, 127, 78))

    vign = Image.new('L', (W, H), 0)
    vd = ImageDraw.Draw(vign)
    vd.ellipse((-260, -170, W+260, H+300), fill=230)
    vign = vign.filter(ImageFilter.GaussianBlur(130))
    black = Image.new('RGBA', (W, H), (0, 0, 0, 255))
    im = Image.composite(im, black, vign)
    noise = Image.effect_noise((W, H), 18).convert('L').point(lambda p: int(p * 0.10))
    grain = Image.new('RGBA', (W, H), (255, 255, 255, 0))
    grain.putalpha(noise)
    im = Image.alpha_composite(im, grain)
    out_image.parent.mkdir(parents=True, exist_ok=True)
    im.convert('RGB').save(out_image, 'JPEG', quality=91, subsampling=0)
    return kind


def _ass_time(sec: float) -> str:
    sec = max(0.0, sec)
    h = int(sec // 3600)
    sec -= h * 3600
    m = int(sec // 60)
    sec -= m * 60
    s = int(sec)
    cs = int(round((sec-s) * 100))
    if cs >= 100:
        s += 1
        cs -= 100
    return f'{h}:{m:02d}:{s:02d}.{cs:02d}'


def _ass_escape(text: str) -> str:
    return re.sub(r'\s+', ' ', text).strip().replace('\\', '\\\\').replace('{', '\\{').replace('}', '\\}')


def write_ass(text: str, dur: float, path: Path) -> None:
    content = f'''[Script Info]\nScriptType: v4.00+\nPlayResX: {W}\nPlayResY: {H}\nWrapStyle: 2\nScaledBorderAndShadow: yes\n\n[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\nStyle: Narration,DejaVu Sans,46,&H00F4ECD8,&H000000FF,&H00100D12,&H90000000,0,0,0,0,100,100,0,0,3,2,0,2,160,160,64,1\n\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\nDialogue: 0,0:00:00.00,{_ass_time(dur)},Narration,,0,0,0,,{_ass_escape(text)}\n'''
    path.write_text(content, encoding='utf-8')


def render_ken_burns(still: Path, audio: Path, subtitle: str, out: Path, move: str = 'zoom_in') -> None:
    dur = duration(audio)
    frames = max(1, int(math.ceil(dur * FPS)))
    work = Path(tempfile.mkdtemp(prefix='spellcraft_scene_'))
    ass = work / 'sub.ass'
    write_ass(subtitle, dur, ass)
    assf = str(ass).replace('\\', '/').replace(':', '\\:').replace("'", "\\'")
    if move == 'zoom_out':
        z = "if(eq(on,0),1.12,max(1.0,zoom-0.0008))"
        x = 'iw/2-(iw/zoom/2)'
        y = 'ih/2-(ih/zoom/2)'
    elif move == 'pan_left':
        z = '1.08'
        x = f"(iw-iw/zoom)*(1-on/{frames})"
        y = 'ih/2-(ih/zoom/2)'
    elif move == 'pan_right':
        z = '1.08'
        x = f"(iw-iw/zoom)*(on/{frames})"
        y = 'ih/2-(ih/zoom/2)'
    else:
        z = 'min(zoom+0.0008,1.12)'
        x = 'iw/2-(iw/zoom/2)'
        y = 'ih/2-(ih/zoom/2)'
    vf = f"zoompan=z='{z}':x='{x}':y='{y}':d=1:s={W}x{H}:fps={FPS},ass='{assf}',format=yuv420p"
    run('ffmpeg', '-y', '-v', 'error', '-loop', '1', '-i', str(still), '-i', str(audio), '-vf', vf, '-t', f'{dur:.3f}', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20', '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', str(out))


def render_tentpole(still: Path, audio: Path, subtitle: str, out: Path, kind: str, seed: int = 0) -> None:
    dur = duration(audio)
    work = Path(tempfile.mkdtemp(prefix='spellcraft_tentpole_'))
    ass = work / 'sub.ass'
    write_ass(subtitle, dur, ass)
    assf = str(ass).replace('\\', '/').replace(':', '\\:').replace("'", "\\'")
    base = Image.open(still).convert('RGB')
    cmd = ['ffmpeg', '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-', '-i', str(audio), '-vf', f"ass='{assf}'", '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart', str(out)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    total = max(1, int(math.ceil(dur * FPS)))
    for i in range(total):
        t = i / FPS
        frame = base.copy().convert('RGBA')
        zoom = 1.0 + 0.025 * (i / max(1, total-1))
        zw, zh = int(W*zoom), int(H*zoom)
        tmp = frame.convert('RGB').resize((zw, zh), Image.Resampling.BICUBIC)
        frame = tmp.crop(((zw-W)//2, (zh-H)//2, (zw-W)//2+W, (zh-H)//2+H)).convert('RGBA')
        d = ImageDraw.Draw(frame, 'RGBA')
        if kind in ('flame', 'layout', 'kit', 'altar', 'prosperity', 'safety'):
            for j, (x, y) in enumerate(((420, 320), (960, 210), (1480, 380))):
                r = 16 + int(7 * math.sin(t*4.2+j))
                a = 55 + int(25 * (0.5 + 0.5 * math.sin(t*3.3+j)))
                d.ellipse((x-r, y-r, x+r, y+r), fill=(255, 175, 61, a))
        if kind in ('herb', 'flame', 'petition'):
            for j in range(3):
                x = 800 + j*150 + int(35*math.sin(t*.8+j))
                y = 690 - int((t*42+j*55) % 280)
                d.arc((x-80, y-140, x+80, y+140), 200, 340, fill=(220, 220, 225, 45), width=7)
        if kind in ('celestial', 'dream'):
            for j in range(18):
                x = (j*157 + seed*31) % W
                y = (j*89 + int(t*18*(j%3+1))) % 700
                a = 60 + int(50 * (0.5 + 0.5 * math.sin(t*2+j)))
                d.ellipse((x, y, x+3, y+3), fill=(235, 224, 174, a))
        proc.stdin.write(frame.convert('RGB').tobytes())
    proc.stdin.close()
    rc = proc.wait()
    if rc != 0:
        raise subprocess.CalledProcessError(rc, cmd)


MOVES = ['zoom_in', 'pan_left', 'zoom_out', 'pan_right']
