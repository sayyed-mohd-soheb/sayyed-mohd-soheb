"""
animate_banner.py
------------------
Turns a static developer-portfolio banner PNG into an animated GIF with:
  1. Traveling "data pulse" lights that ride along the existing world-map
     flight-path arcs (top-right globe), plus soft radar "ping" rings at
     the two bright hub nodes.
  2. A line-by-line terminal-style typing reveal for the code snippet
     (top-left) and the tagline ("Building solutions that make impact.").

Usage:
    pip install pillow --break-system-packages
    python animate_banner.py
"""

from PIL import Image, ImageDraw, ImageFilter, ImageEnhance
import math

# =========================================================
# SETTINGS
# =========================================================
INPUT_FILE = "github-banner.png"
OUTPUT_FILE = "github-banner.gif"

FPS = 15
DURATION = 6.0                 # seconds, seamless loop
FRAMES = int(FPS * DURATION)

GREEN = (46, 230, 166)
CYAN = (110, 231, 255)
PURPLE = (150, 130, 246)
WHITE = (235, 245, 255)

# ---------------------------------------------------------
# Globe arcs: quadratic beziers (P0 -> control -> P2) that
# ride along the flight-path lines already drawn in the art.
# ---------------------------------------------------------
ARCS = [
    # big outer loop out of the bright NA node, sweeping down-left
    dict(p0=(703, 60), c=(600, 120), p1=(645, 218), color=GREEN, speed=0.55, phase=0.00, trail=16),
    # NA node -> small coastal node
    dict(p0=(703, 60), c=(735, 100), p1=(742, 152), color=GREEN, speed=0.9, phase=0.15, trail=12),
    # coastal node -> purple hub
    dict(p0=(742, 152), c=(780, 145), p1=(820, 152), color=PURPLE, speed=1.1, phase=0.40, trail=10),
    # far-right bright node sweeping down through the map
    dict(p0=(978, 42), c=(920, 88), p1=(868, 122), color=CYAN, speed=0.7, phase=0.55, trail=14),
    dict(p0=(868, 122), c=(830, 160), p1=(800, 196), color=CYAN, speed=0.7, phase=0.62, trail=14),
]

PINGS = [
    dict(center=(703, 60), color=GREEN, speed=1.0, phase=0.0),
    dict(center=(978, 42), color=CYAN, speed=1.0, phase=0.5),
]

# ---------------------------------------------------------
# Text reveal regions, hand-measured from the source PNG via
# per-row / per-column brightness analysis.
# Each entry: (x0, y0, x1, y1)
# ---------------------------------------------------------
CODE_LINES = [
    (55, 87, 435, 106),
    (55, 106, 435, 124),
    (55, 124, 435, 142),
    (55, 142, 435, 160),
    (55, 160, 435, 178),
    (55, 193, 435, 212),
]
TAG_LINES = [
    (830, 168, 995, 190),
    (830, 191, 995, 213),
]
ALL_LINES = CODE_LINES + TAG_LINES

# Sequential typing windows (fraction of loop 0..1) per line, in order.
TYPE_START = 0.02
TYPE_END = 0.34
HOLD_END = 0.82
ERASE_END = 0.97


def line_windows():
    n = len(ALL_LINES)
    span = TYPE_END - TYPE_START
    per = span / n
    overlap = per * 0.35  # slight overlap so it feels snappier, not robotic
    windows = []
    for i in range(n):
        start = TYPE_START + i * (per - overlap)
        end = start + per
        windows.append((start, end))
    return windows


LINE_WINDOWS = line_windows()


def qbez(p0, c, p1, t):
    x = (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * c[0] + t ** 2 * p1[0]
    y = (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * c[1] + t ** 2 * p1[1]
    return (x, y)


def clamp(v, lo=0.0, hi=1.0):
    return max(lo, min(hi, v))


def make_hidden_crop(base, box):
    crop = base.crop(box).convert("RGB")
    crop = crop.filter(ImageFilter.GaussianBlur(5))
    crop = ImageEnhance.Brightness(crop).enhance(0.32)
    crop = ImageEnhance.Contrast(crop).enhance(0.75)
    return crop.convert("RGBA")


def reveal_fraction(frame_idx, start_f, end_f):
    frame_t = frame_idx / FRAMES
    if frame_t <= start_f:
        rf = 0.0
    elif frame_t >= HOLD_END:
        if frame_t <= ERASE_END:
            erase_t = (frame_t - HOLD_END) / (ERASE_END - HOLD_END)
            rf = 1.0 - erase_t
        else:
            rf = 0.0
    elif frame_t < end_f:
        rf = (frame_t - start_f) / (end_f - start_f)
    else:
        rf = 1.0
    return clamp(rf)


def draw_glow_dot(layer_draw, pt, radius, color, alpha):
    x, y = pt
    layer_draw.ellipse(
        [x - radius, y - radius, x + radius, y + radius],
        fill=color + (alpha,),
    )


def build_globe_layer(size, frame_idx):
    halo = Image.new("RGBA", size, (0, 0, 0, 0))
    core = Image.new("RGBA", size, (0, 0, 0, 0))
    halo_d = ImageDraw.Draw(halo)
    core_d = ImageDraw.Draw(core)

    t = frame_idx / FRAMES

    for arc in ARCS:
        n_trail = arc["trail"]
        phase = (t * arc["speed"] + arc["phase"]) % 1.0
        for i in range(n_trail):
            tt = phase - i * 0.018
            if tt < 0 or tt > 1:
                continue
            pt = qbez(arc["p0"], arc["c"], arc["p1"], tt)
            fade = 1 - i / n_trail
            draw_glow_dot(halo_d, pt, 7 * fade + 2, arc["color"], int(55 * fade))
            draw_glow_dot(core_d, pt, 2.2 * fade + 0.8, WHITE if i == 0 else arc["color"], int(200 * fade))

    for ping in PINGS:
        pt_t = (t * ping["speed"] + ping["phase"]) % 1.0
        radius = 5 + pt_t * 24
        alpha = int((1 - pt_t) * 100)
        cx, cy = ping["center"]
        halo_d.ellipse(
            [cx - radius, cy - radius, cx + radius, cy + radius],
            outline=ping["color"] + (alpha,),
            width=2,
        )

    halo = halo.filter(ImageFilter.GaussianBlur(3))
    core = core.filter(ImageFilter.GaussianBlur(0.6))

    out = Image.alpha_composite(halo, core)
    return out


def build_text_layer(base, frame_idx, hidden_cache):
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    active_cursor = None

    for idx, box in enumerate(ALL_LINES):
        start_f, end_f = LINE_WINDOWS[idx]
        rf = reveal_fraction(frame_idx, start_f, end_f)

        x0, y0, x1, y1 = box
        w = x1 - x0
        h = y1 - y0

        hidden = hidden_cache[idx]
        composite = hidden.copy()

        reveal_w = int(w * rf)
        if reveal_w > 0:
            revealed_part = base.crop(box).convert("RGBA").crop((0, 0, reveal_w, h))
            composite.paste(revealed_part, (0, 0))

        layer.paste(composite, (x0, y0))

        frame_t = frame_idx / FRAMES
        if 0.0 < rf < 1.0 and frame_t < HOLD_END:
            active_cursor = (x0 + reveal_w, y0, y1)
        elif rf >= 1.0 and idx == len(ALL_LINES) - 1 and frame_t < HOLD_END + 0.10:
            active_cursor = (x1, y0, y1)

    if active_cursor is not None:
        blink_on = (frame_idx // 3) % 2 == 0
        if blink_on:
            cx, cy0, cy1 = active_cursor
            d = ImageDraw.Draw(layer)
            d.rectangle([cx, cy0, cx + 2, cy1], fill=GREEN + (230,))

    return layer


def main():
    base = Image.open(INPUT_FILE).convert("RGBA")
    size = base.size

    hidden_cache = [make_hidden_crop(base, box) for box in ALL_LINES]

    rgba_frames = []
    for f in range(FRAMES):
        frame = base.copy()

        text_layer = build_text_layer(base, f, hidden_cache)
        frame = Image.alpha_composite(frame, text_layer)

        globe_layer = build_globe_layer(size, f)
        frame = Image.alpha_composite(frame, globe_layer)

        rgba_frames.append(frame)
        if f % 10 == 0:
            print(f"rendered frame {f}/{FRAMES}")

    # Build one shared palette from a busy mid-loop frame for a stable,
    # non-flickery GIF, then quantize every frame to it.
    ref_idx = int(FRAMES * 0.5)
    ref_rgb = rgba_frames[ref_idx].convert("RGB")
    master_pal = ref_rgb.convert("P", palette=Image.ADAPTIVE, colors=256)

    p_frames = []
    for fr in rgba_frames:
        rgb = fr.convert("RGB")
        p = rgb.quantize(palette=master_pal, dither=Image.NONE)
        p_frames.append(p)

    p_frames[0].save(
        OUTPUT_FILE,
        save_all=True,
        append_images=p_frames[1:],
        duration=int(1000 / FPS),
        loop=0,
        optimize=True,
    )
    print(f"Saved {OUTPUT_FILE}  ({len(p_frames)} frames, {size[0]}x{size[1]})")


if __name__ == "__main__":
    main()
