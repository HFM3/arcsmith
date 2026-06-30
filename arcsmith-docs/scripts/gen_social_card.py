"""Generate the arcsmith social card (1200x630) used for link previews.

The card mirrors the homepage hero in arcsmith-docs/index.html (.hero):

  bg        --slate #263244
  dot grid  white at 9%, centered so edge margins are even
  eyebrow   orange tick (--orange-lt #E87830) + muted gray uppercase mono text
  title     #E0E6F2 with "toolbox." in --orange-lt
  subtitle  muted blue-gray sans

Output goes to docs/images/social-card.png, which mkdocs publishes to
https://arcsmith.dev/docs/images/social-card.png (wired as og:image and
twitter:image in index.html and docs/overrides/main.html).

Run from anywhere:

    python arcsmith-docs/scripts/gen_social_card.py

Fonts are the site fonts (IBM Plex Mono / IBM Plex Sans, the same families the
homepage loads), vendored under scripts/fonts/ so the card matches the hero
exactly and renders identically on any machine. They are licensed under the
SIL Open Font License 1.1 (see scripts/fonts/OFL.txt).
"""
import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H = 1200, 630
SLATE = (38, 50, 68)          # #263244
TITLE = (223, 229, 241)       # ~ rgba(224,230,242,0.97)
ORANGE_LT = (232, 120, 48)    # #E87830
EYEBROW_GRAY = (208, 216, 230)
SUB_GRAY = (138, 147, 161)

FONTS = Path(__file__).resolve().parent / "fonts"
mono_semibold = lambda s: ImageFont.truetype(str(FONTS / "IBMPlexMono-SemiBold.ttf"), s)
mono_bold = lambda s: ImageFont.truetype(str(FONTS / "IBMPlexMono-Bold.ttf"), s)
sans = lambda s: ImageFont.truetype(str(FONTS / "IBMPlexSans-Regular.ttf"), s)
sans_semibold = lambda s: ImageFont.truetype(str(FONTS / "IBMPlexSans-SemiBold.ttf"), s)
sans_bold = lambda s: ImageFont.truetype(str(FONTS / "IBMPlexSans-Bold.ttf"), s)

img = Image.new("RGB", (W, H), SLATE)
draw = ImageDraw.Draw(img)

# --- dot grid -----------------------------------------------------------
dots = Image.new("RGBA", (W, H), (0, 0, 0, 0))
ddraw = ImageDraw.Draw(dots)
step, r, alpha = 38, 1.7, int(0.09 * 255)
# Center the grid so left/right and top/bottom margins are equal (no dots
# crowding the edges).
n_cols = int(W / step)
n_rows = int(H / step)
start_x = (W - (n_cols - 1) * step) / 2
start_y = (H - (n_rows - 1) * step) / 2
for j in range(n_rows):
    for i in range(n_cols):
        x = start_x + i * step
        y = start_y + j * step
        ddraw.ellipse([x - r, y - r, x + r, y + r], fill=(255, 255, 255, alpha))
img = Image.alpha_composite(img.convert("RGBA"), dots).convert("RGB")
draw = ImageDraw.Draw(img)

LEFT = 96

# --- eyebrow: orange tick + spaced uppercase text -----------------------
eb_font = sans_semibold(52)  # "Arc" + tick cap-height reference
eb_bold = sans_bold(52)      # "Smith"
eb_text = "ArcSmith"
eb_y = 70  # lands the kicker rule exactly on the dot-grid row at y=106
tick_w, tick_h = 28, 4
# Center the tick on the cap height of the eyebrow text (the "A"), not on the
# full font box, so it lines up with the visible letters.
_cap = draw.textbbox((0, eb_y), "A", font=eb_font)
tick_cy = round((_cap[1] + _cap[3]) / 2)
draw.rectangle([LEFT, tick_cy - tick_h // 2, LEFT + tick_w, tick_cy + tick_h // 2], fill=ORANGE_LT)
cx = LEFT + tick_w + 18
track = 2  # letter-spacing
# Wordmark: "Arc" semibold, "Smith" bold.
for i, ch in enumerate(eb_text):
    f = eb_font if i < 3 else eb_bold
    draw.text((cx, eb_y), ch, font=f, fill=EYEBROW_GRAY)
    cx += draw.textlength(ch, font=f) + track

# Long rule to the right of the wordmark, matching the left tick.
draw.rectangle(
    [cx + 14, tick_cy - tick_h // 2, W - LEFT, tick_cy + tick_h // 2], fill=ORANGE_LT
)

# --- title (two lines) --------------------------------------------------
t_font = mono_bold(96)
line1_y = 196
line2_y = line1_y + 104
draw.text((LEFT, line1_y), "A tool builder's", font=t_font, fill=TITLE)
draw.text((LEFT, line2_y), "toolbox.", font=t_font, fill=ORANGE_LT)

# --- subtitle (wrapped) -------------------------------------------------
s_font = sans(42)
sub = "Refined toolbox utilities for GIS research"
max_w = 900
words, lines, cur = sub.split(), [], ""
for w in words:
    test = (cur + " " + w).strip()
    if draw.textlength(test, font=s_font) <= max_w:
        cur = test
    else:
        lines.append(cur)
        cur = w
if cur:
    lines.append(cur)
sy = line2_y + 150
for ln in lines:
    draw.text((LEFT, sy), ln, font=s_font, fill=SUB_GRAY)
    sy += 44

# Output path is anchored to this file: arcsmith-docs/scripts/ -> docs/images/.
out = Path(__file__).resolve().parents[1] / "docs" / "images" / "social-card.png"
os.makedirs(out.parent, exist_ok=True)
img.save(out, "PNG")
print("wrote", out, img.size)
