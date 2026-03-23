# Habitat Documentation Archive

Internal documentation from **Lucasfilm Games Division** for the [Habitat](https://en.wikipedia.org/wiki/Habitat_(video_game)) virtual world project (1986–1988), by Chip Morningstar and team.

## Browse

Open [`html/index.html`](html/index.html) in a browser. The index page has a live filter box to search across all 318 documents by title or summary.

## Source

The original files in `raw/` were retrieved from the [Museum of Art and Digital Entertainment](https://github.com/Museum-of-Art-and-Digital-Entertainment/habitat) repository:

> https://github.com/Museum-of-Art-and-Digital-Entertainment/habitat/tree/b59e2520fd8690bf99a1db43928a679f2fbc875c/chip/habitat/docs

The files are in troff/nroff format (`.itr`, `.tbl`), plain text (`.t`), region text (`.rt`), email/mbox, and Habitat survey response formats. The `.itr` extension stands for interoffice technical report — a Lucasfilm convention.

## Conversion

`convert.py` converts all 318 documents from their original formats to browsable HTML pages. To regenerate:

```
python3 convert.py
```

This reads from `raw/` and writes to `html/`.

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
