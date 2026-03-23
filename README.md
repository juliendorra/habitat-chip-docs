# Habitat Documentation Archive

Internal documentation from **Lucasfilm Games Division** for the [Habitat](https://en.wikipedia.org/wiki/Habitat_(video_game)) virtual world project (1986–1988), by Chip Morningstar and team.

## Browse

Open [`html/index.html`](html/index.html) in a browser. The index page has a live filter box to search across all 318 documents by title or summary.

## Source

The original files in `raw/` were retrieved from the [Museum of Art and Digital Entertainment](https://github.com/Museum-of-Art-and-Digital-Entertainment/habitat) repository:

> https://github.com/Museum-of-Art-and-Digital-Entertainment/habitat/tree/b59e2520fd8690bf99a1db43928a679f2fbc875c/chip/habitat/docs

The files are in troff/nroff format (`.itr`, `.tbl`), plain text (`.t`), region text (`.rt`), email/mbox, and Habitat survey response formats. The `.itr` extension stands for interoffice technical report — a Lucasfilm convention.

## Sections

| Directory | Contents |
|-----------|----------|
| `raw/` (root) | Core design docs, manual, economics, ethics, tools |
| `raw/system/` | Original system design documents (#1–#47) |
| `raw/notes/` | Miscellaneous notes, glossary, ideas, credits |
| `raw/worldgen/` | World generation creative material |
| `raw/admin/` | Status reports, schedules, beta plans, user survey |
| `raw/cya/` | Correspondence, memos, meeting notes, monthly reports |
| `raw/archives/` | Historical documents, contracts, older drafts |
| `raw/hotlist/` | Daily task snapshots (Nov 1986 – Apr 1987) |

## Conversion

`convert.py` converts all 318 documents from their original formats to browsable HTML pages. To regenerate:

```
python3 convert.py
```

This reads from `raw/` and writes to `html/`.

## How this was made

This archive was built using [Claude Code](https://claude.ai/claude-code) (Claude Opus) in an interactive conversation. The process and prompts are documented here so the work is transparent and reproducible.

### Step 1: Download

The raw files were downloaded from the GitHub repository using `gh api` to list the tree recursively, then `curl` to fetch all 321 files in parallel, preserving the subdirectory structure.

### Step 2: Format analysis

Claude read samples from each file format and the `DOC` index files in each subdirectory to identify the formats in use:

- **`.itr`** (interoffice technical report) and **`.tbl`** — troff/nroff with `-ms` macros (`.TL`, `.AU`, `.SH`, `.PP`, `.IP`, `.NH`, etc.)
- **`.t`** — mixed: some troff, mostly plain text
- **`.rt`** — in-game region text, hard-wrapped at ~40 characters for the Commodore 64 screen
- **`.let`** — troff with letter template macros (`.so letdefs.nr`)
- **`.pre` / `.post`** — Habitat beta survey responses from Q-Link users, with `%cvideo` system headers
- **email/mbox** — Unix mail format with `From ` envelope lines and RFC822 headers
- **`fortunes`** — one fortune cookie message per line

### Step 3: Converter (`convert.py`)

A Python script was written with dedicated converters for each format:

- **Troff converter**: A two-pass parser. Pass 1 extracts metadata (`.TL` title, `.AU` author, `.AI` institution, `.ds` string definitions). Pass 2 converts the body: section headings (`.SH`, `.NH`), paragraphs (`.PP`, `.LP`), bullet lists (`.IP`), display blocks (`.DS`/`.DE`, `.nf`/`.fi`), tables (`.TS`/`.TE`), and centered text (`.ce`). Inline formatting uses a state machine for font switches (`\fI` italic, `\fB` bold, `\fC`/`\fH`/`\fL` constant-width, `\f(BI` bold-italic, `\f(CB` constant-width bold) that tracks open tags and properly nests/closes them. Special characters (`\(em`, `\(bu`, `\(->`, etc.) are mapped to Unicode.
- **Email converter**: Parses mbox `From ` separators, RFC822 headers (From, To, Subject, Date), and body text. Multi-message archives are split into sections. Quoted text (`>` lines) gets blockquote formatting.
- **Survey converter**: Parses the `%cvideo` system header, the question text and choices, and individual respondent answers (separated by `- - -` lines with `Mail From:` headers). The summary file gets structured table rendering.
- **Region text converter**: Reflows 40-character hard-wrapped lines into proper paragraphs, extracts dash-delimited headings, and handles page break markers.

### Step 4: Titles and summaries

Every document has a hand-written title and two-sentence summary stored in the `FILE_INFO` dictionary in `convert.py`. These were written by Claude after reading:

- The `DOC` index files in each subdirectory (which map filenames to document numbers and descriptions)
- The first ~60 lines of each file to understand its content
- The survey question texts extracted from the `.pre` files
- The dates from the `.ds Dq` troff string definitions in hotlist files

The summaries describe what each document covers and its role in the project. No auto-generated summaries are used in the final output.

### Step 5: Index page

The `index.html` table of contents groups documents into 8 sections and includes a JavaScript filter box. Typing any words instantly filters all 318 entries by matching against titles and summaries, with highlighted matches. Each document page links back to its original source file on GitHub.

### Reproducing or extending this work

To regenerate the HTML from the raw files:

```
python3 convert.py
```

To replicate the process from scratch with an LLM, the key prompts were:

1. *"Download these docs and convert them to HTML pages with a TOC with a short summary of each one. The format is not clear (ITR?) — make sure the conversion is properly done."* — This drove the initial format analysis and converter.
2. *"You missed all the subdirectories"* — Extended to all 7 subdirectories (321 files total).
3. *"Many docs have issues — look for `\f` to find them"* — Led to fixing the font code state machine, `\f(BI` two-char fonts, and pre-block cleanup.
4. *"Some documents seem to be email in email format"* — Added the dedicated email/mbox converter.
5. *"The `.rt` files are rendering incorrectly"* — Added the region text reflowing converter.
6. *"The survey files are hard to read"* — Added the dedicated survey response converter.
7. *"Add a link to the source / Add JS filtering"* — UI improvements.

The iterative approach — convert, inspect output, identify problems, fix — worked well because the formats have many edge cases that only surface when reading the actual rendered HTML.
