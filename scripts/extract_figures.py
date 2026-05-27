"""Extract figures from the PDF, save with figure number names."""
import pdfplumber
import re
import subprocess
from pathlib import Path
from PIL import Image

PDF = "/mnt/user-data/uploads/A_Guide_to_Geomorphic_Departure_Analysis_using_Relative_Elevation_Models_in_ArcGIS_Pro.pdf"
OUT_DIR = Path("/home/claude/work/site/docs/figures")
TMP_DIR = Path("/home/claude/work/tmp_pages")
TMP_DIR.mkdir(exist_ok=True)
OUT_DIR.mkdir(parents=True, exist_ok=True)

DPI = 200
# pdfplumber pages are 612 pts wide; at 200 DPI that = 612 * 200/72 = 1700 px

# Pixel scale factor from PDF points to image pixels
SCALE = DPI / 72.0

# Header strip top extent (logo strip) - anything fully within top y < ~50 ignored
# Footer strip - top > 720 ignored (date/url bar)
HEADER_BOTTOM = 50
FOOTER_TOP = 720


def rasterize_page(pdf_path, page_num_1based, dpi=DPI):
    """Rasterize a single page to PNG via pdftoppm."""
    out_prefix = TMP_DIR / f"p{page_num_1based:03d}"
    # Clean previous
    for f in TMP_DIR.glob(f"p{page_num_1based:03d}*.png"):
        f.unlink()
    subprocess.run([
        "pdftoppm", "-png", "-r", str(dpi),
        "-f", str(page_num_1based), "-l", str(page_num_1based),
        pdf_path, str(out_prefix)
    ], check=True, capture_output=True)
    # pdftoppm zero-pads based on total pages (111 pages -> 3 digits)
    candidates = sorted(TMP_DIR.glob(f"p{page_num_1based:03d}-*.png"))
    if not candidates:
        return None
    return candidates[0]


def find_figure_locations(pdf):
    """Return dict {fig_num: (page_idx, caption_top_pt)}."""
    fig_map = {}
    fig_pattern = re.compile(r'^Figure\s+(\d+)$')
    for i, page in enumerate(pdf.pages):
        words = page.extract_words()
        for j, w in enumerate(words):
            if w['text'] == 'Figure' and j + 1 < len(words):
                next_w = words[j + 1]
                # Check next word is a number and they're on the same line
                if next_w['text'].isdigit() and abs(next_w['top'] - w['top']) < 3:
                    fig_num = int(next_w['text'])
                    fig_map[fig_num] = (i, w['top'])
    return fig_map


def get_content_images(page):
    """Return list of images that are NOT header/footer decoration."""
    out = []
    for img in page.images:
        top = img['top']
        bottom = img['bottom']
        # Skip header/footer
        if bottom <= HEADER_BOTTOM:
            continue
        if top >= FOOTER_TOP:
            continue
        # Skip very thin strips (horizontal lines, banners)
        if (bottom - top) < 15:
            continue
        # Skip very narrow strips
        if (img['x1'] - img['x0']) < 30:
            continue
        out.append(img)
    return out


def merge_overlapping(imgs):
    """Merge images whose bboxes substantially overlap (often a base image
    plus annotations are recorded as separate image objects)."""
    if not imgs:
        return []
    # Sort by top
    imgs = sorted(imgs, key=lambda i: i['top'])
    merged = [dict(imgs[0])]
    for img in imgs[1:]:
        last = merged[-1]
        # Check overlap on y-axis
        y_overlap = min(img['bottom'], last['bottom']) - max(img['top'], last['top'])
        x_overlap = min(img['x1'], last['x1']) - max(img['x0'], last['x0'])
        # Overlap area
        if y_overlap > 0 and x_overlap > 0:
            min_h = min(img['bottom']-img['top'], last['bottom']-last['top'])
            min_w = min(img['x1']-img['x0'], last['x1']-last['x0'])
            if y_overlap > 0.5 * min_h and x_overlap > 0.5 * min_w:
                # Merge: expand last to union
                last['top'] = min(last['top'], img['top'])
                last['bottom'] = max(last['bottom'], img['bottom'])
                last['x0'] = min(last['x0'], img['x0'])
                last['x1'] = max(last['x1'], img['x1'])
                continue
        merged.append(dict(img))
    return merged


def assign_figures_to_images(page_idx, fig_nums_on_page, fig_caption_tops, images):
    """Match each figure caption to the nearest preceding image on the page."""
    # Sort figures by caption top
    figs = sorted(fig_nums_on_page, key=lambda n: fig_caption_tops[n])
    # Sort images by top
    images_sorted = sorted(images, key=lambda i: i['top'])
    assignments = {}  # fig_num -> image dict
    used = set()
    for fig_num in figs:
        cap_top = fig_caption_tops[fig_num]
        # Find image whose bottom is closest above caption (cap_top should be > img.bottom)
        best = None
        best_dist = float('inf')
        for idx, img in enumerate(images_sorted):
            if idx in used:
                continue
            if img['bottom'] <= cap_top + 5:  # small tolerance
                dist = cap_top - img['bottom']
                if dist < best_dist:
                    best_dist = dist
                    best = idx
        if best is not None:
            assignments[fig_num] = images_sorted[best]
            used.add(best)
        else:
            # Fallback: pick nearest unused image
            for idx, img in enumerate(images_sorted):
                if idx in used:
                    continue
                assignments[fig_num] = img
                used.add(idx)
                break
    return assignments


def crop_image(page_png_path, page_height_pt, bbox):
    """Crop using bbox in PDF points. page_height_pt = page height in points."""
    im = Image.open(page_png_path)
    w_px, h_px = im.size
    # PDF coordinate: top is from top of page, in points
    # Image coordinate: same (PIL top-left origin), scaled
    scale_x = w_px / 612.0
    scale_y = h_px / page_height_pt
    # Add small padding
    pad = 6
    left = max(0, int(bbox['x0'] * scale_x) - pad)
    top = max(0, int(bbox['top'] * scale_y) - pad)
    right = min(w_px, int(bbox['x1'] * scale_x) + pad)
    bottom = min(h_px, int(bbox['bottom'] * scale_y) + pad)
    return im.crop((left, top, right, bottom))


def main():
    with pdfplumber.open(PDF) as pdf:
        fig_map = find_figure_locations(pdf)
        print(f"Captions found: {len(fig_map)}")

        # For each figure caption, determine its source page (could be prev page
        # if caption appears at top of page with no preceding image)
        # A caption near the top (top < ~100 pt) and with no image above it on
        # the same page actually refers to an image on the previous page.

        # Build per-page assignments
        # Each fig_num gets: (source_page_idx, bbox)
        fig_source = {}  # fig_num -> (page_idx, bbox)

        # Pre-compute content images per page
        page_images = {}
        for i, page in enumerate(pdf.pages):
            page_images[i] = merge_overlapping(get_content_images(page))

        # For each page, separate captions into "belongs to prev page" and "this page"
        prev_page_pending = {}  # page_idx -> list of (fig_num, virtual top in prev page coords)

        # Sort figures by page then caption top
        figs_sorted = sorted(fig_map.items(), key=lambda kv: (kv[1][0], kv[1][1]))

        # Group by page
        captions_on_page = {}
        for fig_num, (page_idx, cap_top) in figs_sorted:
            captions_on_page.setdefault(page_idx, []).append((fig_num, cap_top))

        rasterized = {}

        for page_idx, page in enumerate(pdf.pages):
            caps = captions_on_page.get(page_idx, [])
            imgs = page_images[page_idx]
            if not caps:
                continue

            # Sort by caption top
            caps_sorted = sorted(caps, key=lambda c: c[1])
            imgs_sorted = sorted(imgs, key=lambda i: i['top'])

            # Determine which captions refer to prev page (caption-above-images)
            top_caps = []
            same_page_caps = []
            first_img_top = imgs_sorted[0]['top'] if imgs_sorted else 1000
            for fig_num, cap_top in caps_sorted:
                if cap_top < first_img_top and cap_top < 150:
                    # Caption at top of page, before any image - prev page
                    top_caps.append((fig_num, cap_top))
                else:
                    same_page_caps.append((fig_num, cap_top))

            # Assign top_caps to LAST images on previous page
            if top_caps:
                prev_imgs = sorted(page_images.get(page_idx - 1, []),
                                   key=lambda i: i['top'])
                # The last N images on previous page correspond to the N top captions
                # (in order). Take the last len(top_caps) images.
                if prev_imgs:
                    n = len(top_caps)
                    target_imgs = prev_imgs[-n:]
                    for (fig_num, _), img in zip(top_caps, target_imgs):
                        fig_source[fig_num] = (page_idx - 1, img)

            # Assign same_page_caps to images on this page in order
            # Some images may already be claimed by NEXT page's top captions;
            # but we resolve this when iterating next page. For now claim greedily
            # in order: caption_i -> image_i (skipping images already claimed)
            available_imgs = list(imgs_sorted)
            for fig_num, cap_top in same_page_caps:
                # Find first image whose bottom is <= cap_top + tolerance
                chosen = None
                for img in available_imgs:
                    if img['bottom'] <= cap_top + 5:
                        chosen = img
                        break
                if chosen is None and available_imgs:
                    chosen = available_imgs[0]
                if chosen is not None:
                    fig_source[fig_num] = (page_idx, chosen)
                    available_imgs.remove(chosen)

        # Now extract / crop each figure
        results = []
        for fig_num in sorted(fig_source.keys()):
            page_idx, bbox = fig_source[fig_num]
            if page_idx not in rasterized:
                rasterized[page_idx] = rasterize_page(PDF, page_idx + 1)
            png_path = rasterized[page_idx]
            page_h = pdf.pages[page_idx].height
            out_path = OUT_DIR / f"figure_{fig_num:02d}.png"
            cropped = crop_image(png_path, page_h, bbox)
            cropped.save(out_path, optimize=True)
            results.append((fig_num, page_idx + 1, out_path))

        # Report missing figure numbers
        all_nums = set(fig_map.keys())
        extracted = set(r[0] for r in results)
        missing = all_nums - extracted
        print(f"Extracted {len(extracted)} of {len(all_nums)} figures")
        if missing:
            print(f"Missing: {sorted(missing)}")
        # Save figure-to-page mapping for use in markdown build
        with open(OUT_DIR / "figure_pages.txt", "w") as f:
            for fig_num, page_idx, _ in sorted(results):
                f.write(f"{fig_num}\t{page_idx}\n")


if __name__ == "__main__":
    main()
