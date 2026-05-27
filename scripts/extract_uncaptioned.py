"""Extract uncaptioned content images from PDF pages 57+ (Sections 4-9).

Pairs with extract_figures.py which handles captioned figures (figs 1-65).
This script extracts the remaining images and assigns them figure numbers
66, 67, 68, ... in page order.

Outputs:
  - PNG files in site/docs/figures/figure_NN.png
  - figure_positions.json mapping figure number -> (page_num, top_pt) for use
    by build_markdown.py to insert them inline
"""
import pdfplumber
import subprocess
import json
from pathlib import Path
from PIL import Image

PDF = "/mnt/user-data/uploads/A_Guide_to_Geomorphic_Departure_Analysis_using_Relative_Elevation_Models_in_ArcGIS_Pro.pdf"
OUT_DIR = Path("/home/claude/work/site/docs/figures")
TMP_DIR = Path("/home/claude/work/tmp_pages")
TMP_DIR.mkdir(exist_ok=True)
OUT_DIR.mkdir(parents=True, exist_ok=True)

DPI = 200
HEADER_BOTTOM = 50
FOOTER_TOP = 720

# Pages where the captioned figures (1-65) live; skip these
CAPTIONED_FIGURE_PAGES_END = 56  # 1-based; first uncaptioned page is 57
FIRST_PAGE_TO_SCAN = 57

# Start figure numbering for uncaptioned images here
NEXT_FIG_NUM = 66


def rasterize_page(page_num_1based, dpi=DPI):
    out_prefix = TMP_DIR / f"p{page_num_1based:03d}"
    for f in TMP_DIR.glob(f"p{page_num_1based:03d}*.png"):
        f.unlink()
    subprocess.run([
        "pdftoppm", "-png", "-r", str(dpi),
        "-f", str(page_num_1based), "-l", str(page_num_1based),
        PDF, str(out_prefix)
    ], check=True, capture_output=True)
    candidates = sorted(TMP_DIR.glob(f"p{page_num_1based:03d}-*.png"))
    return candidates[0] if candidates else None


def get_content_images(page):
    out = []
    for img in page.images:
        top, bottom = img['top'], img['bottom']
        x0, x1 = img['x0'], img['x1']
        if bottom <= HEADER_BOTTOM:
            continue
        if top >= FOOTER_TOP:
            continue
        if (bottom - top) < 20:  # skip thin strips
            continue
        if (x1 - x0) < 50:  # skip narrow strips
            continue
        out.append(img)
    return out


def merge_overlapping(imgs):
    if not imgs:
        return []
    imgs = sorted(imgs, key=lambda i: i['top'])
    merged = [dict(imgs[0])]
    for img in imgs[1:]:
        last = merged[-1]
        y_overlap = min(img['bottom'], last['bottom']) - max(img['top'], last['top'])
        x_overlap = min(img['x1'], last['x1']) - max(img['x0'], last['x0'])
        if y_overlap > 0 and x_overlap > 0:
            min_h = min(img['bottom'] - img['top'], last['bottom'] - last['top'])
            min_w = min(img['x1'] - img['x0'], last['x1'] - last['x0'])
            if y_overlap > 0.5 * min_h and x_overlap > 0.5 * min_w:
                last['top'] = min(last['top'], img['top'])
                last['bottom'] = max(last['bottom'], img['bottom'])
                last['x0'] = min(last['x0'], img['x0'])
                last['x1'] = max(last['x1'], img['x1'])
                continue
        merged.append(dict(img))
    return merged


def merge_adjacent_stacked(imgs, vertical_gap_threshold=8):
    """Merge images that are stacked vertically with small gaps and have
    overlapping horizontal extent (often a screenshot composed of multiple
    image objects)."""
    if not imgs:
        return []
    imgs = sorted(imgs, key=lambda i: i['top'])
    merged = [dict(imgs[0])]
    for img in imgs[1:]:
        last = merged[-1]
        vertical_gap = img['top'] - last['bottom']
        x_overlap = min(img['x1'], last['x1']) - max(img['x0'], last['x0'])
        x_overlap_ratio = x_overlap / min(img['x1'] - img['x0'], last['x1'] - last['x0']) if min(img['x1'] - img['x0'], last['x1'] - last['x0']) > 0 else 0
        if 0 <= vertical_gap <= vertical_gap_threshold and x_overlap_ratio > 0.6:
            last['top'] = min(last['top'], img['top'])
            last['bottom'] = max(last['bottom'], img['bottom'])
            last['x0'] = min(last['x0'], img['x0'])
            last['x1'] = max(last['x1'], img['x1'])
        else:
            merged.append(dict(img))
    return merged


def crop_image(page_png_path, page_height_pt, bbox):
    im = Image.open(page_png_path)
    w_px, h_px = im.size
    scale_x = w_px / 612.0
    scale_y = h_px / page_height_pt
    pad = 6
    left = max(0, int(bbox['x0'] * scale_x) - pad)
    top = max(0, int(bbox['top'] * scale_y) - pad)
    right = min(w_px, int(bbox['x1'] * scale_x) + pad)
    bottom = min(h_px, int(bbox['bottom'] * scale_y) + pad)
    return im.crop((left, top, right, bottom))


def main():
    positions = {}  # fig_num -> {'page': N, 'top': T}
    next_fig = NEXT_FIG_NUM

    with pdfplumber.open(PDF) as pdf:
        for page_idx in range(FIRST_PAGE_TO_SCAN - 1, len(pdf.pages)):
            page = pdf.pages[page_idx]
            page_num = page_idx + 1
            page_h = page.height
            imgs = get_content_images(page)
            imgs = merge_overlapping(imgs)
            imgs = merge_adjacent_stacked(imgs)
            if not imgs:
                continue
            png_path = rasterize_page(page_num)
            if not png_path:
                continue
            # Sort top to bottom
            imgs = sorted(imgs, key=lambda i: i['top'])
            for img in imgs:
                # Skip very small images that are likely UI fragments
                w = img['x1'] - img['x0']
                h = img['bottom'] - img['top']
                if w * h < 1500:  # less than ~40x40 — too small to matter
                    continue
                fig_num = next_fig
                next_fig += 1
                out_path = OUT_DIR / f"figure_{fig_num:02d}.png"
                cropped = crop_image(png_path, page_h, img)
                cropped.save(out_path, optimize=True)
                positions[fig_num] = {
                    'page': page_num,
                    'top': float(img['top']),
                    'bottom': float(img['bottom']),
                }

    # Save positions for build_markdown.py
    pos_file = OUT_DIR.parent / 'figure_positions.json'
    with open(pos_file, 'w') as f:
        json.dump(positions, f, indent=2)

    print(f"Extracted {len(positions)} uncaptioned figures (figures {NEXT_FIG_NUM}-{next_fig - 1})")
    print(f"Position map saved to {pos_file}")


if __name__ == "__main__":
    main()
