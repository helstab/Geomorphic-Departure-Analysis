# Geomorphic Departure Analysis Guide — MkDocs Site

A MkDocs Material rendering of *A Guide to Geomorphic Departure Analysis using Relative Elevation Models in ArcGIS Pro* (USDA Forest Service, Lower Middle Fork Teanaway River).


Click [Depature Analysis][ref]

[ref]: https://helstab.github.io/Geomorphic-Departure-Analysis/

## Repository Layout

```
.
├── mkdocs.yml                  # Site configuration & navigation
├── docs/
│   ├── index.md                # Landing page
│   ├── sections/               # One markdown file per top-level section
│   │   ├── 01-overview.md
│   │   ├── 02-watershed-setting.md
│   │   ├── 03-valley-floor-approximation.md
│   │   ├── 04-transect-minimum-elevation-spline-fit.md
│   │   ├── 05-classify-valley-floor-surfaces.md
│   │   ├── 06-geomorphic-grade-line-spline-fit.md
│   │   ├── 07-build-ggl-surface.md
│   │   ├── 08-ggl-design-surface.md
│   │   └── 09-appendix.md
│   └── figures/                # 159 extracted figures (figure_01.png … figure_159.png)
├── scripts/                    # Conversion scripts (re-runnable if PDF is updated)
│   ├── extract_figures.py      # Captioned figures (1-65)
│   ├── extract_uncaptioned.py  # Uncaptioned screenshots in Sections 4-9 (66+)
│   ├── build_markdown.py
│   └── README.md
└── README.md
```

## Local Preview

Requirements: Python 3.9+

```bash
pip install mkdocs-material
mkdocs serve
```

Open <http://127.0.0.1:8000> in a browser. Edits to markdown files refresh automatically.

## Build Static Site

```bash
mkdocs build
```

Produces a static site in `./site/` ready to host anywhere.

## Deploy to GitHub Pages

1. Push this repository to GitHub.
2. Uncomment the `repo_url` and `repo_name` lines in `mkdocs.yml` (set them to your repo).
3. From the repo root, run:

   ```bash
   mkdocs gh-deploy
   ```

   This builds the site and pushes it to the `gh-pages` branch. GitHub Pages will serve it at `https://YOUR_USER.github.io/YOUR_REPO/`.

4. In your GitHub repo settings → Pages, set the source to the `gh-pages` branch.

Alternative: configure a GitHub Actions workflow to build and deploy automatically on push to `main`. Save the following as `.github/workflows/deploy.yml`:

```yaml
name: Deploy MkDocs
on:
  push:
    branches: [main]
permissions:
  contents: write
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.x'
      - run: pip install mkdocs-material
      - run: mkdocs gh-deploy --force
```

## Editing Content

Each section is a standalone markdown file under `docs/sections/`. Standard MkDocs Material conventions apply:

- **Headings**: `#`, `##`, `###` for section, subsection, sub-subsection. Anchors are auto-generated.
- **Figures**: referenced relative to the markdown file, e.g. `![Figure 7](../figures/figure_07.png)`.
- **Note boxes**: MkDocs admonitions, e.g.

  ```markdown
  !!! note
      Bathymetric LiDAR was used in this example...
  ```

  Other admonition flavors available: `tip`, `warning`, `info`, `example`.

- **Code blocks**: triple-backtick fences with language hint:

  ````markdown
  ```python
  import numpy as np
  ```
  ````

## Source

Original PDF: *A Guide to Geomorphic Departure Analysis using Relative Elevation Models in ArcGIS Pro (Lower Middle Fork Teanaway River)*. USDA Forest Service Washington Office, Enterprise Program, Restoration Services. Aquatic Restoration Team. 2025.

This markdown rendering was produced by automated extraction; some manual cleanup of figure references, equation notation (e.g., `Q_vf`, `Q_av`), and section transitions may improve readability further.

## Known Conversion Limitations

| Limitation | Detail |
|------------|--------|
| Subscript math notation | Cambria Math glyphs (e.g., `Q_vf`, `Q_av`) were dropped during extraction; section titles in `mkdocs.yml` include the ASCII equivalents (e.g., "Valley Floor Approximation (Qvf)"). |
| Heading wraps | Headings spanning two PDF lines are joined automatically, but check long headings in Section 6 in particular. |
| Section 8 | The source PDF includes only placeholder labels (Objective/Purpose/Notes/Steps) for Section 8 — that placeholder content is what appears here. |
| Cross-page sentence breaks | A few sentences split across PDF pages may show as broken at the page boundary; manual repair is straightforward in the markdown source. |
