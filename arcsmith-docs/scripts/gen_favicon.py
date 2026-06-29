"""Generate the ArcSmith favicon, inspired by the social card.

Design: a slate rounded tile, a white IBM Plex Sans Bold "A", and a short orange
tick beneath it (echoing the card's kicker dash). Outputs:

  docs/stylesheets/arcsmith-icon.svg     vector (font outline embedded, crisp at
                                          any size incl. bookmark/PWA tiles)
  docs/assets/images/favicon.png         512x512 raster fallback / large tile
  docs/assets/images/apple-touch-icon.png 180x180 (iOS home screen)
  docs/assets/images/favicon.ico         16/32/48 multi-size legacy icon

Run from anywhere:  python arcsmith-docs/scripts/gen_favicon.py
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.boundsPen import BoundsPen

ROOT = Path(__file__).resolve().parents[1]
FONT = ROOT / "scripts" / "fonts" / "IBMPlexSans-Bold.ttf"
SVG_OUT = ROOT / "docs" / "stylesheets" / "arcsmith-icon.svg"
IMG_DIR = ROOT / "docs" / "assets" / "images"

SLATE = (38, 50, 68)        # #263244
WHITE = (223, 229, 241)
ORANGE = (232, 120, 48)     # #E87830

# Geometry as fractions of the icon size (so every resolution matches).
RADIUS_F = 0.21             # rounded-tile corner radius
A_HEIGHT_F = 0.44           # cap height of the "A"
A_CENTER_F = 0.43           # vertical center of the "A"
TICK_W_F, TICK_H_F = 0.30, 0.055
TICK_CY_F = 0.71


def _hex(rgb):
    return "#%02X%02X%02X" % rgb


# ---- SVG (font outline) ------------------------------------------------
def build_svg(S=512):
    font = TTFont(str(FONT))
    upm = font["head"].unitsPerEm
    glyphs = font.getGlyphSet()
    name = font.getBestCmap()[ord("A")]

    pen = SVGPathPen(glyphs)
    glyphs[name].draw(pen)
    d = pen.getCommands()

    bp = BoundsPen(glyphs)
    glyphs[name].draw(bp)
    gx0, gy0, gx1, gy1 = bp.bounds
    gh = gy1 - gy0

    a = (A_HEIGHT_F * S) / gh                       # scale font units -> px
    e = S / 2 - a * (gx0 + (gx1 - gx0) / 2)         # center horizontally
    f = A_CENTER_F * S + a * (gy1 + gy0) / 2        # center vertically (Y flip)

    r = RADIUS_F * S
    tw, th, cy = TICK_W_F * S, TICK_H_F * S, TICK_CY_F * S
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {S} {S}">
  <rect width="{S}" height="{S}" rx="{r:.1f}" fill="{_hex(SLATE)}"/>
  <path transform="translate({e:.2f} {f:.2f}) scale({a:.5f} {-a:.5f})" d="{d}" fill="{_hex(WHITE)}"/>
  <rect x="{S/2 - tw/2:.1f}" y="{cy - th/2:.1f}" width="{tw:.1f}" height="{th:.1f}" rx="{th/2:.1f}" fill="{_hex(ORANGE)}"/>
</svg>
"""


# ---- Raster ------------------------------------------------------------
def render_png(S):
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, S - 1, S - 1], radius=round(RADIUS_F * S), fill=SLATE + (255,))

    target = A_HEIGHT_F * S
    fs = int(S * 0.6)
    f = ImageFont.truetype(str(FONT), fs)
    bb = d.textbbox((0, 0), "A", font=f)
    fs = max(1, int(fs * target / (bb[3] - bb[1])))     # adjust to exact cap height
    f = ImageFont.truetype(str(FONT), fs)
    bb = d.textbbox((0, 0), "A", font=f)
    w, h = bb[2] - bb[0], bb[3] - bb[1]
    d.text((S / 2 - w / 2 - bb[0], A_CENTER_F * S - h / 2 - bb[1]), "A", font=f, fill=WHITE + (255,))

    tw, th, cy = TICK_W_F * S, TICK_H_F * S, TICK_CY_F * S
    d.rounded_rectangle([S/2 - tw/2, cy - th/2, S/2 + tw/2, cy + th/2], radius=th/2, fill=ORANGE + (255,))
    return img


IMG_DIR.mkdir(parents=True, exist_ok=True)
SVG_OUT.write_text(build_svg(), encoding="utf-8")
master = render_png(512)
master.save(IMG_DIR / "favicon.png")
render_png(180).save(IMG_DIR / "apple-touch-icon.png")
master.save(IMG_DIR / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48)])
print("wrote", SVG_OUT.name, "favicon.png apple-touch-icon.png favicon.ico")
