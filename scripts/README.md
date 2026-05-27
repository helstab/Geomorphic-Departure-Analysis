# Conversion Scripts

These scripts produced the markdown and figures in `../docs/`. Keep them for reproducibility — if the source PDF is updated, re-run them to refresh the site.

## Requirements

- Python 3.9+
- `pdfplumber`
- `Pillow` (PIL)
- `pdftoppm` (from `poppler-utils`) on PATH

```bash
pip install pdfplumber Pillow
# Debian/Ubuntu:  sudo apt install poppler-utils
# macOS (brew):   brew install poppler
```

## Usage

Both scripts hard-code the input PDF path near the top — edit the `PDF = ...` line at the top of each script to point to your source PDF. Run them in this order:

```bash
# 1. Extract captioned figures (figs 1-65) — those with "Figure N" labels in the PDF
python extract_figures.py

# 2. Extract uncaptioned content images (figs 66+) — Sections 4-9 screenshots
python extract_uncaptioned.py

# 3. Build markdown sections in ../docs/sections/
python build_markdown.py
```

## What Each Does

| Script | Purpose |
|--------|---------|
| `extract_figures.py` | Walks every page of the PDF, identifies "Figure N" captions by position and font, locates the nearest image bbox, and crops it from a rasterized page image at 200 DPI. Handles cross-page captions where "Figure N" sits on page N+1 referring to an image at the bottom of page N. Produces `figure_01.png` through `figure_65.png`. |
| `extract_uncaptioned.py` | Walks pages 57-111 (Sections 4-9 where the source PDF has no "Figure N" captions) and extracts every content image found, merging stacked image fragments. Assigns numbers 66+ in page order. Writes a `figure_positions.json` mapping each figure to its page and vertical position so `build_markdown.py` can insert them inline at the correct location. |
| `build_markdown.py` | Parses text using pdfplumber's word-level extraction with font metadata. Classifies lines into headings (by font size + bold), figure captions, bullets, numbered items, code blocks, italic note boxes, and body paragraphs. Reads `figure_positions.json` to inject uncaptioned figures at their PDF coordinates. Reconstructs small-caps headings ("O VERVIEW" → "OVERVIEW"), title-cases while preserving known acronyms, joins bullet continuation lines, removes Cambria Math glyphs, and emits one markdown file per top-level section. |

## Known Limitations

- Subscript math notation (Cambria Math font) is dropped — the PDF's `Q_vf`, `Q_av`, etc. are filtered out and their parent headings/sentences read with the math omitted. Canonical titles in `mkdocs.yml` re-supply the subscripts as ASCII.
- Section 8 in the source PDF contains only placeholder labels; the script emits what's there.
- Cross-page sentence breaks may show as truncated; minor manual cleanup in the markdown source is straightforward.
