"""Convert the geomorphic departure analysis PDF to MkDocs markdown.

Uses font size + weight to classify text into headings, body, italic notes,
code blocks, and figure captions. Produces one markdown file per top-level
section, with figure references linked to extracted PNGs.
"""
import pdfplumber
import re
from pathlib import Path
from collections import Counter

PDF = "/mnt/user-data/uploads/A_Guide_to_Geomorphic_Departure_Analysis_using_Relative_Elevation_Models_in_ArcGIS_Pro.pdf"
DOCS_DIR = Path("/home/claude/work/site/docs")
SECTIONS_DIR = DOCS_DIR / "sections"
SECTIONS_DIR.mkdir(parents=True, exist_ok=True)

FIRST_CONTENT_PAGE = 5  # Skip cover and TOC

TOP_SECTIONS = [
    (1, "01-overview", "Overview"),
    (2, "02-watershed-setting", "Describe Watershed Setting and Historical Context"),
    (3, "03-valley-floor-approximation", "Valley Floor Approximation (Qvf)"),
    (4, "04-transect-minimum-elevation-spline-fit", "Transect Minimum Elevation Spline Fit"),
    (5, "05-classify-valley-floor-surfaces", "Explore and Classify Valley Floor Surface Types"),
    (6, "06-geomorphic-grade-line-spline-fit", "Geomorphic Grade Line Spline Fit"),
    (7, "07-build-ggl-surface", "Build GGL Surface"),
    (8, "08-ggl-design-surface", "GGL Design Surface"),
    (9, "09-appendix", "Appendix (Additional Learning)"),
]

HEADER_BOTTOM_PT = 50
FOOTER_TOP_PT = 720
BULLET_GLYPHS = {'•', '●', '·'}
SUB_BULLET_GLYPHS = {'o', 'O'}
HEADING_NUM_RE = re.compile(r'^(\d+(?:\.\d+)*)\.?$')

ACRONYMS = {
    'GIS', 'GGL', 'REM', 'IDW', 'TIN', 'DEM', 'LiDAR', 'NHD', 'CSV',
    'HEC-RAS', 'WSDOT', 'USFS', 'HUC', 'NAIP', 'CAD', 'BDA', 'LWD',
    'IQR', 'KDE', 'SD', 'CRS', 'AOI', 'API', 'QGIS', 'SEM', 'SET',
    'T1', 'Qvf', 'Qav', 'Qggl', 'GPS', 'GDB', 'TOC', '2D', '3D', '1D',
    'Q', 'NoData', 'ID', 'XY', 'Z',
}
ACRONYMS_UPPER = {a.upper(): a for a in ACRONYMS}


def font_class(w):
    """Classify a word's font."""
    size = round(w.get('size', 10), 1)
    fn = w.get('fontname', '')
    is_bold = 'Bold' in fn or 'Black' in fn
    is_italic = 'Italic' in fn
    is_mono = 'Courier' in fn or 'Mono' in fn or 'Consolas' in fn
    if is_mono:
        return 'code'
    if size >= 17:
        return 'h1'
    if size >= 13:
        return 'h2'
    if size >= 10.5 and is_bold:
        return 'h3' if not is_italic else 'h3'
    if size <= 9.5 and is_italic:
        return 'italic_small'
    if size >= 10.5 and is_italic:
        return 'italic_body'
    if size <= 9.5 and is_bold:
        return 'bold_small'
    return 'body'


def in_skip_zone(top):
    return top < HEADER_BOTTOM_PT or top > FOOTER_TOP_PT


def group_words_to_lines(words, y_tol=6):
    """Group words on the same baseline. Drops Cambria Math glyphs which can't
    be reliably reassembled into LaTeX subscript notation."""
    if not words:
        return []
    # Filter Cambria Math
    words = [w for w in words
             if 'CambriaMath' not in w.get('fontname', '')
             and 'Math' not in w.get('fontname', '')]
    if not words:
        return []
    ws = sorted(words, key=lambda w: (w['top'], w['x0']))
    lines = []
    cur, cur_top = [ws[0]], ws[0]['top']
    for w in ws[1:]:
        if abs(w['top'] - cur_top) <= y_tol:
            cur.append(w)
        else:
            lines.append(sorted(cur, key=lambda x: x['x0']))
            cur = [w]
            cur_top = w['top']
    lines.append(sorted(cur, key=lambda x: x['x0']))
    return lines


def line_text(line):
    return ' '.join(w['text'] for w in line)


def line_x0(line):
    return min(w['x0'] for w in line)


def line_top(line):
    return min(w['top'] for w in line)


def dominant_class(line):
    counter = Counter()
    for w in line:
        cls = font_class(w)
        counter[cls] += max(1, len(w['text']))
    return counter.most_common(1)[0][0]


def reconstruct_heading_text(line):
    """Reconstruct heading text from line, merging small-caps splits.

    Small caps headings often render as two text runs:
    'O' at size 18 + 'VERVIEW' at size 14.5 -> 'OVERVIEW'.
    """
    # The first word is the number "1", "1.1" etc.
    # Subsequent words form the heading text. Merge same-x-adjacent words
    # where they appear glued together (no gap).
    text_words = line[1:]  # everything after the number
    if not text_words:
        return ''
    merged = []
    cur = text_words[0]['text']
    prev_x1 = text_words[0]['x1']
    for w in text_words[1:]:
        x0 = w['x0']
        # If gap is very small (< 1 pt), this is a continuation of the same word
        if x0 - prev_x1 < 1.0:
            cur += w['text']
        else:
            merged.append(cur)
            cur = w['text']
        prev_x1 = w['x1']
    merged.append(cur)
    return ' '.join(merged)


def is_heading(line):
    if not line:
        return None
    first = line[0]
    first_text = first['text']
    m = HEADING_NUM_RE.match(first_text)
    if not m:
        return None
    number = m.group(1)
    parts = number.split('.')
    level = len(parts)
    cls = font_class(first)
    rest = reconstruct_heading_text(line)
    if rest.count('.') > 10:
        return None
    if cls == 'h1' and level == 1:
        return (1, number, rest)
    if cls == 'h2' and level >= 1:
        return (level, number, rest)
    if cls == 'h3' and level >= 2:
        return (level, number, rest)
    return None


def is_figure_caption(line):
    if len(line) < 2:
        return None
    if line[0]['text'] != 'Figure':
        return None
    second = line[1]['text']
    if not second.rstrip('.').isdigit():
        return None
    fig_num = int(second.rstrip('.'))
    caption = ' '.join(w['text'] for w in line[2:]).strip()
    cls = font_class(line[0])
    if cls not in ('italic_small', 'italic_body'):
        return None
    return (fig_num, caption)


def line_kind(line):
    if not line:
        return ('skip', None)
    if in_skip_zone(line_top(line)):
        return ('skip', None)
    t = line_text(line).strip()
    if t.isdigit() and len(line) == 1:
        return ('skip', None)
    h = is_heading(line)
    if h:
        return ('heading', h)
    f = is_figure_caption(line)
    if f:
        return ('caption', f)
    first_text = line[0]['text']
    # Sub-bullet 'o' in Courier (used by this PDF for nested bullets)
    if (first_text in SUB_BULLET_GLYPHS and len(line) > 1
            and 'Courier' in line[0].get('fontname', '')):
        rest = ' '.join(w['text'] for w in line[1:])
        return ('bullet', (2, rest))
    if first_text in BULLET_GLYPHS:
        rest = ' '.join(w['text'] for w in line[1:])
        x0 = line_x0(line)
        level = 1 if x0 < 140 else 2 if x0 < 180 else 3
        return ('bullet', (level, rest))
    if first_text in SUB_BULLET_GLYPHS and len(line) > 1:
        x0 = line_x0(line)
        if x0 > 110:
            rest = ' '.join(w['text'] for w in line[1:])
            return ('bullet', (2, rest))
    if re.match(r'^\d+\.$', first_text) and len(line) > 1:
        x0 = line_x0(line)
        if x0 >= 85:  # indented from leftmost text margin (x=72)
            rest = ' '.join(w['text'] for w in line[1:])
            return ('numbered', rest)
    # Code: multiple Courier words on the same line
    courier_count = sum(1 for w in line if 'Courier' in w.get('fontname', ''))
    if courier_count >= 2 or (courier_count == 1 and len(line) == 1
                              and line[0]['text'] not in SUB_BULLET_GLYPHS):
        return ('code', t)
    cls = dominant_class(line)
    if cls == 'italic_small':
        return ('italic_small', t)
    if cls == 'italic_body':
        return ('italic_body', t)
    if cls == 'bold_small':
        return ('bold_small', t)
    # Unnumbered bold/h3 line — treat as inline bold label (e.g., "Data Needs:")
    if cls in ('h3',):
        return ('inline_label', t)
    return ('body', t, line_x0(line))


def fix_text(t):
    t = re.sub(r'\s+', ' ', t)
    # Fix split hyphenated words: "process- based" -> "process-based"
    t = re.sub(r'(\w)-\s+(\w)', r'\1-\2', t)
    return t.strip()


def title_case_heading(text):
    if not text:
        return text
    connectors = {'AND', 'OR', 'OF', 'IN', 'TO', 'ON', 'THE', 'A', 'AN',
                  'BY', 'FOR', 'WITH', 'AT', 'AS', 'IS', 'IF', 'BUT', 'VS'}
    words = text.split()
    out = []
    for w in words:
        leading, trailing, core = '', '', w
        while core and not core[0].isalnum():
            leading += core[0]
            core = core[1:]
        while core and not core[-1].isalnum():
            trailing = core[-1] + trailing
            core = core[:-1]
        if not core:
            out.append(w)
            continue
        # Connector words → lowercase
        if core.upper() in connectors:
            out.append(leading + core.lower() + trailing)
            continue
        # Known acronyms → keep canonical case
        if core.upper() in ACRONYMS_UPPER:
            out.append(leading + ACRONYMS_UPPER[core.upper()] + trailing)
            continue
        # Hyphenated tokens: handle each part
        if '-' in core:
            parts = core.split('-')
            new_parts = []
            for p in parts:
                if p.upper() in ACRONYMS_UPPER:
                    new_parts.append(ACRONYMS_UPPER[p.upper()])
                elif p.isupper():
                    new_parts.append(p.capitalize())
                else:
                    new_parts.append(p)
            out.append(leading + '-'.join(new_parts) + trailing)
            continue
        # All-caps: convert to capitalized unless it's a known acronym
        if core.isupper() and core.isalpha():
            out.append(leading + core.capitalize() + trailing)
            continue
        out.append(leading + core + trailing)
    result = ' '.join(out)
    # Clean up empty parens left by removed math glyphs: "Heading ( )" -> "Heading"
    result = re.sub(r'\(\s*\)', '', result).strip()
    result = re.sub(r'\s+', ' ', result)
    if result:
        result = result[0].upper() + result[1:]
    return result


def load_uncaptioned_positions():
    """Load uncaptioned figure positions from extract_uncaptioned.py output."""
    import json
    pos_file = DOCS_DIR / 'figure_positions.json'
    if not pos_file.exists():
        return {}
    with open(pos_file) as f:
        data = json.load(f)
    # Convert keys to int, group by page
    by_page = {}
    for fig_num, info in data.items():
        page = info['page']
        by_page.setdefault(page, []).append({
            'fig_num': int(fig_num),
            'top': info['top'],
            'bottom': info['bottom'],
        })
    # Sort each page's list by top
    for page in by_page:
        by_page[page].sort(key=lambda x: x['top'])
    return by_page


def parse_pdf(pdf):
    blocks = []
    current_section = None
    inserted_figs = set()
    uncap_by_page = load_uncaptioned_positions()
    for page_idx, page in enumerate(pdf.pages):
        page_num = page_idx + 1
        if page_num < FIRST_CONTENT_PAGE:
            continue
        words = page.extract_words(extra_attrs=["fontname", "size"])
        lines = group_words_to_lines(words)
        prev_bottom = None
        last_heading_block_idx = None
        # Pending uncaptioned figures for this page, sorted by top
        pending_uncap = list(uncap_by_page.get(page_num, []))
        uncap_idx = 0
        for line in lines:
            top = line_top(line)
            bot = max(w['bottom'] for w in line)
            # Before processing this line, insert any uncaptioned figures whose
            # top is above this line's top (they should appear before this line)
            while uncap_idx < len(pending_uncap) and pending_uncap[uncap_idx]['top'] < top:
                fig_info = pending_uncap[uncap_idx]
                fig_num = fig_info['fig_num']
                if fig_num not in inserted_figs:
                    blocks.append((current_section, 'figure', {
                        'number': fig_num,
                        'caption': '',
                    }))
                    inserted_figs.add(fig_num)
                    last_heading_block_idx = None  # Figure closes heading-wrap window
                uncap_idx += 1
            kind = line_kind(line)
            kt = kind[0]
            if kt == 'skip':
                continue
            if prev_bottom is not None and (top - prev_bottom) > 8:
                blocks.append((current_section, 'parabreak', None))
            prev_bottom = bot
            if kt == 'heading':
                level, number, htext = kind[1]
                if level == 1:
                    try:
                        current_section = int(number)
                    except ValueError:
                        pass
                blocks.append((current_section, 'heading', {
                    'level': level,
                    'number': number,
                    'text': title_case_heading(htext.strip()),
                }))
                last_heading_block_idx = len(blocks) - 1
                continue
            # If we just saw a heading and this is an inline_label/body line
            # with at most a single parabreak in between, treat as heading-wrap
            # continuation. (The gap between heading and its wrapped second line
            # is often the same as a regular paragraph break.)
            heading_wrap = False
            if (kt in ('inline_label', 'body')
                    and last_heading_block_idx is not None
                    and line_x0(line) >= 95):
                # Look backwards: all blocks between last_heading_block_idx and now
                # must be parabreaks (at most 2)
                between = blocks[last_heading_block_idx + 1:]
                if all(b[1] == 'parabreak' for b in between) and len(between) <= 2:
                    heading_wrap = True
            if heading_wrap:
                merged = []
                cur = line[0]['text']
                prev_x1 = line[0]['x1']
                for w in line[1:]:
                    if w['x0'] - prev_x1 < 1.0:
                        cur += w['text']
                    else:
                        merged.append(cur)
                        cur = w['text']
                    prev_x1 = w['x1']
                merged.append(cur)
                extra = ' '.join(merged)
                hd = blocks[last_heading_block_idx][2]
                cur_text = hd['text']
                if cur_text.endswith('-'):
                    extra_combined = cur_text + extra
                else:
                    extra_combined = cur_text + ' ' + extra
                hd['text'] = title_case_heading(extra_combined.strip())
                # Remove the parabreaks between heading and now so consolidate
                # doesn't insert spurious paragraph breaks
                del blocks[last_heading_block_idx + 1:]
                continue
            last_heading_block_idx = None
            if kt == 'caption':
                fig_num, caption = kind[1]
                if fig_num not in inserted_figs:
                    blocks.append((current_section, 'figure', {
                        'number': fig_num,
                        'caption': fix_text(caption),
                    }))
                    inserted_figs.add(fig_num)
            elif kt == 'bullet':
                lvl, text = kind[1]
                blocks.append((current_section, 'bullet', {
                    'level': lvl,
                    'text': fix_text(text),
                }))
            elif kt == 'numbered':
                blocks.append((current_section, 'numbered', fix_text(kind[1])))
            elif kt == 'code':
                blocks.append((current_section, 'code', kind[1]))
            elif kt in ('italic_small', 'italic_body'):
                blocks.append((current_section, 'italic', fix_text(kind[1])))
            elif kt == 'bold_small':
                blocks.append((current_section, 'bold_small', fix_text(kind[1])))
            elif kt == 'inline_label':
                # A bold (often italic) label like "Data Needs:" or "Objective:"
                # appearing inline; title-case the all-caps text
                text = fix_text(kind[1])
                # Title-case if mostly upper
                if text and sum(1 for c in text if c.isupper()) > len(text) / 2:
                    text = title_case_heading(text)
                blocks.append((current_section, 'inline_label', text))
            elif kt == 'body':
                # kind = ('body', text, x0)
                x0 = kind[2] if len(kind) > 2 else None
                blocks.append((current_section, 'body', {
                    'text': fix_text(kind[1]),
                    'x0': x0,
                }))
        # Drain any uncaptioned figures left on this page (after all lines)
        while uncap_idx < len(pending_uncap):
            fig_info = pending_uncap[uncap_idx]
            fig_num = fig_info['fig_num']
            if fig_num not in inserted_figs:
                blocks.append((current_section, 'figure', {
                    'number': fig_num,
                    'caption': '',
                }))
                inserted_figs.add(fig_num)
            uncap_idx += 1
    return blocks


def consolidate(blocks):
    out = []
    buf_kind = None
    buf_items = []
    bullet_items = []  # list of [level, text, indent_x0]
    numbered_items = []
    current_sec = None

    def flush():
        nonlocal buf_kind, buf_items, bullet_items, numbered_items
        if buf_items:
            joined = ' '.join(buf_items).strip()
            joined = re.sub(r'\s+', ' ', joined)
            # Fix hyphenated word splits that survived line joining
            joined = re.sub(r'(\w)-\s+(\w)', r'\1-\2', joined)
            if buf_kind == 'body' and joined:
                out.append((current_sec, 'paragraph', joined))
            elif buf_kind == 'italic' and joined:
                out.append((current_sec, 'italic_note', joined))
            elif buf_kind == 'code':
                out.append((current_sec, 'code_block', '\n'.join(buf_items)))
            buf_items = []
            buf_kind = None
        if bullet_items:
            cleaned = []
            for lvl, txt, _ in bullet_items:
                txt = re.sub(r'(\w)-\s+(\w)', r'\1-\2', txt)
                cleaned.append((lvl, txt))
            out.append((current_sec, 'bullet_list', cleaned))
            bullet_items = []
        if numbered_items:
            cleaned_num = [re.sub(r'(\w)-\s+(\w)', r'\1-\2', t) for t in numbered_items]
            out.append((current_sec, 'numbered_list', cleaned_num))
            numbered_items = []

    for sec, kind, payload in blocks:
        if kind == 'parabreak':
            if buf_kind in ('body', 'italic'):
                flush()
            continue
        if sec != current_sec and kind != 'heading':
            flush()
            current_sec = sec
        if kind == 'heading':
            flush()
            current_sec = sec
            out.append((sec, 'heading', payload))
        elif kind == 'figure':
            flush()
            out.append((sec, 'figure', payload))
        elif kind == 'body':
            text = payload['text'] if isinstance(payload, dict) else payload
            x0 = payload['x0'] if isinstance(payload, dict) else None
            # If we have an active bullet list and this body line is indented
            # at the bullet text indent, treat as continuation of the last bullet.
            if bullet_items and x0 is not None:
                last_indent = bullet_items[-1][2]
                # Bullet text starts ~18 pt past bullet glyph (108 vs 90, or 144 vs 126)
                if last_indent is not None:
                    expected_continuation = last_indent + 14  # text-of-bullet x0
                    if abs(x0 - expected_continuation) < 6:
                        # Append to last bullet's text
                        lvl, txt, ind = bullet_items[-1]
                        bullet_items[-1] = (lvl, txt + ' ' + text, ind)
                        continue
            if buf_kind != 'body':
                flush()
                buf_kind = 'body'
            buf_items.append(text)
        elif kind == 'italic':
            if buf_kind != 'italic':
                flush()
                buf_kind = 'italic'
            buf_items.append(payload)
        elif kind == 'code':
            if buf_kind != 'code':
                flush()
                buf_kind = 'code'
            buf_items.append(payload)
        elif kind == 'bullet':
            if buf_kind:
                flush()
            # payload: {'level': lvl, 'text': text} - we lost x0; reconstruct from level
            # bullet glyph at x0: level 1 -> 90, level 2 -> 126
            ind_guess = 90 if payload['level'] == 1 else 126 if payload['level'] == 2 else 144
            bullet_items.append((payload['level'], payload['text'], ind_guess))
            numbered_items = []
        elif kind == 'numbered':
            if buf_kind:
                flush()
            numbered_items.append(payload)
            bullet_items = []
        elif kind == 'bold_small':
            if buf_kind != 'body':
                flush()
                buf_kind = 'body'
            buf_items.append(f"**{payload}**")
        elif kind == 'inline_label':
            # Treat as its own bold paragraph (like a sub-heading without number)
            flush()
            out.append((current_sec, 'inline_label', payload))
    flush()
    return out


def to_markdown(consolidated):
    section_titles = {n: title for n, _slug, title in TOP_SECTIONS}
    sections = {n: [] for n in range(1, 10)}
    for sec, kind, payload in consolidated:
        if sec is None or sec not in sections:
            continue
        target = sections[sec]
        if kind == 'heading':
            level = payload['level']
            num = payload['number']
            text = payload['text']
            if level == 1:
                # Use the canonical title from TOP_SECTIONS, which preserves
                # things like "(Qvf)" that the math-font extraction loses.
                text = section_titles.get(int(num), text)
                target.append(f"# {num} {text}\n")
            else:
                md_hashes = '#' * min(level, 6)
                target.append(f"\n{md_hashes} {num} {text}\n")
        elif kind == 'figure':
            num = payload['number']
            cap = payload['caption']
            # Captioned figures (1-65) come from the source PDF's "Figure N"
            # labels. Uncaptioned figures (66+) were extracted positionally and
            # rendered as plain inline images without a "Figure N" label.
            if num <= 65:
                cap_part = (": " + cap) if cap else "."
                target.append(
                    f"\n![Figure {num}](../figures/figure_{num:02d}.png)\n"
                    f"\n<small>**Figure {num}**{cap_part}</small>\n"
                )
            else:
                target.append(
                    f"\n![](../figures/figure_{num:02d}.png)\n"
                )
        elif kind == 'paragraph':
            # Skip dangling H1 wrap fragments — lines that look like a code
            # identifier wrap with many underscores and ALL-CAPS fragments
            text = payload
            if re.match(r'^[A-Z_0-9.\s()]+\)?$', text) and ('_' in text) and len(text) < 100:
                continue
            target.append(text + "\n")
        elif kind == 'inline_label':
            text = payload
            # Skip dangling H1 wrap fragments (same filter as paragraph)
            if re.match(r'^[A-Za-z_0-9.\s()]+\)?$', text) and ('_' in text) and len(text) < 100:
                # Heuristic: lots of single-char or 2-char tokens between underscores
                tokens = re.split(r'[_\s]+', text)
                short_tokens = sum(1 for t in tokens if 0 < len(t) <= 3)
                if short_tokens >= 3:
                    continue
            target.append(f"**{payload}**\n")
        elif kind == 'italic_note':
            target.append(f"\n!!! note\n    {payload}\n")
        elif kind == 'code_block':
            target.append(f"\n```python\n{payload}\n```\n")
        elif kind == 'bullet_list':
            lines = []
            for lvl, text in payload:
                indent = '    ' * (lvl - 1)
                lines.append(f"{indent}- {text}")
            target.append('\n'.join(lines) + '\n')
        elif kind == 'numbered_list':
            lines = [f"{i+1}. {t}" for i, t in enumerate(payload)]
            target.append('\n'.join(lines) + '\n')
    return {n: '\n'.join(parts) for n, parts in sections.items()}


def main():
    with pdfplumber.open(PDF) as pdf:
        raw = parse_pdf(pdf)
        cons = consolidate(raw)
        md = to_markdown(cons)
        for n, slug, title in TOP_SECTIONS:
            content = md.get(n, '').strip() + '\n'
            if len(content) < 50:
                content = f"# {n} {title}\n\n*(Section content unavailable)*\n"
            out_path = SECTIONS_DIR / f"{slug}.md"
            out_path.write_text(content)
            print(f"Wrote {out_path} ({len(content):,} chars)")


if __name__ == "__main__":
    main()
