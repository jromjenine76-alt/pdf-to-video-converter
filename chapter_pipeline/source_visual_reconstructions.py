from __future__ import annotations

import math
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1600, 900
GOLD = (210, 170, 82)
IVORY = (239, 229, 207)


def _font(size: int, bold: bool = False):
    candidates = [
        '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf' if bold else '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
        '/usr/share/fonts/truetype/freefont/FreeSansBold.ttf' if bold else '/usr/share/fonts/truetype/freefont/FreeSans.ttf',
    ]
    for p in candidates:
        if Path(p).exists():
            return ImageFont.truetype(p, size=size)
    return ImageFont.load_default()


def _base(title: str, subtitle: str = '') -> Image.Image:
    im = Image.new('RGB', (W, H), (7, 10, 19)).convert('RGBA')
    d = ImageDraw.Draw(im, 'RGBA')
    for y in range(H):
        u = y / max(1, H - 1)
        c = (8 + int(18*u), 11 + int(10*u), 23 + int(12*u), 255)
        d.line((0, y, W, y), fill=c)
    glow = Image.new('RGBA', im.size, (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow, 'RGBA')
    gd.ellipse((1000, -220, 1700, 500), fill=(93, 53, 142, 82))
    gd.ellipse((-260, 540, 560, 1180), fill=(164, 99, 39, 60))
    glow = glow.filter(ImageFilter.GaussianBlur(130))
    im = Image.alpha_composite(im, glow)
    d = ImageDraw.Draw(im, 'RGBA')
    d.rounded_rectangle((54, 52, 1546, 848), radius=34, outline=GOLD+(115,), width=2)
    d.text((90, 74), title, font=_font(42, True), fill=IVORY+(248,))
    if subtitle:
        d.text((92, 128), subtitle, font=_font(20), fill=(194, 179, 154, 220))
    return im


def _label(d: ImageDraw.ImageDraw, xy: tuple[int, int], text: str) -> None:
    x, y = xy
    font = _font(18, True)
    box = d.textbbox((0, 0), text, font=font)
    w = box[2] - box[0]
    h = box[3] - box[1]
    d.rounded_rectangle((x-10, y-7, x+w+10, y+h+9), radius=9, fill=(5, 8, 14, 178), outline=GOLD+(80,), width=1)
    d.text((x, y), text, font=font, fill=IVORY+(235,))


def _candle(d: ImageDraw.ImageDraw, x: int, y: int, color: tuple[int, int, int], h: int = 250, w: int = 58, lit: bool = True) -> None:
    d.rounded_rectangle((x-w//2, y-h, x+w//2, y), radius=12, fill=color+(255,), outline=(255,255,255,55), width=2)
    d.line((x, y-h, x, y-h-16), fill=(48, 35, 25, 255), width=3)
    if lit:
        d.ellipse((x-48, y-h-74, x+48, y-h+22), fill=(255, 148, 54, 34))
        d.polygon([(x, y-h-58), (x-17, y-h-10), (x, y-h+5), (x+17, y-h-10)], fill=(255, 177, 61, 248))
        d.polygon([(x, y-h-38), (x-7, y-h-7), (x, y-h+1), (x+7, y-h-7)], fill=(255, 247, 190, 255))


def _parchment(d: ImageDraw.ImageDraw, box=(560, 320, 1040, 650), seal=True) -> None:
    x1, y1, x2, y2 = box
    d.rounded_rectangle((x1+14, y1+18, x2+14, y2+18), radius=20, fill=(0,0,0,80))
    d.rounded_rectangle(box, radius=18, fill=(225, 204, 164, 245), outline=(129, 92, 54, 190), width=3)
    for yy in range(y1+68, y2-45, 46):
        d.line((x1+48, yy, x2-48, yy), fill=(102, 72, 44, 66), width=2)
    if seal:
        cx, cy = x2-72, y2-55
        d.ellipse((cx-38, cy-38, cx+38, cy+38), fill=(126, 30, 39, 250), outline=GOLD+(190,), width=3)
        d.ellipse((cx-18, cy-18, cx+18, cy+18), outline=(235, 188, 102, 150), width=2)


def _soul_sticks(out: Path) -> str:
    im = _base('Soul Sticks Gambling Manifesting Intention Kit', 'Reconstructed from the manual source visual without surrounding page text')
    d = ImageDraw.Draw(im, 'RGBA')
    # Sage + mugwort bundle
    cx, cy = 335, 610
    for i in range(15):
        a = -0.32 + i*0.045
        x2 = cx + int(250*math.cos(a))
        y2 = cy - int(250*math.sin(a)) - 180
        d.line((cx, cy, x2, y2), fill=(96+(i%3)*14, 126+(i%4)*8, 78, 235), width=10)
        d.ellipse((x2-24, y2-12, x2+24, y2+12), fill=(109, 139, 89, 220))
    d.rectangle((285, 575, 390, 625), fill=(142, 102, 56, 240))
    d.line((286, 589, 390, 609), fill=(231, 203, 147, 190), width=5)
    _label(d, (208, 700), 'SAGE + MUGWORT')
    # Oil bottle
    d.rounded_rectangle((620, 300, 820, 650), radius=30, fill=(56, 36, 24, 255), outline=(202, 164, 90, 180), width=4)
    d.rectangle((665, 238, 775, 320), fill=(42, 30, 24, 255))
    d.rounded_rectangle((640, 408, 800, 555), radius=10, fill=(229, 214, 170, 235), outline=(139, 105, 55, 180), width=2)
    d.text((665, 448), '10 mL', font=_font(28, True), fill=(66, 43, 25, 255))
    d.text((662, 492), 'HERBAL OIL', font=_font(19, True), fill=(66, 43, 25, 255))
    _label(d, (645, 700), 'GAMBLING HERBAL OIL')
    # Palo santo
    for off, rot in ((0,0),(45,-10),(88,8)):
        x = 990+off
        d.rounded_rectangle((x, 355+rot, x+68, 650+rot), radius=14, fill=(182, 128, 73, 255), outline=(235, 186, 119, 140), width=3)
        d.line((x+20, 390+rot, x+50, 610+rot), fill=(129, 83, 47, 115), width=4)
    _label(d, (972, 700), 'PALO SANTO')
    # Selenite wand
    pts = [(1295, 620),(1350,300),(1420,275),(1472,590),(1430,650),(1340,655)]
    d.polygon(pts, fill=(224, 231, 234, 228), outline=(255,255,255,190))
    d.line((1350,300,1430,650), fill=(167, 192, 204, 125), width=4)
    d.line((1400,286,1368,650), fill=(255,255,255,95), width=3)
    _label(d, (1285, 700), 'SELENITE WAND')
    im.convert('RGB').save(out, quality=94)
    return 'soul_sticks_kit'


def _wyspell_set(out: Path, chart: bool) -> str:
    title = 'Wyspell 36 Colored Spell Candle Set' if not chart else 'Wyspell Color Reference'
    subtitle = 'Reconstructed from the clean product/color source visual'
    im = _base(title, subtitle)
    d = ImageDraw.Draw(im, 'RGBA')
    colors = [
        ('WHITE',(235,231,217)), ('BLACK',(34,34,39)), ('RED',(186,47,48)), ('PINK',(223,124,150)),
        ('ORANGE',(224,113,44)), ('YELLOW',(230,191,52)), ('GREEN',(63,131,76)), ('BLUE',(59,97,178)),
        ('PURPLE',(108,69,145)), ('BROWN',(116,76,53)), ('GOLD',(203,154,45)), ('SILVER',(165,176,184)),
    ]
    start_x, start_y = 235, 330
    for i,(name,c) in enumerate(colors):
        row, col = divmod(i, 6)
        x = start_x + col*225
        y = start_y + row*300
        _candle(d, x, y+180, c, h=170, w=42, lit=False)
        _label(d, (x-46, y+205), name)
    if not chart:
        d.rounded_rectangle((1060, 188, 1470, 755), radius=24, outline=GOLD+(90,), width=2)
        for j in range(3):
            for i in range(4):
                n = j*4+i
                c = colors[n][1]
                x = 1130+i*82
                y = 320+j*125
                _candle(d, x, y+90, c, h=105, w=25, lit=False)
        d.text((1120, 235), '36-CANDLE SET', font=_font(28, True), fill=IVORY+(235,))
    im.convert('RGB').save(out, quality=94)
    return 'wyspell_color_chart' if chart else 'wyspell_kit'


def _lo_scarabeo(out: Path) -> str:
    im = _base('Lo Scarabeo Calligraphic Ritual Kit', 'Reconstructed from the manual source visual')
    d = ImageDraw.Draw(im, 'RGBA')
    _parchment(d, (490, 250, 1120, 700), seal=True)
    # quill
    d.polygon([(245,690),(330,180),(382,145),(346,344),(290,625)], fill=(226, 217, 193, 235), outline=(255,255,255,100))
    d.line((265,690,355,205), fill=(42,35,30,255), width=10)
    for yy in range(245, 520, 45):
        d.line((330,yy,278,yy+28), fill=(131,117,100,155), width=3)
    # ink pot
    d.rounded_rectangle((1185,445,1370,655), radius=34, fill=(28,31,40,255), outline=(142,150,175,170), width=4)
    d.rectangle((1220,385,1335,470), fill=(47,48,56,255))
    d.ellipse((1218,365,1338,415), fill=(34,35,42,255), outline=GOLD+(120,), width=2)
    # wax sticks + seal
    for x,c in ((1190,(120,25,36)),(1260,(57,84,132)),(1330,(112,70,32))):
        d.rounded_rectangle((x,690,x+44,810),radius=12,fill=c+(250,))
    d.ellipse((1065,720,1175,830),fill=(126,29,39,245),outline=GOLD+(190,),width=4)
    _label(d,(180,745),'QUILL')
    _label(d,(1200,330),'INK')
    _label(d,(1190,825),'WAX + SEAL')
    im.convert('RGB').save(out, quality=94)
    return 'lo_scarabeo_kit'


def _layout_title_and_kind(text: str):
    t = text.lower()
    if 'ring of fire' in t or 'containment circle' in t:
        return 'Ring of Fire / Containment Circle', 'ring'
    if 'starseed' in t or 'hexagram' in t:
        return 'Starseed Hexagram', 'hexagram'
    if 'pentagram' in t:
        return 'Pentagram Layout', 'pentagram'
    if 'square' in t or 'foundation' in t:
        return 'Square / Foundation Layout', 'square'
    if 'cross' in t or 'cardinal' in t:
        return 'Cross / Cardinal Alignment', 'cross'
    if 'triangle' in t:
        return 'Triangle / Apex Layout', 'triangle'
    if 'flanking pair' in t or 'two-candle' in t or 'pair' in t:
        return 'Flanking Pair', 'pair'
    if 'single-candle' in t or 'single candle focus' in t:
        return 'Single-Candle Focus', 'single'
    return None, None


def _layout(out: Path, title: str, kind: str) -> str:
    im = _base(title, 'Rebuilt as a clean teaching diagram from the manual layout')
    d = ImageDraw.Draw(im, 'RGBA')
    cx, cy = 800, 500
    r = 280
    points: list[tuple[int,int]] = []
    if kind == 'single':
        points = [(cx, cy)]
    elif kind == 'pair':
        points = [(cx-260, cy),(cx+260,cy)]
    elif kind == 'triangle':
        points = [(cx,cy-r),(cx-int(r*.87),cy+int(r*.5)),(cx+int(r*.87),cy+int(r*.5))]
        d.line(points+[points[0]],fill=GOLD+(170,),width=5)
    elif kind == 'cross':
        points = [(cx,cy-r),(cx,cy+r),(cx-r,cy),(cx+r,cy)]
        d.line((cx,cy-r,cx,cy+r),fill=GOLD+(160,),width=5)
        d.line((cx-r,cy,cx+r,cy),fill=GOLD+(160,),width=5)
    elif kind == 'square':
        points = [(cx-r,cy-r),(cx+r,cy-r),(cx+r,cy+r),(cx-r,cy+r)]
        d.line(points+[points[0]],fill=GOLD+(170,),width=5)
    elif kind == 'pentagram':
        base=[]
        for i in range(5):
            a=-math.pi/2+i*2*math.pi/5
            base.append((cx+int(r*math.cos(a)),cy+int(r*math.sin(a))))
        order=[0,2,4,1,3,0]
        d.line([base[i] for i in order],fill=GOLD+(175,),width=5)
        points=base
    elif kind == 'hexagram':
        p1=[(cx,cy-r),(cx-int(r*.87),cy+int(r*.5)),(cx+int(r*.87),cy+int(r*.5))]
        p2=[(cx,cy+r),(cx-int(r*.87),cy-int(r*.5)),(cx+int(r*.87),cy-int(r*.5))]
        d.line(p1+[p1[0]],fill=GOLD+(170,),width=5)
        d.line(p2+[p2[0]],fill=GOLD+(170,),width=5)
        points=p1+p2
    elif kind == 'ring':
        d.ellipse((cx-r,cy-r,cx+r,cy+r),outline=GOLD+(185,),width=6)
        points=[]
        for i in range(8):
            a=-math.pi/2+i*2*math.pi/8
            points.append((cx+int(r*math.cos(a)),cy+int(r*math.sin(a))))
    _parchment(d,(665,405,935,600),seal=True)
    palette=[(239,232,214),(207,71,56),(76,104,196),(103,64,145),(49,126,79),(225,169,53),(236,232,213),(172,73,57)]
    for i,(x,y) in enumerate(points):
        _candle(d,x,y+72,palette[i%len(palette)],h=120,w=34,lit=True)
    d.arc((cx-r-60,cy-r-60,cx+r+60,cy+r+60),start=205,end=330,fill=(222,190,112,150),width=4)
    d.polygon([(cx+r+48,cy+130),(cx+r+30,cy+94),(cx+r+72,cy+108)],fill=(222,190,112,190))
    im.convert('RGB').save(out,quality=94)
    return f'layout_{kind}'


def _selenite(out: Path) -> str:
    im=_base('Selenite Wand','Dry-use visual reconstruction from the manual guidance')
    d=ImageDraw.Draw(im,'RGBA')
    pts=[(625,710),(760,180),(930,160),(1080,680),(975,760),(720,760)]
    d.polygon(pts,fill=(224,232,237,238),outline=(255,255,255,190))
    d.line((760,180,975,760),fill=(166,190,205,130),width=6)
    d.line((850,170,760,760),fill=(255,255,255,105),width=4)
    d.line((925,165,890,755),fill=(184,205,214,120),width=5)
    _label(d,(700,790),'KEEP DRY')
    im.convert('RGB').save(out,quality=94)
    return 'selenite_wand'


def reconstruction_key(text: str) -> str | None:
    t = text.lower()
    title, kind = _layout_title_and_kind(text)
    if kind:
        return f'layout_{kind}'
    if 'soul sticks' in t or 'gambling manifesting intention kit' in t:
        return 'soul_sticks_kit'
    if 'lo scarabeo' in t or 'calligraphic ritual kit' in t:
        return 'lo_scarabeo_kit'
    if 'wyspell' in t and any(k in t for k in ('12 color','12 colors','color chart','colored spell candle','candle colors','color meanings')):
        return 'wyspell_color_chart'
    if 'wyspell' in t:
        return 'wyspell_kit'
    if 'selenite' in t:
        return 'selenite_wand'
    return None


def reconstruct_source_visual(text: str, output_dir: Path) -> tuple[Path | None, str | None]:
    key = reconstruction_key(text)
    if not key:
        return None, None
    output_dir.mkdir(parents=True, exist_ok=True)
    safe = re.sub(r'[^a-z0-9_]+','_',key.lower()).strip('_')
    out = output_dir / f'{safe}.jpg'
    if out.exists() and out.stat().st_size > 5000:
        return out, key
    if key == 'soul_sticks_kit':
        made = _soul_sticks(out)
    elif key == 'wyspell_kit':
        made = _wyspell_set(out, chart=False)
    elif key == 'wyspell_color_chart':
        made = _wyspell_set(out, chart=True)
    elif key == 'lo_scarabeo_kit':
        made = _lo_scarabeo(out)
    elif key == 'selenite_wand':
        made = _selenite(out)
    elif key.startswith('layout_'):
        title, kind = _layout_title_and_kind(text)
        if not title or not kind:
            return None, None
        made = _layout(out, title, kind)
    else:
        return None, None
    return out, made
