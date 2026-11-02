"""Compose detailed multi-panel IDF figures from the data folder images.

Reads the pipeline stage images stored under data/eval/<plan>/ and
data/processed/ and writes labelled composite figures into
research_deliverables/ieee_latex/figures/ (idf_*.png).
"""

import os
import glob

from PIL import Image, ImageDraw, ImageFont

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "data")
FIG_DIR = os.path.join(BASE, "research_deliverables", "ieee_latex", "figures")

PANEL_W = 760
LABEL_H = 56
GAP = 14
BG = (255, 255, 255)
LABEL_BG = (31, 56, 100)
LABEL_FG = (255, 255, 255)

_stages = [
    ("01_original", "1. Input raster"),
    ("02b_walls_threshold_mask", "2. Wall threshold mask"),
    ("03a_closed_walls", "3. Adaptive gap closing"),
    ("03b_detected_walls", "4. Hough wall detection"),
    ("04a_room_segmentation", "5. Room segmentation"),
    ("04b_corridor_segmentation", "6. Corridor segmentation"),
    ("05_door_detections", "7. Door detection"),
    ("07_final_annotated_floorplan", "8. Final annotated plan"),
]


def _font(size):
    for name in ("arialbd.ttf", "arial.ttf", "DejaVuSans-Bold.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except Exception:
            continue
    return ImageFont.load_default()


def compose_grid(panels, out_name, cols=4, title=None, panel_w=PANEL_W):
    if not panels:
        raise ValueError("no panels")
    cells = []
    for path, label in panels:
        im = Image.open(path).convert("RGB")
        h = max(1, int(im.height * panel_w / im.width))
        cells.append((im.resize((panel_w, h), Image.LANCZOS), label))
    rows = (len(cells) + cols - 1) // cols
    cell_h = max(c[0].height for c in cells) + LABEL_H
    W = cols * panel_w + (cols + 1) * GAP
    H = rows * cell_h + (rows + 1) * GAP
    if title:
        H += LABEL_H + 8
    canvas = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(canvas)
    y = GAP
    if title:
        f_t = _font(40)
        tw = d.textlength(title, font=f_t)
        d.text(((W - tw) // 2, y), title, fill=(31, 56, 100), font=f_t)
        y += LABEL_H + 8
    f_lab = _font(26)
    for i, (im, label) in enumerate(cells):
        r, c = divmod(i, cols)
        x = GAP + c * (panel_w + GAP)
        cy = y + r * (cell_h + GAP)
        canvas.paste(im, (x, cy))
        ly = cy + im.height + 6
        d.rectangle([x + 2, ly, x + panel_w - 2, ly + LABEL_H - 14], fill=LABEL_BG)
        text = d.textlength(label, font=f_lab)
        d.text((x + (panel_w - text) // 2, ly + 6), label, fill=LABEL_FG, font=f_lab)
    out = os.path.join(FIG_DIR, out_name)
    canvas.save(out)
    print("figure written:", out, canvas.size)


def find_plan_dir(plan):
    p = os.path.join(DATA, "eval", plan)
    if os.path.isdir(p):
        return p
    return None


def _plan_panels(plan):
    d = find_plan_dir(plan)
    panels = []
    for key, label in _stages:
        path = os.path.join(d, key + ".png")
        if os.path.exists(path):
            panels.append((path, label))
    return panels


def build_plan_overview(plan, out_name, title):
    compose_grid(_plan_panels(plan), out_name, cols=4, title=title,
                 panel_w=740 if plan != "apartment_floorplan" else 700)


def build_nav_graphs(out_name="idf_nav_graphs.png"):
    imgs = []
    labels = []
    for plan, label in (("sample_floorplan", "Sample plan: dual-panel navigation graph"),
                        ("apartment_floorplan", "Apartment plan: dual-panel navigation graph"),
                        ("office_floorplan", "Office plan: dual-panel navigation graph")):
        p = os.path.join(DATA, "eval", plan, "08_navigation_graph.png")
        if os.path.exists(p):
            imgs.append(Image.open(p).convert("RGB"))
            labels.append(label)
    if not imgs:
        raise ValueError("no navigation graphs found")
    W = 2400
    pad = 60
    h = 30
    for im in imgs:
        h += int(im.height * W / im.width) + 90
    canvas = Image.new("RGB", (W + 2 * pad, h + pad), BG)
    d = ImageDraw.Draw(canvas)
    f_t = _font(38)
    y = pad
    for im, label in zip(imgs, labels):
        tw = d.textlength(label, font=f_t)
        d.text(((W + 2 * pad - tw) // 2, y), label, fill=(31, 56, 100), font=f_t)
        y += 70
        nim = im.resize((W, int(im.height * W / im.width)), Image.LANCZOS)
        canvas.paste(nim, (pad, y))
        y += nim.height + 40
    out = os.path.join(FIG_DIR, out_name)
    canvas.save(out)
    print("figure written:", out, canvas.size)


def build_zoom_details(out_name="idf_detail_zoom.png"):
    """Close-up crops showing wall/door fine structure (apartment folder)."""
    d = os.path.join(DATA, "eval", "apartment_floorplan")
    picks = [
        (os.path.join(d, "doors_debug.png"), "Doors overlay (full plan)"),
        (os.path.join(d, "door_tl_crop.png"), "Zoom: door symbol"),
        (os.path.join(d, "stair_crop.png"), "Zoom: stairwell walls"),
        (os.path.join(d, "hall_left_wall.png"), "Zoom: corridor wall"),
        (os.path.join(d, "bedroom_crop.png"), "Zoom: room boundary"),
        (os.path.join(d, "bed_right_wall.png"), "Zoom: thin wall line"),
    ]
    panels = [(p, l) for p, l in picks if os.path.exists(p)]
    ups = []
    for path, label in panels:
        im = Image.open(path).convert("RGB")
        # upscale tiny crops with nearest-neighbour to keep crisp edges
        scale = max(1, min(5, 560 // max(im.width, 1)))
        if scale > 1:
            im = im.resize((im.width * scale, im.height * scale), Image.NEAREST)
        # guard against gigantic upscales / tall crops
        if im.width > 560:
            im = im.resize((560, int(im.height * 560 / im.width)), Image.LANCZOS)
        if im.height > 500:
            im = im.resize((int(im.width * 500 / im.height), 500), Image.LANCZOS)
        ups.append((im, label))
    rows = [[ups[0], ups[1], ups[2]], [ups[3], ups[4], ups[5]]]
    rows = [[p for p in r if p is not None] for r in rows]
    rows = [r for r in rows if r]
    cell_w = 560
    lab_h = 52
    gap = 16
    row_h = []
    for r in rows:
        row_h.append(max(im.height for im, _ in r))
    H = sum(row_h) + len(rows) * lab_h + (len(rows) + 4) * gap
    W = max(len(r) for r in rows) * (cell_w + gap) + gap
    canvas = Image.new("RGB", (W, H), BG)
    dr = ImageDraw.Draw(canvas)
    f_lab = _font(24)
    y = gap
    for r_i, r in enumerate(rows):
        x = gap
        for im, label in r:
            # vertical-pad smaller-height neighbours for a clean row
            ox = x + (cell_w - im.width) // 2
            canvas.paste(im, (ox, y))
            ly = y + row_h[r_i] + 6
            tw = dr.textlength(label, font=f_lab)
            dr.text((x + (cell_w - tw) // 2, ly), label, fill=(31, 56, 100), font=f_lab)
            x += cell_w + gap
        y += row_h[r_i] + lab_h + gap
    out = os.path.join(FIG_DIR, out_name)
    canvas.save(out)
    print("figure written:", out, canvas.size)


def build_all():
    build_plan_overview("apartment_floorplan", "idf_apartment_pipeline.png",
                        "Apartment plan \u2014 full CV pipeline walkthrough")
    build_plan_overview("office_floorplan", "idf_office_pipeline.png",
                        "Office plan \u2014 full CV pipeline walkthrough")
    build_plan_overview("sample_floorplan", "idf_sample_pipeline.png",
                        "Sample plan \u2014 full CV pipeline walkthrough")
    build_nav_graphs()
    build_zoom_details()


if __name__ == "__main__":
    build_all()
