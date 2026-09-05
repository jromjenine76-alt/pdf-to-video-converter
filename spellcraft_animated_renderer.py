"""Animated Spellcraft walkthrough renderer.

This module is deliberately separate from the legacy page-frame renderer.  The PDF
is treated as a content/asset source, never as the screen layout.  Each narration
unit becomes several timed visual beats with camera movement, object animation,
short callouts, and optional clean crops from the manual.

The renderer is designed for GitHub Actions / Google Colab and only relies on
PyMuPDF, Pillow and FFmpeg, which are already used by this repository.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import random
import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

import pymupdf as fitz
from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageFont

W, H = 1920, 1080
FPS = 24
SAFE_X = 105
SAFE_Y = 70
BG = (8, 10, 28)
GOLD = (212, 174, 86)
CREAM = (244, 235, 214)
MUTED = (183, 174, 162)
PURPLE = (92, 59, 142)

FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSerif.ttf",
]
SANS_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
]


def ffmpeg(*args: str) -> None:
    subprocess.run(["ffmpeg", "-y", "-v", "error", *args], check=True)


def ffprobe_duration(path: Path) -> float:
    return float(subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(path)
    ], text=True).strip())


def font(size: int, serif: bool = False, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = FONT_CANDIDATES if serif else SANS_CANDIDATES
    if bold:
        candidates = [p.replace(".ttf", "-Bold.ttf") for p in candidates] + candidates
    for p in candidates:
        if Path(p).exists():
            return ImageFont.truetype(p, size=size)
    return ImageFont.load_default()


def ease(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)


def fit_cover(im: Image.Image, size=(W, H)) -> Image.Image:
    tw, th = size
    scale = max(tw / im.width, th / im.height)
    nw, nh = int(im.width * scale), int(im.height * scale)
    im = im.resize((nw, nh), Image.Resampling.LANCZOS)
    x = (nw - tw) // 2
    y = (nh - th) // 2
    return im.crop((x, y, x + tw, y + th))


def vignette(im: Image.Image) -> Image.Image:
    mask = Image.new("L", im.size, 0)
    d = ImageDraw.Draw(mask)
    for i in range(20):
        a = int(255 * (i + 1) / 20)
        inset = int(i * min(im.size) * 0.015)
        d.rounded_rectangle((inset, inset, im.width-inset, im.height-inset), radius=80, outline=a, width=18)
    mask = mask.filter(ImageFilter.GaussianBlur(70))
    dark = Image.new("RGB", im.size, (0, 0, 0))
    return Image.composite(im, dark, mask.point(lambda p: int(p * 0.28)))


def atmospheric_background(seed: int = 0) -> Image.Image:
    rnd = random.Random(seed)
    im = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(im, "RGBA")
    # soft nebula glows
    for _ in range(10):
        x = rnd.randint(-200, W+200)
        y = rnd.randint(-100, H+100)
        r = rnd.randint(180, 470)
        color = rnd.choice([(87,48,130,26), (18,78,92,22), (160,105,36,18)])
        glow = Image.new("RGBA", (W, H), (0,0,0,0))
        gd = ImageDraw.Draw(glow)
        gd.ellipse((x-r, y-r, x+r, y+r), fill=color)
        glow = glow.filter(ImageFilter.GaussianBlur(r//2))
        im = Image.alpha_composite(im.convert("RGBA"), glow).convert("RGB")
    draw = ImageDraw.Draw(im, "RGBA")
    for _ in range(170):
        x, y = rnd.randrange(W), rnd.randrange(H)
        r = rnd.choice([1,1,1,2])
        a = rnd.randint(55, 145)
        draw.ellipse((x-r,y-r,x+r,y+r), fill=(238,223,170,a))
    # fine gold frame
    draw.rounded_rectangle((34,34,W-34,H-34), radius=18, outline=GOLD+(135,), width=2)
    draw.rounded_rectangle((48,48,W-48,H-48), radius=18, outline=GOLD+(55,), width=1)
    return im


def wrap_text(draw: ImageDraw.ImageDraw, text: str, fnt, width_px: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    cur: list[str] = []
    for word in words:
        test = " ".join(cur + [word])
        if draw.textbbox((0,0), test, font=fnt)[2] <= width_px:
            cur.append(word)
        else:
            if cur:
                lines.append(" ".join(cur))
            cur = [word]
    if cur:
        lines.append(" ".join(cur))
    return lines


def draw_title_card(base: Image.Image, heading: str, kicker: str = "THE COMPLETE MANIFESTATION & SPELLCRAFT MANUAL") -> Image.Image:
    im = base.copy()
    d = ImageDraw.Draw(im, "RGBA")
    d.text((SAFE_X, SAFE_Y+8), kicker.upper(), font=font(25, False, True), fill=GOLD+(220,))
    d.line((SAFE_X, SAFE_Y+50, SAFE_X+470, SAFE_Y+50), fill=GOLD+(120,), width=2)
    f = font(78, serif=True, bold=True)
    lines = wrap_text(d, heading, f, 1120)
    y = 170
    for line in lines[:3]:
        d.text((SAFE_X, y), line, font=f, fill=CREAM+(255,))
        y += 92
    return im


def draw_candle(im: Image.Image, x: int, y: int, color: tuple[int,int,int], flame_phase: float, label: str | None = None, scale: float = 1.0) -> None:
    d = ImageDraw.Draw(im, "RGBA")
    bw = int(62*scale); bh = int(260*scale)
    # glow
    glow = Image.new("RGBA", im.size, (0,0,0,0))
    gd = ImageDraw.Draw(glow)
    gr = int(110*scale)
    gd.ellipse((x-gr, y-bh-gr//2, x+gr, y-bh+gr*2), fill=(255,183,67,55))
    glow = glow.filter(ImageFilter.GaussianBlur(int(45*scale)))
    im.alpha_composite(glow) if im.mode == "RGBA" else None
    d.rounded_rectangle((x-bw//2, y-bh, x+bw//2, y), radius=max(8,int(14*scale)), fill=color+(255,), outline=(255,255,255,38), width=2)
    wick_y = y-bh
    d.line((x, wick_y, x, wick_y-int(26*scale)), fill=(45,31,24,255), width=max(2,int(4*scale)))
    flick = math.sin(flame_phase*math.tau)*7*scale
    fh = int((70 + 8*math.sin(flame_phase*math.tau*1.7))*scale)
    fw = int(26*scale)
    pts = [(x, wick_y-int(25*scale)-fh), (x-fw+flick, wick_y-int(22*scale)), (x, wick_y+int(6*scale)), (x+fw+flick, wick_y-int(22*scale))]
    d.polygon(pts, fill=(255,179,43,235))
    inner = [(x, wick_y-int(18*scale)-fh*0.55), (x-int(10*scale), wick_y-int(18*scale)), (x, wick_y+int(1*scale)), (x+int(10*scale), wick_y-int(18*scale))]
    d.polygon(inner, fill=(255,245,174,245))
    if label:
        f = font(int(28*scale), False, True)
        bbox = d.textbbox((0,0), label, font=f)
        d.text((x-(bbox[2]-bbox[0])/2, y+18), label, font=f, fill=CREAM+(230,))


def draw_petition(im: Image.Image, center: tuple[int,int], progress: float, text: str = "PETITION") -> None:
    x,y = center
    d = ImageDraw.Draw(im, "RGBA")
    w,h = 440,255
    # float into place
    y2 = int(y + (1-ease(progress))*80)
    shadow = (x-w//2+16,y2-h//2+18,x+w//2+16,y2+h//2+18)
    d.rounded_rectangle(shadow, radius=18, fill=(0,0,0,95))
    d.rounded_rectangle((x-w//2,y2-h//2,x+w//2,y2+h//2), radius=16, fill=(219,196,151,248), outline=GOLD+(170,), width=3)
    for off in (-70,-20,30,80):
        d.line((x-w//2+45,y2+off,x+w//2-45,y2+off), fill=(102,79,52,80), width=2)
    f=font(36, serif=True, bold=True)
    bb=d.textbbox((0,0),text,font=f)
    d.text((x-(bb[2]-bb[0])/2,y2-22),text,font=f,fill=(72,54,39,220))


def draw_arrow(im: Image.Image, a: tuple[int,int], b: tuple[int,int], progress: float, label: str | None = None) -> None:
    d = ImageDraw.Draw(im, "RGBA")
    p=ease(progress)
    bx=int(a[0]+(b[0]-a[0])*p); by=int(a[1]+(b[1]-a[1])*p)
    d.line((a[0],a[1],bx,by), fill=GOLD+(230,), width=5)
    if p>0.92:
        ang=math.atan2(by-a[1], bx-a[0])
        r=18
        pts=[(bx,by),(bx-r*math.cos(ang-.55),by-r*math.sin(ang-.55)),(bx-r*math.cos(ang+.55),by-r*math.sin(ang+.55))]
        d.polygon(pts, fill=GOLD+(230,))
    if label and p>0.55:
        f=font(25,False,True)
        d.text(((a[0]+b[0])//2+12,(a[1]+b[1])//2-38),label,font=f,fill=CREAM+(235,))


def add_callout(im: Image.Image, text: str, x: int, y: int, alpha: int = 255, maxw: int = 550) -> None:
    d=ImageDraw.Draw(im,"RGBA")
    f=font(31,False,True)
    lines=wrap_text(d,text,f,maxw-50)[:3]
    lh=42; h=35+lh*len(lines)+20
    d.rounded_rectangle((x,y,x+maxw,y+h),radius=18,fill=(10,12,31,min(alpha,205)),outline=GOLD+(min(alpha,150),),width=2)
    yy=y+22
    for line in lines:
        d.text((x+26,yy),line,font=f,fill=CREAM+(alpha,))
        yy+=lh


def detect_scene_type(text: str) -> str:
    t=text.lower()
    if any(k in t for k in ("wyspell", "soul sticks", "lo scarabeo", "kit contains", "kit includes")):
        return "kit"
    if any(k in t for k in ("triangle", "layout", "arrange", "flanking", "cardinal", "pentagram", "hexagram", "ring of fire")):
        return "layout"
    if any(k in t for k in ("flame", "wax", "ceromancy", "pyromancy", "smoke")):
        return "flame"
    if any(k in t for k in ("herb", "sage", "mugwort", "palo santo", "lavender", "rosemary")):
        return "herb"
    if any(k in t for k in ("petition", "scribe", "quill", "seal", "sealing wax")):
        return "petition"
    return "story"


@dataclass
class Unit:
    episode: int
    unit: int
    text: str
    audio: Path
    heading: str = ""
    source_pages: tuple[int, ...] = ()
    asset: Path | None = None


class CleanAssetExtractor:
    """Extract standalone PDF image objects only when page text does not overlap them."""
    def __init__(self, pdf: Path, out_dir: Path):
        self.pdf=pdf; self.out_dir=out_dir
        out_dir.mkdir(parents=True,exist_ok=True)

    def extract_page_images(self, page_number: int) -> list[Path]:
        out=[]
        with fitz.open(self.pdf) as doc:
            page=doc[page_number-1]
            text_blocks=[]
            for b in page.get_text("dict").get("blocks",[]):
                if b.get("type")==0:
                    text_blocks.append(fitz.Rect(b["bbox"]))
            for idx,info in enumerate(page.get_image_info(xrefs=True)):
                xref=info.get("xref") or 0
                bbox=fitz.Rect(info.get("bbox"))
                if xref<=0 or bbox.width<80 or bbox.height<80:
                    continue
                contaminated=any(bbox.intersects(tb) and (bbox & tb).get_area()>0.015*bbox.get_area() for tb in text_blocks)
                if contaminated:
                    continue
                try:
                    raw=doc.extract_image(xref)
                except Exception:
                    continue
                ext=raw.get("ext","png")
                p=self.out_dir/f"p{page_number:03d}_{idx:02d}.{ext}"
                p.write_bytes(raw["image"])
                out.append(p)
        return out


def render_unit(unit: Unit, out_path: Path, *, seed: int = 0) -> None:
    duration=ffprobe_duration(unit.audio)
    scene_type=detect_scene_type(unit.text)
    work=Path(tempfile.mkdtemp(prefix="spellcraft_motion_"))
    frames=work/"frames"; frames.mkdir()
    n=max(1,int(math.ceil(duration*FPS)))
    bg=atmospheric_background(seed+unit.episode*1000+unit.unit)
    # optional asset pre-processing
    asset=None
    if unit.asset and unit.asset.exists():
        try:
            asset=Image.open(unit.asset).convert("RGBA")
        except Exception:
            asset=None

    sentences=[s.strip() for s in re.split(r"(?<=[.!?])\s+",unit.text) if s.strip()]
    beat_count=max(3,min(8,len(sentences)))
    for i in range(n):
        t=i/max(1,n-1)
        local=(t*beat_count)%1.0
        beat=min(beat_count-1,int(t*beat_count))
        # subtle drifting background camera
        frame=bg.copy().convert("RGBA")
        drift_x=int(10*math.sin(t*math.tau*0.35)); drift_y=int(6*math.cos(t*math.tau*0.28))
        frame=ImageChops.offset(frame,drift_x,drift_y)
        frame=draw_title_card(frame, unit.heading or f"Spellcraft Walkthrough · Episode {unit.episode}")
        d=ImageDraw.Draw(frame,"RGBA")

        if scene_type=="layout":
            # petition settles into center; candles animate into positions one-by-one
            draw_petition(frame,(W//2,620),min(1,t*4))
            positions=[(960,280),(620,760),(1300,760)]
            cols=[(245,245,232),(231,116,35),(221,190,46)]
            labels=["FOCUS","MOMENTUM","CLARITY"]
            for j,(pos,col,lab) in enumerate(zip(positions,cols,labels)):
                start=j*0.12+0.1
                p=max(0,min(1,(t-start)/0.22))
                x=int(W//2+(pos[0]-W//2)*ease(p)); y=int(980+(pos[1]-980)*ease(p))
                if p>0:
                    draw_candle(frame,x,y,col,t*3+j*.17,lab,0.88)
            if t>.55:
                draw_arrow(frame,(960,600),(960,340),min(1,(t-.55)/.15),"LIGHTING ORDER")
        elif scene_type=="flame":
            xs=[520,960,1400]; labs=["STEADY","HIGH","FLICKER"]
            for j,x in enumerate(xs):
                scale=[.92,1.15,.9][j]
                draw_candle(frame,x,835,(235,221,190),t*(2+j*.4),labs[j],scale)
            if beat>=1:
                add_callout(frame,"Read movement, smoke, and wax as observations, not proof.",105,700,int(255*min(1,local*3)),560)
        elif scene_type=="petition":
            draw_petition(frame,(960,610),min(1,t*3),"INTENTION")
            # animated quill stroke
            p=min(1,max(0,(t-.2)/.55))
            x1,y1=760,575; x2,y2=1150,655
            d.line((x1,y1,int(x1+(x2-x1)*p),int(y1+(y2-y1)*p)),fill=(78,53,34,220),width=5)
            if t>.62:
                sealx,sealy=1180,720
                r=int(48*ease(min(1,(t-.62)/.18)))
                d.ellipse((sealx-r,sealy-r,sealx+r,sealy+r),fill=(124,31,39,235),outline=GOLD+(180,),width=3)
        elif scene_type=="kit":
            # use isolated source visual if available; otherwise animated object tray
            if asset:
                # slow camera push, never show whole PDF page
                a=asset.copy()
                target_w=int(760*(1+0.10*ease(t)))
                ratio=target_w/a.width
                a=a.resize((target_w,int(a.height*ratio)),Image.Resampling.LANCZOS)
                frame.alpha_composite(a,(W-880,215))
            # kit components arrive as labeled tokens
            items=[("CANDLES",(590,500),PURPLE),("PARCHMENT",(570,670),(151,111,66)),("HOLDERS",(980,770),(45,45,52)),("GUIDE",(1260,560),(81,94,123))]
            for j,(lab,(x,y),col) in enumerate(items):
                p=max(0,min(1,(t-.08*j)/.25))
                if not p: continue
                yy=int(y+(1-ease(p))*80)
                d.rounded_rectangle((x-120,yy-46,x+120,yy+46),radius=22,fill=col+(205,),outline=GOLD+(120,),width=2)
                f=font(24,False,True); bb=d.textbbox((0,0),lab,font=f)
                d.text((x-(bb[2]-bb[0])/2,yy-14),lab,font=f,fill=CREAM+(245,))
        elif scene_type=="herb":
            # animated botanical sprigs and ingredient bowls, stylized without unsafe page crops
            centers=[(520,660),(960,570),(1400,670)]
            names=["SAGE","MUGWORT","PALO SANTO"]
            cols=[(97,136,82),(84,118,71),(151,105,65)]
            for j,((x,y),name,col) in enumerate(zip(centers,names,cols)):
                p=max(0,min(1,(t-j*.12)/.30))
                r=int(95*ease(p))
                d.ellipse((x-r,y-r,x+r,y+r),fill=(35,29,22,220),outline=GOLD+(150,),width=3)
                for k in range(9):
                    ang=(k/9)*math.tau+t*.18
                    ex=x+int(math.cos(ang)*r*.7); ey=y+int(math.sin(ang)*r*.7)
                    d.ellipse((ex-20,ey-8,ex+20,ey+8),fill=col+(235,))
                f=font(27,False,True); bb=d.textbbox((0,0),name,font=f)
                d.text((x-(bb[2]-bb[0])/2,y+r+25),name,font=f,fill=CREAM+(235,))
        else:
            # documentary rhythm: large moving visual field, 3 callout beats, optional isolated asset
            if asset:
                a=asset.copy(); maxw=850
                sc=min(maxw/a.width,640/a.height)
                a=a.resize((int(a.width*sc),int(a.height*sc)),Image.Resampling.LANCZOS)
                x=int(1010+30*math.sin(t*math.pi)); y=245
                frame.alpha_composite(a,(x,y))
            # callout changes by narration beat instead of leaving a static paragraph onscreen
            if sentences:
                s=sentences[min(len(sentences)-1,beat)]
                short=re.sub(r"\s+"," ",s)
                if len(short)>130: short=short[:127].rsplit(" ",1)[0]+"…"
                add_callout(frame,short,105,680,235,720)

        # progress ribbon + source range, always inside safe area
        fsmall=font(22,False,True)
        footer=f"EPISODE {unit.episode}  ·  UNIT {unit.unit}"
        if unit.source_pages:
            footer += "  ·  SOURCE PAGES " + ", ".join(map(str,unit.source_pages))
        d.text((SAFE_X,H-94),footer,font=fsmall,fill=MUTED+(210,))
        d.line((SAFE_X,H-122,W-SAFE_X,H-122),fill=GOLD+(80,),width=2)
        d.line((SAFE_X,H-122,SAFE_X+(W-2*SAFE_X)*t,H-122),fill=GOLD+(225,),width=4)
        frame.convert("RGB").save(frames/f"f_{i:06d}.jpg",quality=91,subsampling=0)

    video_only=work/"visual.mp4"
    ffmpeg("-framerate",str(FPS),"-i",str(frames/"f_%06d.jpg"),"-c:v","libx264","-pix_fmt","yuv420p","-crf","20","-preset","veryfast",str(video_only))
    ffmpeg("-i",str(video_only),"-i",str(unit.audio),"-c:v","copy","-c:a","aac","-b:a","192k","-shortest","-movflags","+faststart",str(out_path))


def load_units(manifest: Path, audio_dir: Path, episode: int) -> list[Unit]:
    data=json.loads(manifest.read_text(encoding="utf-8"))
    rows=data.get("units",data if isinstance(data,list) else [])
    out=[]
    for row in rows:
        ep=int(row.get("episode",episode))
        if ep!=episode: continue
        uid=int(row.get("unit",row.get("id",len(out)+1)))
        text=str(row.get("text",row.get("narration",""))).strip()
        if not text: continue
        heading=str(row.get("heading",row.get("title",f"Episode {episode}")))
        pages=row.get("source_pages",row.get("pages",[])) or []
        if isinstance(pages,int): pages=[pages]
        audio_name=row.get("audio") or f"unit_{uid:02d}.wav"
        audio=audio_dir/audio_name
        if not audio.exists():
            # also accept mp3/m4a
            matches=list(audio_dir.glob(f"*{uid:02d}*.*"))
            matches=[p for p in matches if p.suffix.lower() in {".wav",".mp3",".m4a",".aac"}]
            if matches: audio=matches[0]
        if not audio.exists():
            raise FileNotFoundError(f"Missing narration audio for unit {uid}: {audio}")
        asset_path=row.get("asset")
        out.append(Unit(ep,uid,text,audio,heading,tuple(map(int,pages)),Path(asset_path) if asset_path else None))
    return out


def concat_segments(segments: Sequence[Path], output: Path) -> None:
    listfile=output.with_suffix(".concat.txt")
    listfile.write_text("".join(f"file '{p.resolve().as_posix()}'\n" for p in segments),encoding="utf-8")
    ffmpeg("-f","concat","-safe","0","-i",str(listfile),"-c","copy","-movflags","+faststart",str(output))


def main() -> None:
    ap=argparse.ArgumentParser()
    ap.add_argument("--manifest",type=Path,required=True)
    ap.add_argument("--audio-dir",type=Path,required=True)
    ap.add_argument("--episode",type=int,required=True)
    ap.add_argument("--output",type=Path,required=True)
    ap.add_argument("--start-unit",type=int,default=1)
    ap.add_argument("--end-unit",type=int,default=999)
    args=ap.parse_args()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    units=[u for u in load_units(args.manifest,args.audio_dir,args.episode) if args.start_unit<=u.unit<=args.end_unit]
    if not units:
        raise SystemExit("No matching units found")
    segdir=args.output.parent/f"ep{args.episode:02d}_segments"; segdir.mkdir(exist_ok=True)
    segs=[]
    for idx,u in enumerate(units,1):
        out=segdir/f"unit_{u.unit:03d}.mp4"
        print(f"[{idx}/{len(units)}] Rendering episode {u.episode} unit {u.unit}: {detect_scene_type(u.text)}",flush=True)
        render_unit(u,out,seed=20260905)
        segs.append(out)
    concat_segments(segs,args.output)
    print(json.dumps({"episode":args.episode,"units":len(units),"output":str(args.output),"duration":ffprobe_duration(args.output)},indent=2))


if __name__ == "__main__":
    main()
