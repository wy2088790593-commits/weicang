---
name: local-offline-dashboard
description: Build a self-contained, offline HTML dashboard from a local data file — no server, no network, opens by double-click. This skill should be used when the user wants a local 看板 / dashboard / 速查页 / tracking board rendered from data they maintain on their own machine (e.g. 灵感库、进度看板、投放决策看板、竞品跟踪表), or whenever an HTML output must render correctly from the local filesystem under file:// without CORS or fetch errors.
agent_created: true
---

# Local Offline Dashboard

## Overview

Produce a single-file HTML board that renders local data, opens by double-click, and
never needs a server or network. Use when data must stay on the machine, or when the
user wants a board they can just open rather than launch.

## Architecture — three parts, one direction

    data.json  →  build.py  →  board.html   (data inlined at build time)

1. `data.json` — the single source of truth. Append records here; never hand-edit the HTML.
2. `build.py` — reads the JSON and substitutes it into the HTML's inert data block.
3. `board.html` — self-contained page, opens offline by double-click.
4. `refresh.bat` — one double-click rebuild for the user.

Do not add more moving parts. Do not introduce a web server unless the user explicitly
wants live in-browser editing — that is a different architecture with a different cost.

## Critical pitfalls

These are the ones that silently break the whole thing. Do not skip them.

### 1. `file://` blocks fetch — inline the data instead

`fetch('data.json')` fails under `file://` with a cross-origin error in Chrome/Edge.
Do not try to work around it with browser flags. Instead keep an inert block in the
HTML and substitute its content at build time:

```html
<script id="data" type="application/json">
{ "items": [] }
</script>
```

Substitute with a non-greedy regex anchored on the id, and fail loudly unless exactly
one match is found — never write the file on an ambiguous match:

```python
DATA_RE = re.compile(r'(<script id="data" type="application/json">)(.*?)(</script>)', re.S)
payload = json.dumps(data, ensure_ascii=False, indent=2).replace("</", "<\\/")
new_html, n = DATA_RE.subn(lambda m: m.group(1) + "\n" + payload + "\n" + m.group(3), html, count=1)
if n != 1:
    sys.exit("data block marker not found - file left untouched")
```

### 2. Escape `</` before injecting JSON

A record containing `</script>` would close the block early and break the page.
`json.dumps(...).replace("</", "<\\/")` is safe — `\/` is a legal JSON escape.

### 3. Images must use relative paths

Relative paths (`灵感截屏/x.png`) render fine under `file://`. Absolute paths pointing
at other drives often do not. Keep images in a subfolder of the board and reference them
relatively. Check at build time that every referenced image exists.

### 4. Windows launcher (.bat)

- Keep the `.bat` strictly ASCII. A Chinese filename inside the body forces GBK encoding
  and corrupts the file for UTF-8 tooling. Trigger browser opening from Python instead,
  via `os.startfile(html_path)`.
- CRLF line endings, no BOM.
- Do not pipe through `tail` / `dirname` — stripped Git Bash environments on Windows may
  not have them.

```bat
@echo off
title Board
"C:\path\to\python.exe" "%~dp0build.py" --open
echo.
pause
```

### 5. An enum change has to be made in three places

The category/type enum lives in three files, and the build script only touches one:

1. the record's field in `data.json`
2. the allowed-enum list in `build.py` — miss it and every build prints a warning
3. the `CATS` array **and** its colour map in `board.html` — the build only substitutes the
   data block, so it will **never** sync these two JS constants

Miss #3 and it fails silently and confusingly: the new category is simply absent from the
filter bar, and records in it render in the neutral grey fallback. When the user corrects a
classification, treat it as an enum change, not just a data edit — check whether the category
already exists in all three places before touching the record.

## Build-time self-checks to include

- Every image referenced by a record exists on disk
- Report orphan files in the image folder (present but unreferenced)
- Report records whose category or type falls outside the allowed enum
- Print one summary line: total / new this month / by type

## Visual defaults

Reuse this palette unless the user has another established one — it reads as an
operational board rather than a generic web page:

| Role | Fill | Text |
|---|---|---|
| brand / primary | `#FAECE7` | `#E8552D` |
| pending, needs action | `#FCEBEB` | `#C00000` |
| category | `#FAEEDA` | `#BA7517` |
| metric | `#E6F1FB` | `#2F5597` |
| neutral | `#F1EFE8` | `#5F5E5A` |

Layout: orange title strip (left accent bar 5×22px + 2px `#F0997B` underline) → four
metric cards → filter pills carrying counts → card grid.
Grid: `repeat(auto-fill, minmax(300px, 1fr))`, gap 14px. Page bg `#FBFAF7`, cards white
with `1px solid #EAE8E1`, radius 12px.

Interaction the user will expect: filter pills, a search box over title/text/tags,
date-descending order, an empty-state message, and images clickable to open full size.

## Build flags

Support `--open` to launch the finished board (`os.startfile`), and make it opt-in so
scripted rebuilds do not pop windows unexpectedly.

## Recording a new entry (when you maintain the board for the user)

The user drops you a screenshot or a paragraph; you do the filing. Flow:

1. Screenshot → copy into the image folder, name it `YYYY-MM-DD_category_keyword.png`
2. Append one record to the JSON (`id` = `YYYYMMDD-NNN`)
3. Rebuild the HTML by running the build script — never hand-edit the board
4. Report back: how many added, new total, and any metric movement

**Keep the user's wording verbatim in `text`.** They are writing down a rule or a
judgement they will reread in three months, so do not paraphrase. In particular,
preserve their enumerated structure as real newlines (`\n` inside the JSON string) —
flattening "1、… 2、… 3、…" into one paragraph destroys the structure they wrote it in.
Only strip instruction scaffolding around the content (e.g. a leading "记录下来：").

**Importing a result from another task? Establish the version first.** A topic that has been
iterated on will have superseded drafts, and an outdated draft pasted into a knowledge base is
worse than no entry — it will be trusted. Search the source workspace for its memory log,
read the latest entry, and prefer quoting the authoritative document (a skill, a spec) over
reconstructing from conversation. Record where the truth lives in the entry's `source` field.

Then tell the user if the content now exists in two places. If the same rules already live in a
skill or doc, the board copy is dual-maintenance: it will silently go stale the next time the
source is revised. Say so explicitly, and keep the board copy to a skeleton that points at the
source rather than a full duplicate.

**Source screenshots usually have hostile filenames.** Chat clients drop files as names like
`5G[)_RK657[(]0H1D3XI_7T.png` or `F%CX)FUYXR$%{PYEA4N9WMY.png`. A hardcoded path to one of these
can raise `FileNotFoundError` even though the file exists and `iterdir()` lists it fine. Do not
hardcode — enumerate the folder and take the first `.png` that is not a `_tmb` thumbnail; if
several match, prefer the largest. Then rename to `YYYY-MM-DD_category_keyword.png` on copy.

**Read the small print before writing it down.** Full-page screenshots of training decks carry
footnote-sized text that gets misread. Crop the region and upscale it 4–6× with Pillow, then read
the crop, rather than guessing at a blurry line. Pillow is often missing from the managed Python —
check the venv (`binaries/python/envs/default/Scripts/python.exe`) first. Rushing this step
produced three separate misreadings in one session (e.g. "过大拟" read as "对大致").

**Back up before appending**, once the board holds real content: the build step rewrites the whole
HTML, so copy the data file, the board, and the build script into `backups/<timestamp>/` first.

**Watch for internal contradictions in the source** and flag them to the user instead of silently
picking one reading. A deck that says "over 20%" in one place and "threshold X = 25%" in another
has a real ambiguity; record it as written and raise the question.

## Handoff checklist

1. `build.py` runs clean and prints the summary line
2. The board opens by double-click and shows real data, not the empty state
3. `.bat` is ASCII + CRLF + no BOM
4. Seed/demo records are labelled so the user can tell them from real ones — and once the
   first real record lands, delete the demos. Fake numbers sitting next to real ones in a
   personal knowledge base is worse than an empty board; promise the cleanup upfront.
5. Verify the rebuild actually landed: grep the output HTML for the new record's id or a
   distinctive phrase, rather than trusting the build script's exit code alone.
5. Tell the user which file holds the truth (`data.json`) and the one step to append a record
6. If the data folder lives outside any project workspace, check whether it is covered by
   the user's local backup scope and say so — an unbacked-up data folder is a silent risk
