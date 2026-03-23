#!/usr/bin/env python3
"""Convert Habitat documentation files (troff/nroff and plain text) to HTML.
Handles all subdirectories: admin/, archives/, cya/, hotlist/, notes/, system/, worldgen/
"""

import os
import re
import html
import sys
import json

RAW_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "raw")
HTML_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "html")

CSS = """
body {
    font-family: Georgia, 'Times New Roman', serif;
    max-width: 800px;
    margin: 40px auto;
    padding: 0 20px;
    line-height: 1.7;
    color: #1a1a1a;
    background: #fafaf8;
}
h1 { font-size: 1.8em; border-bottom: 2px solid #8b4513; padding-bottom: 8px; color: #3c2415; }
h2 { font-size: 1.4em; color: #5a3520; margin-top: 1.5em; border-bottom: 1px solid #d4c4b0; padding-bottom: 4px; }
h3 { font-size: 1.15em; color: #6b4226; margin-top: 1.2em; }
h4 { font-size: 1.05em; color: #7a5533; }
pre {
    background: #f0ebe4; border: 1px solid #d4c4b0;
    padding: 12px 16px; overflow-x: auto;
    font-size: 0.9em; line-height: 1.5; border-radius: 4px;
}
code { background: #f0ebe4; padding: 2px 5px; border-radius: 3px; font-size: 0.9em; }
.author { font-style: italic; color: #666; margin-bottom: 0.5em; }
.institution { color: #888; margin-bottom: 1em; }
.date { color: #888; margin-bottom: 2em; }
.doc-number { color: #8b4513; font-weight: bold; }
.nav { margin: 20px 0; }
.nav a { color: #8b4513; text-decoration: none; }
.nav a:hover { text-decoration: underline; }
a { color: #8b4513; }
ul.bullet { list-style-type: disc; margin-left: 1.5em; }
ul.bullet li { margin-bottom: 0.5em; }
.page-break { border-top: 2px dashed #ccc; margin: 2em 0; padding-top: 0.5em; color: #999; font-size: 0.85em; }
table { border-collapse: collapse; margin: 1em 0; width: 100%; }
th, td { border: 1px solid #d4c4b0; padding: 6px 10px; text-align: left; }
th { background: #f0ebe4; }
.fortune { padding: 8px 12px; margin: 4px 0; background: #f8f5f0; border-left: 3px solid #8b4513; }
"""


GITHUB_BASE = "https://github.com/Museum-of-Art-and-Digital-Entertainment/habitat/blob/b59e2520fd8690bf99a1db43928a679f2fbc875c/chip/habitat/docs/"


def html_page(title, body, back_href="index.html", source_path=""):
    source_link = ""
    if source_path:
        url = GITHUB_BASE + source_path
        source_link = f' &middot; <a href="{url}" style="font-size:0.85em;">View source</a>'
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html.escape(title)} - Habitat Documentation</title>
<style>{CSS}</style>
</head>
<body>
<div class="nav"><a href="{back_href}">&larr; Back to Table of Contents</a>{source_link}</div>
{body}
<div class="nav" style="margin-top:3em; border-top:1px solid #ddd; padding-top:1em;">
<a href="{back_href}">&larr; Back to Table of Contents</a>{source_link}
</div>
</body>
</html>
"""


def clean_troff_inline(text):
    """Process troff inline formatting on RAW text (before html.escape).
    Returns text with HTML tags for formatting, HTML-escaped content."""
    t = text

    # String interpolations
    t = t.replace("\\*(Dq", "")
    t = t.replace("\\*(T", "\u2122")
    t = t.replace("\\*M", "\u2122")
    t = re.sub(r"\\\*\((.{2})", "", t)
    t = re.sub(r"\\\*(.)", "", t)

    # Size changes \s+N ... \s-N — remove them
    t = re.sub(r"\\s[+-]?\d+", "", t)

    # Special characters (must be before general \( cleanup)
    SPECIAL_CHARS = {
        "\\(em": "\u2014", "\\(en": "\u2013", "\\(bu": "\u2022",
        "\\(ct": "\u00a2", "\\(lq": "\u201c", "\\(rq": "\u201d",
        "\\(dg": "\u2020", "\\(sq": "\u25a1", "\\(->": "\u2192",
        "\\(<-": "\u2190", "\\(>=": "\u2265", "\\(<=": "\u2264",
        "\\(!=": "\u2260", "\\(aa": "\u00b4", "\\(ga": "`",
        "\\(mi": "\u2212", "\\(pl": "+", "\\(mu": "\u00d7",
        "\\(di": "\u00f7", "\\(de": "\u00b0", "\\(co": "\u00a9",
        "\\(rg": "\u00ae", "\\(tm": "\u2122",
    }
    for seq, repl in SPECIAL_CHARS.items():
        t = t.replace(seq, repl)
    t = re.sub(r"\\\((.{2})", "", t)  # remaining unknown \(XX

    # Escaped characters
    t = t.replace("\\-", "-")
    t = t.replace("\\&", "")
    t = t.replace("\\e", "\\")
    t = t.replace("\\`", "`")
    t = t.replace("\\'", "'")
    t = t.replace("\\~", "\u00a0")
    t = t.replace("\\0", "\u00a0")

    # Motions and measurements — remove
    t = re.sub(r"\\v'[^']*'", "", t)
    t = re.sub(r"\\h'[^']*'", "", t)
    t = re.sub(r"\\w'[^']*'", "", t)
    t = re.sub(r"\\l'[^']*'", "", t)  # horizontal line drawing
    t = re.sub(r"\\k.", "", t)  # mark position

    # Quotes
    t = t.replace("``", "\u201c").replace("''", "\u201d")

    # Now handle font changes with a state machine
    # Split on font switches, tracking current font
    # Single-char font names
    FONT_MAP = {
        'I': ('em',),      # italic
        'B': ('b',),       # bold
        'C': ('code',),    # constant-width
        'H': ('code',),    # Helvetica (treat as code)
        'L': ('code',),    # literal (treat as code)
        'R': (),            # roman (default)
        'P': (),            # previous (treat as default)
    }
    # Two-char font names \f(XX
    FONT_MAP_2 = {
        'BI': ('b', 'em'),      # bold-italic
        'IB': ('em', 'b'),      # italic-bold
        'CB': ('code', 'b'),    # constant-width bold
        'CI': ('code', 'em'),   # constant-width italic
        'CW': ('code',),        # constant-width
        'HD': ('b',),           # Helvetica bold (treat as bold)
    }

    # Split on both \f(XX and \fX font switches
    parts = re.split(r'(\\f\([A-Z]{2}|\\f[A-Z])', t)
    result = []
    current_tags = []  # stack of open tags
    for part in parts:
        # Two-char font: \f(XX
        m2 = re.match(r'^\\f\(([A-Z]{2})$', part)
        # Single-char font: \fX
        m1 = re.match(r'^\\f([A-Z])$', part)
        if m2:
            # Close all current tags (reverse order)
            for tag in reversed(current_tags):
                result.append(f'</{tag}>')
            new_tags = list(FONT_MAP_2.get(m2.group(1), ()))
            for tag in new_tags:
                result.append(f'<{tag}>')
            current_tags = new_tags
        elif m1:
            for tag in reversed(current_tags):
                result.append(f'</{tag}>')
            new_tags = list(FONT_MAP.get(m1.group(1), ()))
            for tag in new_tags:
                result.append(f'<{tag}>')
            current_tags = new_tags
        else:
            result.append(html.escape(part))
    # Close any remaining open tags
    for tag in reversed(current_tags):
        result.append(f'</{tag}>')

    t = ''.join(result)

    # Clean up escaped backslashes that remain
    t = t.replace("\\\\", "\\")
    # Remove any remaining \X sequences we didn't handle
    t = re.sub(r'\\[a-z]', '', t)

    return t


def clean_troff_pre(text):
    """Clean troff formatting from pre/display blocks. Preserves whitespace."""
    lines = text.split('\n')
    cleaned = []
    for line in lines:
        cleaned.append(clean_troff_inline(line))
    return '\n'.join(cleaned)


def troff_body_to_text(text_content):
    """Convert raw troff text to HTML with formatting. Handles escaping internally."""
    return clean_troff_inline(text_content)


def convert_troff(text, filename=""):
    lines = text.split('\n')
    out = []
    title = ""
    author = ""
    institution = ""
    date_str = ""
    doc_number = ""
    in_list = False
    in_display = False
    display_buf = []
    string_defs = {}

    # First pass: metadata
    i = 0
    while i < len(lines):
        line = lines[i]
        m = re.match(r'\.ds\s+(\S+)\s+(.*)', line)
        if m:
            string_defs[m.group(1)] = m.group(2).strip()
        if line.startswith('.TL'):
            i += 1
            parts = []
            while i < len(lines) and not lines[i].startswith('.'):
                t = lines[i].strip()
                if t:
                    parts.append(clean_troff_inline(t))
                i += 1
            title = ' '.join(parts)
            continue
        elif line.startswith('.AU'):
            i += 1
            parts = []
            while i < len(lines) and not lines[i].startswith('.'):
                t = lines[i].strip()
                if t and t.lower() != 'by':
                    parts.append(clean_troff_inline(t))
                i += 1
            author = ', '.join(parts)
            continue
        elif line.startswith('.AI'):
            i += 1
            parts = []
            while i < len(lines) and not lines[i].startswith('.'):
                t = lines[i].strip()
                if t:
                    c = clean_troff_inline(t).strip().strip('\\').strip()
                    if c:
                        parts.append(c)
                i += 1
            institution = ', '.join(parts)
            continue
        i += 1

    date_str = string_defs.get('Dq', '')
    for key, val in string_defs.items():
        if 'Document' in val or 'document' in val:
            doc_number = clean_troff_inline(val)

    if title:
        out.append(f'<h1>{title}</h1>')
    if author:
        out.append(f'<p class="author">by {author}</p>')
    if institution:
        out.append(f'<p class="institution">{institution}</p>')
    if date_str:
        out.append(f'<p class="date">{date_str}</p>')
    if doc_number:
        out.append(f'<p class="doc-number">{doc_number}</p>')

    # Second pass: body
    i = 0
    while i < len(lines):
        line = lines[i]

        if re.match(r'\.(AM|lg|nr|na|ad|fi|nf|ne|sp|bp|br|in|ti|ta|ce|ul|cu|mk|rt|fc|ec|eo|em|rm|rn|di|da|wh|ch|it|nm|nn|af|ev|ex|pm|fl|ab|lf|nx|pi|rd|so|sy|tr|hy|nh|ll|pl|po|ps|vs|ft)\b', line):
            if line.startswith('.nf'):
                in_display = True
                display_buf = []
            elif line.startswith('.fi'):
                if in_display and display_buf:
                    out.append('<pre>' + clean_troff_pre('\n'.join(display_buf)) + '</pre>')
                    display_buf = []
                in_display = False
            elif line.startswith('.sp'):
                out.append('<br>')
            elif line.startswith('.bp'):
                out.append('<hr>')
            elif line.startswith('.ce'):
                m2 = re.match(r'\.ce\s*(\d*)', line)
                count = int(m2.group(1)) if m2.group(1) else 1
                for _ in range(count):
                    i += 1
                    if i < len(lines):
                        out.append(f'<p style="text-align:center">{clean_troff_inline(lines[i])}</p>')
            i += 1
            continue

        if re.match(r'\.ds\b', line):
            i += 1
            continue

        if line.startswith('.TL') or line.startswith('.AU') or line.startswith('.AI'):
            i += 1
            while i < len(lines) and not lines[i].startswith('.'):
                i += 1
            continue

        m = re.match(r'\.(SH|NH)\s*(.*)', line)
        if m:
            cmd = m.group(1)
            rest = m.group(2).strip()
            if in_list:
                out.append('</ul>')
                in_list = False
            heading_text = ""
            if rest and not rest[0].isdigit():
                heading_text = rest
            else:
                i += 1
                if i < len(lines):
                    heading_text = lines[i].strip()
            heading_text = clean_troff_inline(heading_text)
            heading_text = re.sub(r'^\d+(\.\d+)*\s*', '', heading_text)
            tag = 'h2'
            if cmd == 'NH':
                level_m = re.match(r'(\d+)', rest) if rest else None
                level = int(level_m.group(1)) if level_m else 1
                tag = f'h{min(level + 1, 4)}'
            if heading_text:
                out.append(f'<{tag}>{heading_text}</{tag}>')
            i += 1
            continue

        if line.startswith('.SS'):
            rest = line[3:].strip()
            if not rest:
                i += 1
                if i < len(lines):
                    rest = lines[i].strip()
            out.append(f'<h3>{clean_troff_inline(rest)}</h3>')
            i += 1
            continue

        if line.startswith('.PP') or line.startswith('.LP') or line.startswith('.XP'):
            if in_list:
                out.append('</ul>')
                in_list = False
            i += 1
            para = []
            while i < len(lines) and not lines[i].startswith('.'):
                para.append(lines[i])
                i += 1
            if para:
                t = ' '.join(l.strip() for l in para if l.strip())
                out.append(f'<p>{troff_body_to_text(t)}</p>')
            continue

        m = re.match(r'\.IP\s*(.*)', line)
        if m:
            label = m.group(1).strip().strip('"')
            if not in_list:
                out.append('<ul class="bullet">')
                in_list = True
            i += 1
            items = []
            while i < len(lines) and not lines[i].startswith('.'):
                items.append(lines[i])
                i += 1
            t = ' '.join(l.strip() for l in items if l.strip())
            t = troff_body_to_text(t)
            label = re.sub(r'[\\\ ]*\(bu[\\\ ]*', '', label).strip()
            if label:
                out.append(f'<li><b>{clean_troff_inline(label)}</b> {t}</li>')
            else:
                out.append(f'<li>{t}</li>')
            continue

        if line.startswith('.DS') or line.startswith('.LD') or line.startswith('.ID') or line.startswith('.CD'):
            in_display = True
            display_buf = []
            i += 1
            continue
        if line.startswith('.DE'):
            if display_buf:
                out.append('<pre>' + clean_troff_pre('\n'.join(display_buf)) + '</pre>')
                display_buf = []
            in_display = False
            i += 1
            continue

        if line.startswith('.TS'):
            i += 1
            table_data = []
            fmt_done = False
            while i < len(lines):
                if lines[i].startswith('.TE'):
                    break
                if not fmt_done:
                    if lines[i].strip().endswith('.') or lines[i].strip().endswith(';'):
                        fmt_done = True
                        i += 1
                        continue
                    if '\t' in lines[i]:
                        fmt_done = True
                        table_data.append(lines[i])
                else:
                    table_data.append(lines[i])
                i += 1
            if table_data:
                out.append('<table>')
                for ri, row in enumerate(table_data):
                    cells = row.split('\t')
                    tag = 'th' if ri == 0 else 'td'
                    out.append('<tr>' + ''.join(f'<{tag}>{clean_troff_inline(c.strip())}</{tag}>' for c in cells) + '</tr>')
                out.append('</table>')
            i += 1
            continue

        if line.startswith('.EQ'):
            i += 1
            while i < len(lines) and not lines[i].startswith('.EN'):
                i += 1
            i += 1
            continue

        if line.startswith('.de'):
            i += 1
            while i < len(lines) and not lines[i].startswith('..'):
                i += 1
            i += 1
            continue

        if line.startswith('.KS') or line.startswith('.KE') or line.startswith('.KF'):
            i += 1
            continue

        if in_display:
            display_buf.append(line)
            i += 1
            continue

        if line.startswith('.'):
            i += 1
            continue

        if line.strip():
            para = []
            while i < len(lines) and not lines[i].startswith('.') and lines[i].strip():
                para.append(lines[i])
                i += 1
            if para:
                t = ' '.join(l.strip() for l in para)
                out.append(f'<p>{troff_body_to_text(t)}</p>')
            continue

        i += 1

    if in_list:
        out.append('</ul>')
    if in_display and display_buf:
        out.append('<pre>' + clean_troff_pre('\n'.join(display_buf)) + '</pre>')

    return title or filename, '\n'.join(out)


def convert_plaintext(text, filename=""):
    lines = text.split('\n')
    out = []
    title = ""

    for line in lines[:5]:
        s = line.strip()
        if s and not s.startswith('#') and len(s) < 120:
            title = s
            break

    if title:
        out.append(f'<h1>{html.escape(title)}</h1>')

    i = 0
    in_pre = False
    pre_buf = []

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if stripped.startswith('####'):
            if in_pre and pre_buf:
                out.append('<pre>' + html.escape('\n'.join(pre_buf)) + '</pre>')
                pre_buf = []
                in_pre = False
            m = re.search(r'page\s+(\d+)', stripped)
            if m:
                out.append(f'<div class="page-break">Page {m.group(1)}</div>')
            i += 1
            continue

        if stripped and len(stripped) < 80:
            leading = len(line) - len(line.lstrip())
            if leading >= 3 and len(stripped) < 60:
                if i + 1 < len(lines) and not lines[i + 1].strip():
                    if in_pre and pre_buf:
                        out.append('<pre>' + html.escape('\n'.join(pre_buf)) + '</pre>')
                        pre_buf = []
                        in_pre = False
                    if stripped == stripped.upper() and len(stripped) > 3:
                        out.append(f'<h2>{html.escape(stripped)}</h2>')
                    elif leading >= 8:
                        out.append(f'<h2>{html.escape(stripped)}</h2>')
                    else:
                        out.append(f'<h3>{html.escape(stripped)}</h3>')
                    i += 1
                    continue

            if stripped.endswith(':') and stripped == stripped.upper() and len(stripped) > 5:
                if in_pre and pre_buf:
                    out.append('<pre>' + html.escape('\n'.join(pre_buf)) + '</pre>')
                    pre_buf = []
                    in_pre = False
                out.append(f'<h3>{html.escape(stripped)}</h3>')
                i += 1
                continue

        if line.startswith('\t') or (line.startswith('    ') and stripped):
            if not in_pre:
                in_pre = True
                pre_buf = []
            pre_buf.append(line)
            i += 1
            continue

        if in_pre and pre_buf and not line.startswith('\t') and not line.startswith('    '):
            out.append('<pre>' + html.escape('\n'.join(pre_buf)) + '</pre>')
            pre_buf = []
            in_pre = False

        if not stripped:
            i += 1
            continue

        para = []
        while i < len(lines):
            s = lines[i].strip()
            if not s:
                break
            if lines[i].startswith('\t') or lines[i].startswith('    '):
                break
            if s.startswith('####'):
                break
            para.append(s)
            i += 1
        if para:
            out.append(f'<p>{html.escape(" ".join(para))}</p>')
        continue

    if in_pre and pre_buf:
        out.append('<pre>' + html.escape('\n'.join(pre_buf)) + '</pre>')

    return title, '\n'.join(out)


def convert_fortunes(text):
    out = ['<h1>Habitat Fortune Cookie Messages</h1>',
           '<p>Fortune messages dispensed by the Oracle and FortuneDroid in the Habitat world.</p>']
    for line in text.strip().split('\n'):
        line = line.strip()
        if line:
            out.append(f'<div class="fortune">{html.escape(line)}</div>')
    return "Habitat Fortune Cookies", '\n'.join(out)


def convert_survey(text, filename=""):
    """Convert Habitat survey response files (q*.pre, q*.post, summary)."""
    lines = text.split('\n')
    out = []

    # Extract question number from filename
    m = re.search(r'q(\d+)\.(pre|post)', filename)
    if m:
        qnum = int(m.group(1))
        phase = "Pre-Test" if m.group(2) == 'pre' else "Post-Test"
        title = f"Survey Question {qnum} ({phase})"
    elif 'summary' in filename:
        title = "Survey Results Summary"
    else:
        title = f"Survey: {filename}"

    out.append(f'<h1>{html.escape(title)}</h1>')

    # Skip the %cvideo header line
    i = 0
    if i < len(lines) and lines[i].startswith('%'):
        # Extract timestamp
        m2 = re.search(r'(\d{2}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\s+\w+)', lines[i])
        if m2:
            out.append(f'<p class="date">Collected: {html.escape(m2.group(1))}</p>')
        i += 1

    # For summary file, use a different approach
    if 'summary' in filename:
        # Summary has structured Q&A with tables — use plain text with pre for tables
        para = []
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()

            # Question headers
            qm = re.match(r'^(QUESTION\s+\d+):', stripped)
            if qm:
                if para:
                    out.append(f'<p>{html.escape(" ".join(para))}</p>')
                    para = []
                out.append(f'<h2>{html.escape(qm.group(1))}</h2>')
                i += 1
                continue

            # Table-like lines (contain tabs or dashes as separators)
            if '\t' in line or re.match(r'^-{5,}', stripped):
                if para:
                    out.append(f'<p>{html.escape(" ".join(para))}</p>')
                    para = []
                # Collect table block
                table_lines = []
                while i < len(lines):
                    l = lines[i]
                    if not l.strip() and table_lines:
                        break
                    if '\t' in l or re.match(r'^-{3,}', l.strip()) or (table_lines and l.startswith(' ')):
                        table_lines.append(l)
                    elif table_lines:
                        break
                    else:
                        break
                    i += 1
                if table_lines:
                    out.append('<pre>' + html.escape('\n'.join(table_lines)) + '</pre>')
                continue

            # "Comments" section headers
            if stripped.startswith('Comments'):
                if para:
                    out.append(f'<p>{html.escape(" ".join(para))}</p>')
                    para = []
                out.append(f'<h3>{html.escape(stripped)}</h3>')
                i += 1
                continue

            # "From:" response in summary
            fm = re.match(r'^From:\s+(.+)', stripped)
            if fm:
                if para:
                    out.append(f'<p>{html.escape(" ".join(para))}</p>')
                    para = []
                responder = fm.group(1)
                i += 1
                resp_lines = []
                while i < len(lines):
                    s = lines[i].strip()
                    if s.startswith('- - - ') or s.startswith('From:') or re.match(r'^QUESTION\s+\d+', s):
                        break
                    resp_lines.append(s)
                    i += 1
                resp_text = ' '.join(l for l in resp_lines if l)
                out.append(f'<div style="margin:0.8em 0; padding:8px 12px; background:#f8f5f0; border-left:3px solid #8b4513; border-radius:0 4px 4px 0;">')
                out.append(f'<div style="font-weight:bold; color:#5a3520; margin-bottom:4px;">{html.escape(responder)}</div>')
                if resp_text:
                    out.append(f'<div>{html.escape(resp_text)}</div>')
                out.append('</div>')
                # Skip separator
                if i < len(lines) and lines[i].strip().startswith('- - -'):
                    i += 1
                continue

            # Separator
            if stripped.startswith('- - -'):
                i += 1
                continue

            # Empty
            if not stripped:
                if para:
                    out.append(f'<p>{html.escape(" ".join(para))}</p>')
                    para = []
                i += 1
                continue

            para.append(stripped)
            i += 1

        if para:
            out.append(f'<p>{html.escape(" ".join(para))}</p>')
        return title, '\n'.join(out)

    # For q*.pre and q*.post files: parse question + individual responses
    # Skip blank lines
    while i < len(lines) and not lines[i].strip():
        i += 1

    # Parse question text (for .pre files, question comes first)
    question_text = []
    choices = []
    in_question = False

    if i < len(lines) and lines[i].strip().startswith('QUESTION'):
        i += 1  # skip "QUESTION:" line
        # Gather question text until blank line
        while i < len(lines) and lines[i].strip():
            question_text.append(lines[i].strip())
            i += 1
        # Skip blank
        while i < len(lines) and not lines[i].strip():
            i += 1
        # Gather choices until blank line or separator
        while i < len(lines):
            s = lines[i].strip()
            if not s or s.startswith('- - -') or s.startswith('Mail'):
                break
            choices.append(s)
            i += 1

    if question_text:
        out.append(f'<div style="background:#f0ebe4; border:1px solid #d4c4b0; border-radius:6px; padding:14px 18px; margin:1em 0;">')
        out.append(f'<div style="font-weight:bold; margin-bottom:8px;">Question:</div>')
        out.append(f'<p style="margin:0;">{html.escape(" ".join(question_text))}</p>')
        if choices:
            out.append('<ul style="margin:8px 0 0 0;">')
            for c in choices:
                out.append(f'<li>{html.escape(c)}</li>')
            out.append('</ul>')
        out.append('</div>')

    # Parse responses: separated by "- - - -" lines
    # Each response block: "Mail to: ...", "Mail From: ...", optional "Date: ...", then response text
    out.append(f'<h2>Responses</h2>')
    response_count = 0

    while i < len(lines):
        line = lines[i].strip()

        # Skip separators and blank lines
        if not line or line.startswith('- - -'):
            i += 1
            continue

        # Parse a response block
        resp_from = ""
        resp_date = ""
        resp_lines = []

        # Look for Mail headers
        if line.startswith('Mail to:'):
            i += 1
            if i < len(lines) and lines[i].strip().startswith('Mail From:'):
                m3 = re.match(r'Mail From:\s+(.+)', lines[i].strip())
                if m3:
                    resp_from = m3.group(1).strip()
                i += 1
            if i < len(lines) and lines[i].strip().startswith('Date:'):
                m4 = re.match(r'Date:\s+(.+)', lines[i].strip())
                if m4:
                    resp_date = m4.group(1).strip()
                i += 1
            # Gather response text until separator or next Mail block
            while i < len(lines):
                s = lines[i].strip()
                if s.startswith('- - -') or s.startswith('Mail to:'):
                    break
                if s and s != '.':
                    resp_lines.append(s)
                i += 1

            resp_text = ' '.join(resp_lines)
            response_count += 1

            out.append(f'<div style="margin:0.5em 0; padding:6px 12px; background:#f8f5f0; border-left:3px solid #8b4513; border-radius:0 4px 4px 0;">')
            out.append(f'<span style="font-weight:bold; color:#5a3520;">{html.escape(resp_from)}</span>')
            if resp_date:
                out.append(f' <span style="color:#999; font-size:0.85em;">{html.escape(resp_date)}</span>')
            if resp_text:
                out.append(f'<div style="margin-top:2px;">{html.escape(resp_text)}</div>')
            out.append('</div>')
        else:
            i += 1

    if response_count:
        out.insert(-0, '')  # no-op, count is already visible
        # Add count after the Responses heading
        for idx, line in enumerate(out):
            if 'Responses</h2>' in line:
                out[idx] = f'<h2>Responses ({response_count})</h2>'
                break

    return title, '\n'.join(out)


def is_survey(text, filename=""):
    """Check if file is a survey response file."""
    basename = os.path.basename(filename)
    # Match q01.pre, q01.post, summary
    if re.match(r'^q\d+\.(pre|post)$', basename):
        return True
    if basename == 'summary' and 'survey' in filename:
        return True
    # Check content pattern
    if text.lstrip().startswith('%cvideo'):
        return True
    return False


def convert_region_text(text, filename=""):
    """Convert .rt region text files (in-game text hard-wrapped at ~40 chars)."""
    lines = text.split('\n')
    out = []
    title = ""

    # Extract title from first non-empty line
    for line in lines[:5]:
        s = line.strip()
        if s and not s.startswith('#') and not s.startswith('--'):
            title = s
            break

    if title:
        out.append(f'<h1>{html.escape(title)}</h1>')

    # Reflow: join consecutive non-empty lines into paragraphs,
    # treating page breaks and centered/dashed headings specially
    i = 0
    para = []

    def flush_para():
        if para:
            out.append(f'<p>{html.escape(" ".join(para))}</p>')
            para.clear()

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Page separator: "###...### page N" or "-- page --" or "-- Page N of M --"
        if stripped.startswith('####') or re.match(r'^--\s*page\s*--$', stripped, re.I):
            flush_para()
            m = re.search(r'page\s+(\d+)', stripped)
            if m:
                out.append(f'<div class="page-break">Page {m.group(1)}</div>')
            i += 1
            continue

        # Page number line: "-- Page N of M --"
        m = re.match(r'^\s*--\s*Page\s+(\d+)\s+of\s+(\d+)\s*--\s*$', stripped)
        if m:
            flush_para()
            i += 1
            continue

        # Heading-like lines: dashes surrounding text, or ALL CAPS centered
        m = re.match(r'^-{2,}(.+?)-{2,}$', stripped)
        if m:
            flush_para()
            heading = m.group(1).strip()
            out.append(f'<h2>{html.escape(heading)}</h2>')
            i += 1
            continue

        # Centered heading (lots of leading space, short text, followed by blank)
        leading = len(line) - len(line.lstrip())
        if leading >= 5 and len(stripped) < 50 and stripped == stripped.upper() and len(stripped) > 3:
            if i + 1 >= len(lines) or not lines[i + 1].strip():
                flush_para()
                out.append(f'<h3>{html.escape(stripped)}</h3>')
                i += 1
                continue

        # Empty line = paragraph break
        if not stripped:
            flush_para()
            i += 1
            continue

        # Regular text line — accumulate for reflow
        para.append(stripped)
        i += 1

    flush_para()
    return title, '\n'.join(out)


def is_region_text(text, filename=""):
    """Check if file is a .rt region text file."""
    return filename.endswith('.rt')


def is_email(text):
    """Check if text looks like an email or mbox file."""
    lines = text.lstrip('\n').split('\n')
    if not lines:
        return False
    first = lines[0]
    # mbox "From " line
    if re.match(r'^From \S+.*\d{4}', first):
        return True
    # Direct headers
    header_count = 0
    for line in lines[:10]:
        if re.match(r'^(From|To|Subject|Date|Cc|Received|Return-Path|Message-Id|Status):\s', line):
            header_count += 1
    return header_count >= 2


def parse_email_headers(lines, start=0):
    """Parse email headers starting at line index. Returns (headers_dict, body_start_index)."""
    headers = {}
    i = start
    # Skip mbox "From " envelope line
    if i < len(lines) and lines[i].startswith('From '):
        # Extract date from mbox line
        m = re.search(r'(Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+(.*\d{4})', lines[i])
        if m:
            headers['_mbox_date'] = m.group(0)
        i += 1
    # Parse RFC822-style headers
    current_key = None
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
            break
        # Continuation line (starts with whitespace)
        if line[0] in (' ', '\t') and current_key:
            headers[current_key] += ' ' + line.strip()
        else:
            m = re.match(r'^([\w-]+):\s*(.*)', line)
            if m:
                current_key = m.group(1)
                val = m.group(2).strip()
                if current_key in headers:
                    headers[current_key] += ', ' + val
                else:
                    headers[current_key] = val
            else:
                # Not a header line — this is body
                break
        i += 1
    return headers, i


def convert_email(text, filename=""):
    """Convert email/mbox format to HTML."""
    lines = text.split('\n')
    # Skip leading blank lines
    start = 0
    while start < len(lines) and not lines[start].strip():
        start += 1

    messages = []

    # Split into individual messages (mbox format: separated by "From " lines)
    msg_starts = []
    for i in range(start, len(lines)):
        if lines[i].startswith('From ') and re.match(r'^From \S+.*\d{2,4}', lines[i]):
            msg_starts.append(i)

    # If no mbox separators, treat whole thing as one message
    if not msg_starts:
        msg_starts = [start]

    for idx, msg_start in enumerate(msg_starts):
        msg_end = msg_starts[idx + 1] if idx + 1 < len(msg_starts) else len(lines)
        headers, body_start = parse_email_headers(lines, msg_start)
        body_lines = lines[body_start:msg_end]
        # Strip trailing empty lines
        while body_lines and not body_lines[-1].strip():
            body_lines.pop()
        messages.append((headers, body_lines))

    # Determine overall title
    if len(messages) == 1:
        h = messages[0][0]
        subject = h.get('Subject', '')
        sender = h.get('From', h.get('_mbox_date', ''))
        title = subject if subject else f"Email from {sender}" if sender else filename
    else:
        title = f"Mail Archive ({len(messages)} messages)"

    out = [f'<h1>{html.escape(title)}</h1>']

    for msg_idx, (headers, body_lines) in enumerate(messages):
        if len(messages) > 1:
            subj = headers.get('Subject', f'Message {msg_idx + 1}')
            out.append(f'<h2>{html.escape(subj)}</h2>')

        # Render headers as a styled block
        out.append('<div style="background:#f0ebe4; border:1px solid #d4c4b0; border-radius:4px; padding:10px 14px; margin:1em 0; font-size:0.9em;">')
        SHOW_HEADERS = ['From', 'To', 'Cc', 'Subject', 'Date']
        for key in SHOW_HEADERS:
            val = headers.get(key, '')
            if val:
                out.append(f'<div><b>{html.escape(key)}:</b> {html.escape(val)}</div>')
        # Show date from mbox line if no Date header
        if 'Date' not in headers and '_mbox_date' in headers:
            out.append(f'<div><b>Date:</b> {html.escape(headers["_mbox_date"])}</div>')
        out.append('</div>')

        # Render body
        if body_lines:
            # Check if body contains quoted text (lines starting with >)
            in_pre = False
            para = []
            for line in body_lines:
                if line.startswith('>') or line.startswith('|'):
                    if para:
                        out.append(f'<p>{html.escape(" ".join(para))}</p>')
                        para = []
                    if not in_pre:
                        out.append('<blockquote style="border-left:3px solid #d4c4b0; margin:0.5em 0; padding:4px 12px; color:#666;"><pre style="border:none; background:none; padding:0; margin:0;">')
                        in_pre = True
                    out.append(html.escape(line))
                else:
                    if in_pre:
                        out.append('</pre></blockquote>')
                        in_pre = False
                    stripped = line.strip()
                    if not stripped:
                        if para:
                            out.append(f'<p>{html.escape(" ".join(para))}</p>')
                            para = []
                    elif line.startswith('\t') or line.startswith('    '):
                        if para:
                            out.append(f'<p>{html.escape(" ".join(para))}</p>')
                            para = []
                        out.append(f'<pre>{html.escape(line)}</pre>')
                    else:
                        para.append(stripped)

            if in_pre:
                out.append('</pre></blockquote>')
            if para:
                out.append(f'<p>{html.escape(" ".join(para))}</p>')

        if msg_idx < len(messages) - 1:
            out.append('<hr style="border:none; border-top:2px dashed #d4c4b0; margin:2em 0;">')

    return title, '\n'.join(out)


def is_troff(text):
    lines = text.split('\n')
    cnt = 0
    for line in lines[:50]:
        if re.match(r'\.[A-Z]{2}', line) or line.startswith('.ds ') or line.startswith('.de ') or line.startswith('.so '):
            cnt += 1
    return cnt >= 3


def is_binary(data):
    """Check if data looks binary."""
    if not data:
        return True
    text_chars = set(range(32, 127)) | {9, 10, 13}
    non_text = sum(1 for b in data[:512].encode('utf-8', errors='replace') if b not in text_chars)
    return non_text > len(data[:512]) * 0.3


def extract_summary(text, max_len=200):
    """Extract first meaningful sentence(s) from content for auto-summary."""
    # Strip troff commands
    clean = re.sub(r'^\.[A-Za-z].*$', '', text, flags=re.MULTILINE)
    clean = re.sub(r'\\f[\(A-Z][A-Z]*', '', clean)
    clean = re.sub(r'\\s[+-]?\d+', '', clean)
    clean = re.sub(r'\\\*\([A-Za-z]{2}', '', clean)
    clean = re.sub(r'\\\*[A-Za-z]', '', clean)
    clean = re.sub(r'\\[()]..', '', clean)
    clean = re.sub(r'\\[a-z]', '', clean)
    clean = clean.replace('``', '"').replace("''", '"')
    # Strip %cvideo headers, mbox From lines, Mail to/from lines
    clean = re.sub(r'^%cvideo.*$', '', clean, flags=re.MULTILINE)
    clean = re.sub(r'^From \S+.*\d{4}.*$', '', clean, flags=re.MULTILINE)
    clean = re.sub(r'^(Return-Path|Received|Message-Id|Status):.*$', '', clean, flags=re.MULTILINE)
    clean = re.sub(r'^Mail (to|From):.*$', '', clean, flags=re.MULTILINE)
    clean = re.sub(r'^Date:\s+\S+day.*$', '', clean, flags=re.MULTILINE)
    clean = re.sub(r'^- - - .*$', '', clean, flags=re.MULTILINE)
    clean = re.sub(r'\bid [A-Z]{2}\d+;.*$', '', clean, flags=re.MULTILINE)
    # Get first two non-empty paragraph-like chunks
    chunks = re.split(r'\n\s*\n', clean)
    sentences = []
    for chunk in chunks:
        s = ' '.join(chunk.split()).strip()
        if len(s) > 20:
            sentences.append(s)
            if len(' '.join(sentences)) > max_len:
                break
    result = ' '.join(sentences)
    if len(result) > max_len:
        result = result[:max_len].rsplit(' ', 1)[0] + '...'
    return result


# ---- Descriptions from DOC files and analysis ----
FILE_INFO = {
    # Root docs
    'batch.itr': ('Batch Processes', 'Specs for overnight batch processes maintaining the Habitat world. Covers garbage collection, stock market, rent collection, and Hall of Records.'),
    'dropfix.itr': ('Drop Fix', 'Technical fix for the object drop mechanism. Addresses how objects are placed when avatars drop items.'),
    'econ.tbl': ('Habitat Economics', 'Complete economic model for Habitat including the Token currency. Defines trust funds, pricing, money sources and sinks.'),
    'ethics.itr': ('Habitat Ethics', 'Exploration of ethical considerations in the Habitat virtual world. Discusses governance, player behavior, and community standards.'),
    'extensions.itr': ('Habitat Extensions', 'Potential future directions for Habitat development. Catalogs short-term and long-term extension possibilities.'),
    'fortunes': ('Fortune Cookie Messages', 'In-game fortune messages from the Oracle and FortuneDroid. Humor, fake warnings, and Habitat lore.'),
    'garbage.tbl': ('Garbage Collection', 'Specs for garbage collection batch process on the host. How debris and abandoned objects are cleaned up.'),
    'geography.tbl': ('Geographic Master Plan', 'Master geographic plan for the Habitat world layout. Regions, cities, routes, and spatial design.'),
    'ghu.itr': ('Ghu Original Specs', 'Original specifications for Ghu, the Habitat region editor. Core design and command set.'),
    'ghuguide.itr': ('Ghu User Guide', 'Complete reference manual for Ghu, the region editor. Building and editing Habitat regions.'),
    'habitat': ('Habitat Email (1989)', 'A 1989 email about Habitat and cyberspace from the early days of virtual world thinking.'),
    'hostguide.t': ('Host Guide: Where Stuff Is', 'Overview of all Habitat directories on the Quantum Stratus. Source code and development environment structure.'),
    'hostnotes.t': ('Host Source Notes', 'Technical notes on every host-side source file. PL/1 include files, modules, and purposes.'),
    'hostnotes2.t': ('Host Connection Notes', 'Telenet connectivity and terminal configuration notes. Network setup for the Habitat host.'),
    'hotlist.tbl': ('Task Hot List', 'Priority task list for the Habitat development team. Outstanding work items and status.'),
    'manual.tbl': ('The Habitat Manual', 'The complete official Habitat user manual for players. All game mechanics, objects, and how to play.'),
    'memload.itr': ('Memory Load Analysis', 'C64 memory usage and object loading analysis. Memory constraints and optimization.'),
    'muddle.t': ('Muddle and Puddle', 'Muddle utility docs for generating C64 object disk data files. Muddle language and data formats.'),
    'newclass.t': ('Adding New Object Classes', 'Step-by-step guide for adding new object classes to Habitat. C64 and host-side requirements.'),
    'objman.itr': ('Object Manual', 'Comprehensive reference for every Habitat object class. Behaviors, properties, and interactions.'),
    'operations.itr': ('Operations Plan', 'First-pass operations plan for running Habitat. Staffing, monitoring, and maintenance procedures.'),
    'portdir.rt': ('Teleport Directory', 'In-game Populopolis teleport directory. Booth addresses and usage instructions.'),
    'records.itr': ('Hall of Records', 'Plan and spec for the Hall of Records system. Records, rankings, and achievement tracking.'),
    'regdesign.itr': ('Region Design Guide', 'Guide to designing Habitat regions (unfinished). Principles and techniques for world building.'),
    'regiontools.t': ('Griddle Region Tools', 'Griddle region description language and tools. Input/output formats for region data.'),
    'stats.itr': ('Statistics Plan', 'Updated plan for the Hall of Records statistics system. Extended metrics.'),
    'stuff.itr': ('Things To Do in Habitat', 'Design document on activities for Habitat players. Games, quests, social features.'),
    'update.t': ('Object Disk Version Management', 'Field-updating the C64 object disk via the host. Version tracking and incremental update protocol.'),
    'DOC': ('Documentation Index (Root)', 'Master directory listing and index of all Habitat documentation files.'),

    # system/
    'system/adventures.itr': ('Adventures Design', 'First pass at defining activities and things to do in Habitat.'),
    'system/animation.itr': ('Avatar Animation', 'Original spec for avatar animation cels and movement.'),
    'system/coming.itr': ('Coming Attractions', 'Discussion of realms and regions for the beta world.'),
    'system/coord.itr': ('Coordinate Systems', 'Coordinate systems and topology for the Habitat world.'),
    'system/databases.itr': ('Database Requirements', 'Host database requirements for Habitat.'),
    'system/death.itr': ('Avatar Death', 'How avatar death works in Habitat.'),
    'system/definition.itr': ('MicroCosm Definition', 'Dictionary definition of "microcosm" as project manifesto.'),
    'system/drop.itr': ('Drop Design Problem', 'Document on a minor design problem with dropping objects.'),
    'system/enddef.itr': ('Release System Definition', 'Early definition of the release system.'),
    'system/features.itr': ('System Components', 'System components description (very early design).'),
    'system/firstMagic.itr': ('First Magic', 'Spec for preliminary magic stuff in Habitat.'),
    'system/gateway.itr': ('Gateway Commentary', 'Commentary on realm-oriented extensions.'),
    'system/graphics.itr': ('C64 Graphics', 'Spec for C64 graphics implementation.'),
    'system/homearch.itr': ('C64 Home Architecture', 'Spec for C64 general system architecture.'),
    'system/hostarch.itr': ('Host Architecture', 'Spec for host general system architecture.'),
    'system/iface.itr': ('User Interface', 'Spec for the Habitat user interface.'),
    'system/intomic.itr': ('Third Party Software', 'Comments on 3rd party software inside Habitat.'),
    'system/looi.itr': ('LOOI Spec', 'Spec for LOOI (part of Habitat infrastructure).'),
    'system/machiavelli.itr': ('Machiavelli Sub-Game', 'Design for the Machiavelli sub-game.'),
    'system/mail.itr': ('Habitat Mail', 'Spec for the Habitat mail system.'),
    'system/maps.itr': ('World Layout Guidelines', 'Early guidelines for world layout and maps.'),
    'system/memload.itr': ('Memory Usage Analysis', 'Analysis of C64 memory usage.'),
    'system/microcosm.itr': ('MicroCosm Proposal', 'The original Habitat (MicroCosm) proposal document.'),
    'system/minobs.itr': ('Minimal Object Set', 'Minimal object set specification.'),
    'system/noodl.itr': ('NOODL Spec', 'Spec for NOODL (object description language).'),
    'system/noodl.y': ('NOODL Grammar', 'Yacc grammar file for the NOODL parser.'),
    'system/objectform.itr': ('Object Test Checklist', 'Object test checklist form.'),
    'system/obman.tbl': ('Object Manual (Original)', 'Original exhaustive object manual with tables.'),
    'system/oracle.itr': ('Oracle Design', 'Oracle capabilities design.'),
    'system/portmic.itr': ('Alternative Hosts', 'Considerations about alternative host platforms.'),
    'system/protocols.tbl': ('Message Protocols', 'Object message protocol description.'),
    'system/rantads.itr': ('Rant Advertising Policy', 'Policy on advertising in the Rant newspaper.'),
    'system/reno.itr': ('RENO Proposal', 'Proposal for RENO (region editor).'),
    'system/scenarios.itr': ('Interaction Scenarios', 'More things to do in Habitat.'),
    'system/shortwh.itr': ('Sample Interaction', 'Sample Habitat interaction writeup (promo doc).'),
    'system/DOC': ('System Docs Index', 'Index of original Habitat system design documents.'),

    # notes/
    'notes/abstract.t': ('Project Abstraction Notes', 'Notes on problems encountered in running the project.'),
    'notes/avatarcustom.t': ('Avatar Customization', 'Notes on avatar customization options.'),
    'notes/bitmap.t': ('Bitmap Display Notes', 'Notes on going to an all-bitmap display on the C64.'),
    'notes/blurb.t': ('Promo Blurb', 'Short promotional blurb for Habitat.'),
    'notes/bugreport.t': ('Bug Report Form', 'Explanation of the bug report form.'),
    'notes/burmashave': ('Burma Shave Signs', 'Burma Shave roadside signs from Noah for Habitat.'),
    'notes/capacity.pl1': ('Capacity Monitor (PL/1)', 'PL/1 source for the capacity monitor on host.'),
    'notes/comm.t': ('Telecomm Problems', 'Notes on problems with Q-Link telecomm protocols.'),
    'notes/congrats.itr': ('Congratulations Blurb', 'A silly promotional blurb.'),
    'notes/contVector.t': ('Contents Vectors', 'Format for contents vectors.'),
    'notes/counters.t': ('Counters and Displays', 'Notes on design of counters and display cases.'),
    'notes/credits.t': ('Habitat Credits', 'Credits for the Habitat project.'),
    'notes/custom.t': ('Customizer Help Text', 'User help text for the customizer.'),
    'notes/disk.t': ('C64 Object Disk Layout', 'Layout of the C64 object disk.'),
    'notes/docs.t': ('Design Documents List', 'List of original design documents.'),
    'notes/farmerComm.t': ('Farmer Telecomm Notes', 'Notes on telecomm protocols.'),
    'notes/glossary.t': ('Habitat Glossary', 'Brief glossary of Habitat terminology.'),
    'notes/groups.t': ('Object Class Groups', 'Object classes listed by functional group.'),
    'notes/help_messages.t': ('Help Messages', 'Help text for various objects (obsolete).'),
    'notes/ideas.t': ('Ideas', 'Some ideas for Habitat.'),
    'notes/ideas1.t': ('More Ideas', 'More ideas for Habitat.'),
    'notes/ideas2.t': ('Still More Ideas', 'Still more ideas for Habitat features.'),
    'notes/manualids': ('Manual User IDs', 'Userstat output on user-ids listed in the manual.'),
    'notes/messages.t': ('Message Numbers', 'Description of Habitat message numbers.'),
    'notes/moneyNotes.t': ('Money in Vendos', 'Notes on usage of money in vendos.'),
    'notes/names.t': ('Reserved User IDs', 'List of proposed reserved user-ids.'),
    'notes/newu.t': ('New User Protocol', 'Protocol for signing on a new user.'),
    'notes/orient.t': ('Orientation Byte', 'Layout of the orientation byte.'),
    'notes/palindromes.t': ('Palindrome Signs', 'Palindromic Burma Shave signs from Noah.'),
    'notes/patt.t': ('Graphics Patterns', 'Format of 16 Habitat graphics patterns.'),
    'notes/protocol_notes.t': ('Protocol Wishlist', "Randy's telecom protocol wishlist."),
    'notes/rant.1.1.rt': ('The Rant Vol 1 No 1', 'First issue of The Rant, Habitat newspaper.'),
    'notes/slur.t': ('Slur and Riddle', 'Documentation for Slur and Riddle tools (obsolete).'),
    'notes/source.t': ('Source Code Guide', 'A guide to the Habitat source code.'),
    'notes/stats': ('Stat Codes', 'Stat codes for the Hall of Records.'),
    'notes/stats.t': ('Statistics to Collect', 'List of possible statistics to collect on users.'),
    'notes/stratusMap.t': ('Stratus Directory Map', 'Map of directories on the Stratus.'),
    'notes/throttle.t': ('Telecomm Throttle', 'Notes on the telecomm throttle.'),
    'notes/version.t': ('Version Notes', 'Notes on track/sector disk update versioning.'),
    'notes/DOC': ('Notes Index', 'Index of miscellaneous notes and fragments.'),

    # worldgen/
    'worldgen/aricpop.t': ('Populopolis (Aric)', "Aric's notes on Populopolis region design."),
    'worldgen/aricpopAug.t': ('Populopolis August Update', 'August update to Populopolis region design.'),
    'worldgen/barwood.t': ('Barwood Notes', 'Creative notes from Barwood on world design.'),
    'worldgen/dnalsi.t': ('Dnalsi Island', 'Design notes for Dnalsi Island area.'),
    'worldgen/dnalsiRant.t': ('Dnalsi Rant', 'Extended design notes and rant on Dnalsi Island.'),
    'worldgen/downtown.t': ('Downtown Design', 'Design notes for downtown area.'),
    'worldgen/draftplan.t': ('World Draft Plan', 'Draft plan for world generation.'),
    'worldgen/elect.rt': ('Election', 'In-game election text or event.'),
    'worldgen/farmerAdvs.t': ('Farmer Adventures', 'Adventure designs for Farmer player scenarios.'),
    'worldgen/farmerAdvs2.t': ('Farmer Adventures 2', 'More adventure designs for Farmer scenarios.'),
    'worldgen/funativity.itr': ('Funativity', 'More on stuff to do in Habitat (fun activities).'),
    'worldgen/gregp': ('Greg P Notes', "Greg P's creative notes for world generation."),
    'worldgen/mayhem': ('Mayhem', 'Notes on mayhem and chaos events in Habitat.'),
    'worldgen/nameflame': ('Name Flame', 'Notes on naming controversies or flame wars.'),
    'worldgen/oath.t': ('The Oath', 'An oath or pledge related to Habitat lore.'),
    'worldgen/preplan.t': ('Pre-Plan', 'Pre-planning notes for world generation.'),
    'worldgen/reno.itr': ('RENO (Worldgen)', 'RENO-related worldgen notes.'),
    'worldgen/scenarios.itr': ('Worldgen Scenarios', 'Scenario designs for world generation.'),
    'worldgen/DOC': ('Worldgen Index', 'Index of world generation creative material.'),

    # admin/
    'admin/behind.t': ('Behind Schedule', 'Notes on schedule slippage and falling behind.'),
    'admin/beta.t': ('Beta Plan', 'Beta test planning document.'),
    'admin/beta2.t': ('Beta Plan 2', 'Second beta test planning document.'),
    'admin/beta3.t': ('Beta Plan 3', 'Third beta test planning iteration.'),
    'admin/beta4.t': ('Beta Plan 4', 'Fourth beta test planning iteration.'),
    'admin/dbtasks.t': ('Database Tasks', 'Database-related task list.'),
    'admin/done.t': ('Done List', 'List of completed tasks.'),
    'admin/illos': ('Illustrations List', 'List of illustrations needed.'),
    'admin/items.t': ('Action Items', 'Action items and tasks.'),
    'admin/items2.t': ('Action Items 2', 'More action items.'),
    'admin/janetEst': ('Janet Estimates', "Janet's time/cost estimates."),
    'admin/mondayChecklist.t': ('Monday Checklist', 'Weekly Monday checklist for operations.'),
    'admin/newprocedure.t': ('New Procedures', 'New operational procedures document.'),
    'admin/newsched.t': ('New Schedule', 'Revised project schedule.'),
    'admin/qprobs.t': ('Q-Link Problems', 'Problems with Q-Link integration.'),
    'admin/realms.t': ('Realms Planning', 'Planning notes for realm implementation.'),
    'admin/resolution.t': ('Issue Resolution', 'Issue resolution and decision document.'),
    'admin/sched2.t': ('Schedule Rev 2', 'Second revision of project schedule.'),
    'admin/status.Oct20.t': ('Status Oct 20', 'Project status report for October 20.'),
    'admin/status.Oct29.t': ('Status Oct 29', 'Project status report for October 29.'),
    'admin/status.t': ('Project Status', 'Main project status report.'),
    'admin/status2.t': ('Project Status 2', 'Second project status report.'),
    'admin/survey.t': ('Survey Overview', 'Overview of the Habitat user survey.'),
    'admin/tasks.t': ('Task List', 'Project task list.'),
    'admin/tuesdayChecklist.t': ('Tuesday Checklist', 'Weekly Tuesday checklist for operations.'),
    'admin/DOC': ('Admin Index', 'Index of administrative documents.'),

    # cya/
    'cya/Feb20.let': ('Letter Feb 20', 'Correspondence dated February 20.'),
    'cya/Jan21.let': ('Letter Jan 21', 'Correspondence dated January 21.'),
    'cya/contractComments.t': ('Contract Comments', 'Comments on the Habitat contract.'),
    'cya/contractComments2.t': ('Contract Comments 2', 'Additional contract comments.'),
    'cya/coverDec5.let': ('Cover Letter Dec 5', 'Cover letter dated December 5.'),
    'cya/coverFeb5.let': ('Cover Letter Feb 5', 'Cover letter dated February 5.'),
    'cya/coverJan5.let': ('Cover Letter Jan 5', 'Cover letter dated January 5.'),
    'cya/coverMar5.let': ('Cover Letter Mar 5', 'Cover letter dated March 5.'),
    'cya/definition': ('Definition', 'A definition document for CYA purposes.'),
    'cya/distrib': ('Distribution List', 'Document distribution list.'),
    'cya/exhibita.itr': ('Exhibit A', 'Contract Exhibit A.'),
    'cya/exhibitb.itr': ('Exhibit B', 'Contract Exhibit B.'),
    'cya/explorations1': ('Explorations 1', 'First set of exploration notes.'),
    'cya/grigg': ('Grigg Note', 'Note related to Grigg.'),
    'cya/letter.let': ('Letter', 'A formal letter.'),
    'cya/mailarchive': ('Mail Archive', 'Archive of project-related emails.'),
    'cya/maillog': ('Mail Log', 'Log of project correspondence.'),
    'cya/meetingOct7.t': ('Meeting Oct 7', 'Meeting notes from October 7.'),
    'cya/memo.t': ('Memo', 'Internal project memo.'),
    'cya/memoJun17.let': ('Memo Jun 17', 'Memo dated June 17.'),
    'cya/memoOct27.let': ('Memo Oct 27', 'Memo dated October 27.'),
    'cya/midCoverApr25.let': ('Mid-Cover Apr 25', 'Mid-period cover letter April 25.'),
    'cya/midCoverFeb15.let': ('Mid-Cover Feb 15', 'Mid-period cover letter February 15.'),
    'cya/midCoverJan15.let': ('Mid-Cover Jan 15', 'Mid-period cover letter January 15.'),
    'cya/midCoverJul2.let': ('Mid-Cover Jul 2', 'Mid-period cover letter July 2.'),
    'cya/midCoverMar15.let': ('Mid-Cover Mar 15', 'Mid-period cover letter March 15.'),
    'cya/milestones.t': ('Milestones', 'Project milestone tracking.'),
    'cya/qinfo.t': ('Q-Link Info', 'Information about Q-Link partnership.'),
    'cya/qlog.t': ('Q-Link Log', 'Log of Q-Link interactions and events.'),
    'cya/qmeeting.t': ('Q-Link Meeting', 'Q-Link meeting notes.'),
    'cya/reportDecember.itr': ('Report December', 'Monthly report for December.'),
    'cya/reportFebruary.itr': ('Report February', 'Monthly report for February.'),
    'cya/reportJanuary.itr': ('Report January', 'Monthly report for January.'),
    'cya/reportMarch.itr': ('Report March', 'Monthly report for March.'),
    'cya/reportNovember.itr': ('Report November', 'Monthly report for November.'),
    'cya/robreqs.t': ('Rob Requirements', "Rob's requirements and requests."),
    'cya/statusReport.Sept5': ('Status Report Sep 5', 'Status report from September 5.'),
    'cya/DOC': ('CYA Index', 'Index of CYA (Cover Your Ass) correspondence and memos.'),

    # archives/
    'archives/brief.itr': ('Brief Overview', 'Brief overview document for Habitat.'),
    'archives/coming.Oct20.itr': ('Coming Attractions Oct 20', 'Upcoming features and plans as of October 20.'),
    'archives/contract': ('Contract', 'The Habitat development contract.'),
    'archives/contract2': ('Contract 2', 'Second version or addendum to the Habitat contract.'),
    'archives/demo.aric.t': ('Aric Demo Script', "Aric's demo script for Habitat."),
    'archives/excerpts.tbl': ('Document Excerpts', 'Excerpts from various Habitat documents.'),
    'archives/extensions.Sep29.itr': ('Extensions Sep 29', 'Extensions document from September 29.'),
    'archives/gateway.Sep25.itr': ('Gateway Sep 25', 'Gateway document from September 25.'),
    'archives/ghu.itr.aug6': ('Ghu Specs Aug 6', 'Ghu specifications from August 6.'),
    'archives/long1.itr': ('Long Range Plan 1', 'First long-range planning document.'),
    'archives/long2.itr': ('Long Range Plan 2', 'Second long-range planning document.'),
    'archives/long3.itr': ('Long Range Plan 3', 'Third long-range planning document.'),
    'archives/long4.itr': ('Long Range Plan 4', 'Fourth long-range planning document.'),
    'archives/manual.nov17': ('Manual Nov 17', 'Manual version from November 17.'),
    'archives/manual.sep8': ('Manual Sep 8', 'Manual version from September 8.'),
    'archives/manualMay86.itr': ('Manual May 86', 'Manual version from May 1986.'),
    'archives/microland.itr': ('MicroLand', 'MicroLand concept document.'),
    'archives/names.t': ('Names', 'List of names for Habitat.'),
    'archives/nancymemo': ('Nancy Memo', 'Memo from/about Nancy.'),
    'archives/notabugList.t': ('Not-a-Bug List', 'List of reported issues that are not bugs.'),
    'archives/old.lnetnotes/chip.t': ('Chip LNet Notes', "Chip's notes from LNet."),
    'archives/old.lnetnotes/concept.t': ('Concept LNet Notes', 'Conceptual notes from LNet discussions.'),
    'archives/old.lnetnotes/nf.t': ('NF LNet Notes', 'NF-related notes from LNet.'),
    'archives/operations.Oct5.itr': ('Operations Oct 5', 'Operations document from October 5.'),
    'archives/palladium.itr': ('Palladium', 'Palladium concept/proposal document.'),
    'archives/plan.t': ('Plan', 'Project planning document.'),
    'archives/plan2.t': ('Plan 2', 'Second project planning document.'),
    'archives/pr.t': ('Press Release', 'Press release or PR materials.'),
    'archives/riddle.t': ('Riddle', 'Documentation for the Riddle tool.'),
    'archives/scenarios.itr': ('Scenarios (Archive)', 'Archived scenario designs.'),
    'archives/short1.itr': ('Short Range Plan', 'Short-range planning document.'),
    'archives/tapenotes.itr': ('Tape Notes', 'Notes about tape-based deliverables.'),
    'archives/tmark': ('Trademark', 'Trademark information document.'),
    'archives/world.itr': ('World Design', 'World design document.'),
    'archives/worldComments': ('World Comments', 'Comments on the world design.'),
    'archives/worldTasks.t': ('World Tasks', 'Task list for world creation.'),
    'archives/DOC': ('Archives Index', 'Index of historically important archived documents.'),
}

# Skip these files entirely (binary, too large survey data, or redundant)
SKIP_FILES = {'.mo'}
SKIP_PATTERNS = {'survey.pre', 'survey.post'}  # The giant concatenated survey files


def make_html_filename(relpath):
    """Turn a relative path like 'system/coord.itr' into 'system__coord_itr.html'."""
    return relpath.replace('/', '__').replace('.', '_') + '.html'


def walk_raw_files():
    """Walk raw directory and yield (relpath, abspath) for all files."""
    for root, dirs, files in os.walk(RAW_DIR):
        dirs.sort()
        for fname in sorted(files):
            relpath = os.path.relpath(os.path.join(root, fname), RAW_DIR)
            abspath = os.path.join(root, fname)
            yield relpath, abspath


def main():
    os.makedirs(HTML_DIR, exist_ok=True)

    generated = []  # (relpath, html_filename, display_title, summary, section)

    for relpath, abspath in walk_raw_files():
        fname = os.path.basename(relpath)

        if fname in SKIP_FILES:
            continue
        if fname in SKIP_PATTERNS:
            continue

        size = os.path.getsize(abspath)
        if size == 0:
            continue

        try:
            with open(abspath, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
        except Exception as e:
            print(f"  SKIP (read error): {relpath}: {e}", file=sys.stderr)
            continue

        if is_binary(content):
            print(f"  SKIP (binary): {relpath}")
            continue

        # Determine section
        parts = relpath.split('/')
        section = parts[0] if len(parts) > 1 else 'root'

        # Convert
        if fname == 'fortunes':
            title, body = convert_fortunes(content)
        elif fname == 'DOC':
            title = f"Index: {section}" if section != 'root' else "Documentation Index"
            body = f'<h1>{html.escape(title)}</h1><pre>{html.escape(content)}</pre>'
        elif is_survey(content, relpath):
            title, body = convert_survey(content, os.path.basename(relpath))
        elif is_region_text(content, fname):
            title, body = convert_region_text(content, fname)
        elif is_troff(content):
            title, body = convert_troff(content, fname)
        elif is_email(content):
            title, body = convert_email(content, fname)
        else:
            title, body = convert_plaintext(content, fname)

        if not title:
            title = fname

        info = FILE_INFO.get(relpath, (None, None))
        if info[0] is None:
            # For hotlist/* and survey/* files, auto-generate
            display_title = title
            summary = extract_summary(content, 160)
        else:
            display_title = info[0]
            summary = info[1] or extract_summary(content, 160)

        html_fname = make_html_filename(relpath)
        full_html = html_page(display_title, body, "index.html", source_path=relpath)

        with open(os.path.join(HTML_DIR, html_fname), 'w', encoding='utf-8') as f:
            f.write(full_html)

        generated.append((relpath, html_fname, display_title, summary, section))
        print(f"  {relpath} -> {html_fname}")

    print(f"\nConverted {len(generated)} documents. Building index...")

    # ---- Build index.html with JS filtering ----
    SECTION_NAMES = {
        'root': 'Core Documentation',
        'system': 'System Design Documents',
        'notes': 'Notes & Fragments',
        'worldgen': 'World Generation',
        'admin': 'Administration & Status',
        'cya': 'Correspondence & Memos (CYA)',
        'archives': 'Historical Archives',
        'hotlist': 'Task Hot Lists (Historical)',
    }

    SECTION_ORDER = ['root', 'system', 'notes', 'worldgen', 'admin', 'cya', 'archives', 'hotlist']

    # Group by section
    by_section = {}
    for relpath, html_fname, display_title, summary, section in generated:
        by_section.setdefault(section, []).append((relpath, html_fname, display_title, summary))

    # Build table rows as data for JS
    rows_json = json.dumps([
        {"href": html_fname, "title": display_title, "summary": summary, "section": section, "file": relpath}
        for relpath, html_fname, display_title, summary, section in generated
    ], ensure_ascii=False)

    section_names_json = json.dumps(SECTION_NAMES, ensure_ascii=False)

    toc_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Habitat Documentation Archive</title>
<style>{CSS}
#filter-box {{
    width: 100%;
    padding: 10px 14px;
    font-size: 1.05em;
    border: 2px solid #d4c4b0;
    border-radius: 6px;
    background: #fff;
    margin: 16px 0 8px 0;
    font-family: inherit;
    box-sizing: border-box;
}}
#filter-box:focus {{
    outline: none;
    border-color: #8b4513;
    box-shadow: 0 0 0 2px rgba(139,69,19,0.15);
}}
#match-count {{
    font-size: 0.85em;
    color: #888;
    margin-bottom: 16px;
}}
.section-group {{ margin-bottom: 2em; }}
.section-group.hidden {{ display: none; }}
tr.hidden {{ display: none; }}
mark {{ background: #fde68a; padding: 0 1px; border-radius: 2px; }}
</style>
</head>
<body>

<h1>Habitat Documentation Archive</h1>
<p style="font-size:1.1em; color:#555;">Internal documentation from <b>Lucasfilm Games Division</b> for the Habitat virtual world project (1986&ndash;1988), by Chip Morningstar and team. <a href="{GITHUB_BASE}" style="font-size:0.85em;">GitHub source</a></p>
<p style="color:#888; font-size:0.9em;">Originally on the Quantum Stratus host system &mdash; {len(generated)} documents converted from troff/nroff and plain text.</p>

<input type="text" id="filter-box" placeholder="Filter documents... (type to search titles and summaries)" autofocus>
<div id="match-count"></div>

<div id="toc-content"></div>

<script>
const DOCS = {rows_json};
const SECTION_NAMES = {section_names_json};
const SECTION_ORDER = {json.dumps(SECTION_ORDER)};

function escapeHtml(s) {{
    return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}}

function highlightMatch(text, words) {{
    if (!words.length) return escapeHtml(text);
    let result = escapeHtml(text);
    for (const w of words) {{
        const re = new RegExp('(' + w.replace(/[.*+?^${{}}()|[\\]\\\\]/g, '\\\\$&') + ')', 'gi');
        result = result.replace(re, '<mark>$1</mark>');
    }}
    return result;
}}

function render(filterText) {{
    const words = filterText.trim().toLowerCase().split(/\\s+/).filter(w => w.length > 0);

    // Filter docs
    const filtered = DOCS.filter(d => {{
        if (!words.length) return true;
        const haystack = (d.title + ' ' + d.summary + ' ' + d.file).toLowerCase();
        return words.every(w => haystack.includes(w));
    }});

    // Group by section
    const groups = {{}};
    for (const d of filtered) {{
        if (!groups[d.section]) groups[d.section] = [];
        groups[d.section].push(d);
    }}

    let html = '';
    for (const sec of SECTION_ORDER) {{
        const docs = groups[sec];
        if (!docs || docs.length === 0) continue;
        const name = SECTION_NAMES[sec] || sec;
        html += '<div class="section-group">';
        html += '<h2>' + escapeHtml(name) + ' <span style="font-size:0.7em;color:#999;">(' + docs.length + ')</span></h2>';
        html += '<table><tr><th style="width:28%">Document</th><th>Summary</th></tr>';
        for (const d of docs) {{
            const title = highlightMatch(d.title, words);
            const summary = highlightMatch(d.summary, words);
            html += '<tr><td><a href="' + d.href + '">' + title + '</a></td><td>' + summary + '</td></tr>';
        }}
        html += '</table></div>';
    }}

    document.getElementById('toc-content').innerHTML = html;
    const countEl = document.getElementById('match-count');
    if (words.length) {{
        countEl.textContent = filtered.length + ' of ' + DOCS.length + ' documents match';
    }} else {{
        countEl.textContent = DOCS.length + ' documents';
    }}
}}

const filterBox = document.getElementById('filter-box');
filterBox.addEventListener('input', () => render(filterBox.value));
render('');
</script>

</body>
</html>
"""

    with open(os.path.join(HTML_DIR, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(toc_html)

    print(f"Generated index.html with {len(generated)} documents and JS filtering.")


if __name__ == '__main__':
    main()
