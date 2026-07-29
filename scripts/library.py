#!/usr/bin/env python3
"""media-library-setup — organise a folder of photos and videos, then make it searchable.

Works on a normal folder on this computer. With Google Drive for Desktop installed,
that folder IS your Google Drive, and everything syncs back up on its own. No API,
no Cloud project, no OAuth.

Six commands, run in order:

    library.py check                         what is installed, what is missing
    library.py scan <folder>                 read-only. Writes scan.json
    library.py plan                          read-only. Writes plan.json
    library.py visualise                     read-only. Writes 2 HTML visuals
    library.py apply --approved-by "<who>"   moves files. Nothing is deleted
    library.py transcribe                    makes it searchable (costs a few dollars)

`apply` refuses to run unless a plan exists, the visuals were generated, and a person
is named. Every move is written to rollback.csv before it happens.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import os
import plistlib
import shutil
import subprocess
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

WORK = Path.home() / "active" / "media-library-setup"

VIDEO_EXTS = {".mp4", ".mov", ".m4v", ".avi", ".mkv", ".webm", ".mpg", ".mpeg", ".wmv"}
PHOTO_EXTS = {".jpg", ".jpeg", ".png", ".heic", ".gif", ".webp", ".tif", ".tiff",
              ".bmp", ".dng", ".cr2", ".nef", ".arw", ".raf"}
DOC_EXTS = {".pdf", ".doc", ".docx", ".ppt", ".pptx", ".xls", ".xlsx", ".key",
            ".numbers", ".pages", ".txt", ".rtf", ".csv"}
INDEX_SUFFIXES = (".transcript.md", ".summary.md", ".tags.json")

# macOS Finder tag colours: 1 grey, 2 green, 3 purple, 4 blue, 5 yellow, 6 red, 7 orange.
FINDER_TAGS = {
    "Videos": ("Purple", 3),
    "Photos": ("Blue", 4),
    "Documents": ("Orange", 7),
    "_Index": ("Grey", 1),
}
CATEGORIES = tuple(FINDER_TAGS)

WHISPER_MODEL = "whisper-1"
WHISPER_USD_PER_MIN = 0.006  # OpenAI list price for whisper-1

IS_MAC = sys.platform == "darwin"
IS_WIN = os.name == "nt"
IS_LINUX = not IS_MAC and not IS_WIN

# Files the operating system litters everywhere. Never counted, never moved.
JUNK = {".DS_Store", "Icon\r", "desktop.ini", ".localized"}


def category(p: Path) -> str:
    name = p.name
    if any(name.endswith(s) for s in INDEX_SUFFIXES) or name.startswith("_MANIFEST"):
        return "_Index"
    ext = p.suffix.lower()
    if ext in VIDEO_EXTS:
        return "Videos"
    if ext in PHOTO_EXTS:
        return "Photos"
    if ext in DOC_EXTS:
        return "Documents"
    return "Documents"


def is_junk(p: Path) -> bool:
    """OS litter only. Never a file the member would miss.

    `._name` is macOS's AppleDouble sidecar, but a person can legitimately name a
    file that. Treat it as litter only when the file it shadows is actually there,
    which is what makes it a sidecar rather than somebody's `._family-archive.mp4`.
    """
    if p.name in JUNK:
        return True
    if p.name.startswith("._"):
        return (p.parent / p.name[2:]).exists()
    return False


def open_file(p: Path) -> bool:
    """Open a file in whatever this computer uses. Returns False if it could not."""
    try:
        if IS_MAC:
            subprocess.run(["open", str(p)], check=False)
        elif IS_WIN:
            os.startfile(str(p))  # type: ignore[attr-defined]
        else:
            subprocess.run(["xdg-open", str(p)], check=False)
        return True
    except Exception:
        return False


def set_finder_tag(path: Path, cat: str) -> None:
    """Colour a folder in Finder. Cosmetic — a failure here is never fatal."""
    tag = FINDER_TAGS.get(cat)
    if not tag or not IS_MAC:
        return
    try:
        data = plistlib.dumps([f"{tag[0]}\n{tag[1]}"], fmt=plistlib.FMT_BINARY)
        subprocess.run(["/usr/bin/xattr", "-w", "-x",
                        "com.apple.metadata:_kMDItemUserTags", data.hex(), str(path)],
                       capture_output=True, check=False)
    except Exception:
        pass


def force_case(path: Path) -> None:
    """Make the folder on disk actually use `path`'s casing.

    macOS and Windows are case-insensitive, so mkdir("Videos") silently reuses an
    existing "videos" and the old casing sticks. Path.resolve() does not report the
    real casing either, so compare against the parent's actual listing.
    """
    try:
        actual = next((c.name for c in path.parent.iterdir()
                       if c.name.lower() == path.name.lower()), None)
    except OSError:
        return
    if actual is None or actual == path.name:
        return
    tmp = path.parent / f".__case__{path.name}"
    try:
        (path.parent / actual).rename(tmp)
        tmp.rename(path)
    except OSError:
        if tmp.exists():
            tmp.rename(path.parent / actual)


def plan_digest(plan: dict) -> str:
    """Fingerprint of what a plan would actually do.

    `visualise` stamps this into the plan; `apply` refuses unless it still matches.
    That is what ties the approval to the pictures the person was shown, instead of
    just "two HTML files exist somewhere".
    """
    payload = json.dumps({
        "root": plan.get("root"),
        "group_by": plan.get("group_by"),
        "moves": [[m["path"], m["to"]] for m in plan.get("moves", [])],
    }, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def human(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{n:.0f}{unit}"
        n /= 1024
    return f"{n:.1f}PB"


# ---------------------------------------------------------------- check

def find_drive_folders() -> list[Path]:
    """Where Google Drive for Desktop mounts, across the versions people actually have."""
    out = []
    cs = Path.home() / "Library" / "CloudStorage"
    if cs.is_dir():
        out += [p for p in cs.iterdir() if p.name.startswith("GoogleDrive-")]
    for legacy in (Path.home() / "Google Drive", Path("/Volumes/GoogleDrive")):
        if legacy.is_dir():
            out.append(legacy)
    for letter in "GHIJ":                      # Windows mounts as a drive letter
        d = Path(f"{letter}:/My Drive")
        if d.is_dir():
            out.append(d)
    return out


def cmd_check(args) -> None:
    """Report everything that is missing at once, in plain English, with the fix.

    Finding out one prerequisite at a time, each after a failed command, is what
    makes a setup feel broken to somebody non-technical. This says it all up front.
    """
    ok, todo = [], []

    ok.append(f"Python {sys.version_info.major}.{sys.version_info.minor} is here")

    drives = find_drive_folders()
    if drives:
        ok.append(f"Google Drive is on this computer ({drives[0]})")
    else:
        todo.append((
            "Google Drive is not on this computer yet",
            "This is the one that matters — it puts your Drive here as a normal folder.",
            "Install it from https://www.google.com/drive/download/ , sign in, and pick\n"
            '    "Stream files" when it asks. Then wait for the first sync to finish.'))

    for tool, why in (("ffmpeg", "reads the audio out of your videos"),
                      ("ffprobe", "measures how long each video is, to price the job")):
        if shutil.which(tool):
            ok.append(f"{tool} is installed ({why})")
        else:
            how = ("brew install ffmpeg\n"
                   "    No Homebrew? Install it from https://brew.sh first." if IS_MAC else
                   "winget install ffmpeg\n"
                   "    Then close this window and open a new one." if IS_WIN else
                   "sudo apt install ffmpeg")
            todo.append((f"{tool} is missing", f"Needed to transcribe — it {why}.", how))
            break

    try:
        import openai  # noqa: F401
        ok.append("The OpenAI package is installed")
    except ImportError:
        todo.append(("The OpenAI package is missing",
                     "The small piece of software that talks to the transcription service.",
                     "pip3 install openai"))

    key = os.environ.get("OPENAI_API_KEY", "")
    if key:
        ok.append(f"Your OpenAI key is set ({len(key)} characters, not shown)")
    else:
        todo.append((
            "No OpenAI key set",
            "Only needed for transcribing. Organising your folders works without it.",
            "1. Get a key at https://platform.openai.com/api-keys\n"
            "    2. Add credit at https://platform.openai.com/settings/organization/billing\n"
            "       — $5 covers about 14 hours of video\n"
            "    3. " + ('setx OPENAI_API_KEY "sk-your-key"\n'
                         "       then close this window and open a new one" if IS_WIN else
                         'echo \'export OPENAI_API_KEY="sk-your-key"\' >> ~/.zshrc'
                         " && source ~/.zshrc")))

    plat = "Mac" if IS_MAC else "Windows" if IS_WIN else "Linux"
    print(f"Checking what is already set up on this {plat}…\n")
    for line in ok:
        print(f"  READY   {line}")
    if not todo:
        print("\nEverything is ready. Nothing else to install.")
        if drives:
            print(f"\nYour Drive folder is at:\n  {drives[0]}")
            print("Point me at the folder inside it that holds your photos and videos.")
        return

    print(f"\n  {len(todo)} thing{'s' if len(todo) != 1 else ''} still to set up:\n")
    for i, (what, why, how) in enumerate(todo, 1):
        print(f"  {i}. {what}")
        print(f"     {why}")
        print("     " + how.replace("\n    ", "\n     ") + "\n")
    print("None of this is urgent — organising your folders needs only the first one.")
    print("Transcribing needs the rest. Run this check again after each step.")


# ---------------------------------------------------------------- scan

def cmd_scan(args) -> None:
    root = Path(args.folder).expanduser().resolve()
    if not root.is_dir():
        raise SystemExit(f"Not a folder: {root}")
    WORK.mkdir(parents=True, exist_ok=True)

    files, folders = [], []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if not d.startswith(".")]
        here = Path(dirpath)
        rel_dir = here.relative_to(root)
        if here != root:
            folders.append({"name": here.name,
                            "path": str(rel_dir),
                            "depth": len(rel_dir.parts)})
        for fn in filenames:
            p = here / fn
            if is_junk(p) or not p.is_file():
                continue
            try:
                size = p.stat().st_size
            except OSError:
                continue
            files.append({"name": fn,
                          "path": str(p.relative_to(root)),
                          "parent_path": str(rel_dir) if str(rel_dir) != "." else ".",
                          "depth": len(rel_dir.parts),
                          "size": size,
                          "category": category(p)})

    per_folder = Counter(f["parent_path"] for f in files)
    sparse = [f for f in folders if per_folder.get(f["path"], 0) <= 2]

    scan = {
        "scanned_at": datetime.now().isoformat(timespec="seconds"),
        "root": {"path": str(root), "name": root.name},
        "totals": {
            "files": len(files),
            "folders": len(folders),
            "max_depth": max([f["depth"] for f in folders], default=0),
            "sparse_folders": len(sparse),
            "bytes": sum(f["size"] for f in files),
        },
        "by_category": dict(Counter(f["category"] for f in files)),
        "folders": folders,
        "files": files,
    }
    (WORK / "scan.json").write_text(json.dumps(scan, indent=2))

    t = scan["totals"]
    print(f"Scanned '{root.name}' — read only, nothing changed.")
    print(f"  {t['files']} files ({human(t['bytes'])}) in {t['folders']} folders, "
          f"{t['max_depth']} levels deep")
    print(f"  {t['sparse_folders']} folders hold 2 files or fewer")
    for cat, n in sorted(scan["by_category"].items(), key=lambda kv: -kv[1]):
        print(f"  {cat:<12} {n}")
    print(f"\nWrote {WORK / 'scan.json'}")


# ---------------------------------------------------------------- plan

CATEGORY_ISH = {c.lower() for c in CATEGORIES} | {
    "images", "docs", "index", "raw videos", "raw photos", "edits",
    "testimonials", "text", "metadata", "transcripts", "summaries",
    "footage", "stills", "clips",
}


def detect_shape(scan: dict) -> str:
    """One shoot (subfolders are categories) or a whole library (subfolders are events)?

    Getting this wrong is the easiest way to produce a nonsense plan — pointing at a
    single shoot and grouping by event would turn each category folder into its own event.
    """
    level1 = [f["name"].strip().lower() for f in scan["folders"] if f["depth"] == 1]
    if not level1:
        return "flat"
    if sum(1 for n in level1 if n in CATEGORY_ISH) >= max(1, len(level1) // 2):
        return "flat"
    loose = sum(1 for f in scan["files"] if f["parent_path"] == ".")
    if loose > len(scan["files"]) // 2:
        return "flat"
    return "event"


def cmd_plan(args) -> None:
    scan = json.loads((WORK / "scan.json").read_text())
    group_by = args.group_by or detect_shape(scan)
    if not args.group_by:
        why = ("its subfolders are already categories, so this is one shoot"
               if group_by == "flat" else "its subfolders look like separate events")
        print(f"Detected: {group_by} layout ({why}). Override with --group-by.")

    moves = []
    for f in scan["files"]:
        if group_by == "flat":
            event = ""
        else:
            event = (f["parent_path"].split("/")[0]
                     if f["parent_path"] != "." else "Unsorted")
        dest = f"{event}/{f['category']}" if event else f["category"]
        moves.append({"path": f["path"], "name": f["name"], "from": f["parent_path"],
                      "to": dest, "category": f["category"], "event": event})

    dests = sorted({m["to"] for m in moves})
    already = sum(1 for m in moves if m["from"] == m["to"])
    events = {m["event"] for m in moves if m["event"]}
    plan = {
        "planned_at": datetime.now().isoformat(timespec="seconds"),
        "root": scan["root"],
        "group_by": group_by,
        "structure": dests,
        "counts": {
            "files_total": len(moves),
            "files_moving": len(moves) - already,
            "files_already_correct": already,
            "folders_before": scan["totals"]["folders"],
            "folders_after": len(dests) + len(events),
            "depth_before": scan["totals"]["max_depth"],
            "depth_after": 2 if group_by != "flat" else 1,
        },
        "per_destination": dict(Counter(m["to"] for m in moves)),
        "moves": moves,
        "approved": False,
    }
    (WORK / "plan.json").write_text(json.dumps(plan, indent=2))

    c = plan["counts"]
    print("Planned — still read only, nothing has moved.")
    print(f"  {c['folders_before']} folders ({c['depth_before']} deep)"
          f"  ->  {c['folders_after']} folders ({c['depth_after']} deep)")
    print(f"  {c['files_moving']} files will move, {c['files_already_correct']} already correct")
    print("  Nothing is deleted. Every move is logged and reversible.")
    print(f"\nWrote {WORK / 'plan.json'}")


# ---------------------------------------------------------------- visualise

SWATCH = {"Videos": "#6736E2", "Photos": "#00A9A5",
          "Documents": "#F5A524", "_Index": "#64748B"}


def cmd_visualise(args) -> None:
    plan = json.loads((WORK / "plan.json").read_text())
    scan = json.loads((WORK / "scan.json").read_text())
    c = plan["counts"]
    root_name = html.escape(plan["root"]["name"])
    events = sorted({html.escape(m["event"]) for m in plan["moves"] if m["event"]})
    per_dest = plan["per_destination"]

    # Full paths, not leaf names — a list of leaf names repeats "Raw Videos" and proves nothing.
    files_in = Counter(f["parent_path"] for f in scan["files"])
    deepest = sorted(scan["folders"], key=lambda x: (-x["depth"], x["path"]))[:12]
    before_rows = "".join(
        f'<li class="deep{" sparse" if files_in.get(f["path"], 0) <= 2 else ""}">'
        f'<span class="path">{html.escape(f["path"])}</span>'
        f'<span class="muted">{files_in.get(f["path"], 0)} file'
        f'{"s" if files_in.get(f["path"], 0) != 1 else ""}</span></li>'
        for f in deepest
    ) or '<li class="muted">no subfolders</li>'
    if len(scan["folders"]) > len(deepest):
        before_rows += f'<li class="more">+ {len(scan["folders"]) - len(deepest)} more folders</li>'

    def event_block(ev: str) -> str:
        raw = html.unescape(ev)
        def n_of(cat: str) -> int:
            return per_dest.get(f"{raw}/{cat}" if raw else cat, 0)
        rows = "".join(
            f'<li><span class="dot" style="background:{SWATCH[cat]}"></span>{cat}'
            f'<span class="count">{n_of(cat)} file{"s" if n_of(cat) != 1 else ""}</span></li>'
            for cat in CATEGORIES if n_of(cat)
        )
        return f'<div class="event"><h4>{ev or root_name}</h4><ul class="cats">{rows}</ul></div>'

    SHOWN = 4
    after_blocks = "".join(event_block(e) for e in events[:SHOWN]) or event_block("")
    if len(events) > SHOWN:
        rest = events[SHOWN:]
        after_blocks += (f'<div class="rest"><b>+ {len(rest)} more event folder'
                         f'{"s" if len(rest) != 1 else ""}</b>, each with the same folders'
                         f'<span>{", ".join(rest[:6])}{" &hellip;" if len(rest) > 6 else ""}</span></div>')

    css = """
  :root { --purple:#6736E2; --ink:#0A0A0A; --cloud:#EDEFF7; }
  * { box-sizing:border-box; }
  body { margin:0; padding:48px; font:16px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
         color:var(--ink); background:#fff; }
  h1 { font-size:30px; margin:0 0 6px; letter-spacing:-.02em; }
  .sub { color:#5B6178; margin:0 0 32px; }
  .grid { display:grid; grid-template-columns:1fr 1fr; gap:28px; align-items:start; }
  .panel { border:1px solid #E3E6F0; border-radius:16px; padding:24px; background:#fff; }
  .panel.after { border-color:var(--purple); box-shadow:0 8px 28px rgba(103,54,226,.10); }
  .panel h2 { font-size:13px; text-transform:uppercase; letter-spacing:.09em;
              margin:0 0 16px; color:#5B6178; }
  .panel.after h2 { color:var(--purple); }
  ul { list-style:none; margin:0; padding:0; }
  .deep { padding:7px 10px; border-radius:8px; background:var(--cloud); margin-bottom:5px;
          font-size:13.5px; display:flex; justify-content:space-between; gap:12px; }
  .deep .path { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
  .deep.sparse { background:#FFECEC; }
  .deep.sparse .muted { color:#C4342B; font-weight:600; }
  .more { padding:7px 10px; font-size:13px; color:#8A90A6; }
  .muted { color:#8A90A6; font-size:12px; flex:0 0 auto; }
  .rest { border:1px dashed #D5C4FF; border-radius:11px; padding:14px 16px; font-size:13.5px; }
  .rest span { display:block; color:#5B6178; font-size:12.5px; margin-top:5px; }
  .event { margin-bottom:18px; }
  .event h4 { margin:0 0 8px; font-size:15px; }
  .cats li { display:flex; align-items:center; gap:10px; padding:8px 12px;
             border-radius:9px; background:var(--cloud); margin-bottom:5px; font-size:14px; }
  .dot { width:12px; height:12px; border-radius:3px; flex:0 0 auto; }
  .count { margin-left:auto; color:#5B6178; font-size:13px; }
  .note { margin:14px 0 0; font-size:13px; color:#5B6178; }
  .stats { display:flex; gap:14px; margin-top:32px; flex-wrap:wrap; }
  .stat { flex:1 1 180px; border:1px solid #E3E6F0; border-radius:14px; padding:18px 20px; }
  .stat b { display:block; font-size:26px; letter-spacing:-.02em; }
  .stat span { color:#5B6178; font-size:13px; }
  .safe { margin-top:28px; padding:16px 20px; border-radius:12px;
          background:#F2EDFF; border:1px solid #D5C4FF; font-size:14px; }
  @media (max-width:820px) { .grid { grid-template-columns:1fr; } }
"""

    v1 = f"""<!doctype html><meta charset="utf-8">
<title>Proposed folder structure — {root_name}</title>
<style>{css}</style>
<h1>Proposed folder structure</h1>
<p class="sub">{root_name} · nothing has been changed yet</p>
<div class="grid">
  <div class="panel"><h2>Now — {c['folders_before']} folders, {c['depth_before']} levels deep</h2>
    <ul>{before_rows}</ul>
    <p class="note">Red rows hold two files or fewer. There
    {"are" if scan['totals']['sparse_folders'] != 1 else "is"}
    <b>{scan['totals']['sparse_folders']}</b> of them.</p></div>
  <div class="panel after"><h2>Proposed — {c['folders_after']} folders, {c['depth_after']} levels deep</h2>
    {after_blocks}</div>
</div>
<div class="stats">
  <div class="stat"><b>{c['files_total']}</b><span>files in the library</span></div>
  <div class="stat"><b>{c['files_moving']}</b><span>files that would move</span></div>
  <div class="stat"><b>0</b><span>files deleted, ever</span></div>
  <div class="stat"><b>{scan['totals']['sparse_folders']}</b><span>near-empty folders removed</span></div>
</div>
<div class="safe"><b>Nothing is deleted.</b> Files are moved, never removed, and every single move
is written to a rollback file first — so the whole thing can be put back exactly as it was.</div>
"""

    lanes = "".join(
        f'<div class="lane"><div class="lane-head" style="--c:{SWATCH[cat]}">'
        f'<span class="dot" style="background:{SWATCH[cat]}"></span><b>{cat}</b>'
        f'<span class="n">{sum(v for k, v in per_dest.items() if k.split("/")[-1] == cat)} files</span>'
        f'</div><p>{desc}</p></div>'
        for cat, desc in [
            ("Videos", "Every video, in one flat scrollable folder. "
                       "The shot type lives in the filename, not in a subfolder."),
            ("Photos", "Every photo and image together, so you can flick through them."),
            ("Documents", "PDFs, decks, sheets and contracts for that event."),
            ("_Index", "The searchable layer: a transcript, a summary and tags for every "
                       "clip. This is what lets you ask for a moment instead of a filename."),
        ])

    v2 = f"""<!doctype html><meta charset="utf-8">
<title>Where everything is stored — {root_name}</title>
<style>
  :root {{ --purple:#6736E2; --ink:#0A0A0A; --cloud:#EDEFF7; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; padding:48px; font:16px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
         color:var(--ink); background:#fff; }}
  h1 {{ font-size:30px; margin:0 0 6px; letter-spacing:-.02em; }}
  .sub {{ color:#5B6178; margin:0 0 34px; }}
  .flow {{ display:grid; grid-template-columns:repeat(4,1fr); gap:34px; margin-bottom:38px; }}
  .node {{ position:relative; border:1px solid #E3E6F0; border-radius:14px;
           padding:16px 20px; background:#fff; font-size:13.5px; color:#5B6178; }}
  .node b {{ display:block; font-size:15px; color:var(--ink); margin-bottom:3px; }}
  .node.pri {{ border-color:var(--purple); background:#F2EDFF; }}
  .node + .node::before {{ content:"\\2192"; position:absolute; left:-26px; top:50%;
                           transform:translateY(-50%); color:#B3B8CC; font-size:20px; }}
  .lanes {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(240px,1fr)); gap:18px; }}
  .lane {{ border:1px solid #E3E6F0; border-radius:14px; overflow:hidden; }}
  .lane-head {{ display:flex; align-items:center; gap:9px; padding:14px 18px;
                background:var(--cloud); border-bottom:3px solid var(--c); }}
  .lane-head .n {{ margin-left:auto; font-size:13px; color:#5B6178; }}
  .dot {{ width:12px; height:12px; border-radius:3px; }}
  .lane p {{ margin:0; padding:16px 18px; font-size:14px; color:#3B4058; }}
  .ask {{ margin-top:34px; border:1px solid #D5C4FF; background:#F2EDFF;
          border-radius:14px; padding:22px 26px; }}
  .ask h3 {{ margin:0 0 10px; font-size:15px; }}
  .ask code {{ display:block; background:#fff; border:1px solid #E3E6F0; border-radius:9px;
               padding:10px 14px; margin:7px 0; font-size:13.5px; }}
  @media (max-width:900px) {{
    .flow {{ grid-template-columns:1fr; gap:12px; }}
    .node + .node::before {{ display:none; }}
  }}
</style>
<h1>Where everything is stored</h1>
<p class="sub">{root_name} · {c['files_total']} files across
   {len(events) or 1} folder{"s" if len(events) != 1 else ""}</p>
<div class="flow">
  <div class="node"><b>Your files</b>photos, videos, documents</div>
  <div class="node pri"><b>{root_name}</b>the library folder, synced to Google Drive</div>
  <div class="node"><b>One folder per event</b>{", ".join(events[:2]) or "single flat library"}
    {f"and {len(events) - 2} more" if len(events) > 2 else ""}</div>
  <div class="node"><b>Four folders</b>and that is the deepest it goes</div>
</div>
<div class="lanes">{lanes}</div>
<div class="ask">
  <h3>What this buys you — ask in plain English, get the clip</h3>
  <code>find the bit where someone talks about pricing</code>
  <code>pull every testimonial from the May workshop</code>
  <code>what footage do we have of the room filling up</code>
  <p style="margin:10px 0 0;padding:0;font-size:13.5px;color:#5B6178">
  Answered from the <b>_Index</b> folder, which is why it exists.</p>
</div>
"""

    p1, p2 = WORK / "1-folder-structure.html", WORK / "2-where-things-are-stored.html"
    p1.write_text(v1)
    p2.write_text(v2)
    # Record WHAT was shown, so apply can refuse a plan that changed afterwards.
    plan["shown_digest"] = plan_digest(plan)
    (WORK / "plan.json").write_text(json.dumps(plan, indent=2))
    print(f"Wrote:\n  {p1}\n  {p2}")
    if not args.no_open:
        opened = all(open_file(p) for p in (p1, p2))
        if opened:
            print("\nBoth visuals opened in the browser.")
        else:
            print("\nCould not open them automatically. Open these two files in a browser —"
                  "\nthey must be looked at before anything moves:")
            for p in (p1, p2):
                print(f"  {p}")
    if not IS_MAC:
        print("\nNote: folder colours are a Mac feature. On this computer the folders are"
              "\nnamed and organised the same way, just without the colour tags.")


# ---------------------------------------------------------------- apply

def cmd_apply(args) -> None:
    plan_path = WORK / "plan.json"
    if not plan_path.exists():
        raise SystemExit("No plan.json. Run scan, plan and visualise first.")
    plan = json.loads(plan_path.read_text())

    visuals = [WORK / "1-folder-structure.html", WORK / "2-where-things-are-stored.html"]
    if not all(v.exists() for v in visuals):
        raise SystemExit("The visuals have not been generated, so nobody has seen this plan.\n"
                         "Run: library.py visualise")
    # A name of spaces is not an approval, and neither is an initial.
    approver = (args.approved_by or "").strip()
    if len(approver) < 2:
        raise SystemExit(
            "Refusing to move anything without approval.\n"
            "Show the two visuals to the owner, get a clear yes, then re-run with:\n"
            '  library.py apply --approved-by "<their name>"')

    # The gate has to bind to the plan they were actually shown. Without this, old
    # visuals from a different library would satisfy "the visuals exist", and a plan
    # edited after the showing would sail straight through.
    shown = plan.get("shown_digest")
    if shown != plan_digest(plan):
        raise SystemExit(
            "This plan has changed since the visuals were made, so what was approved\n"
            "is not what would happen. Re-run:  library.py visualise\n"
            "then show them again before applying.")

    root = Path(plan["root"]["path"])
    todo = [m for m in plan["moves"] if m["from"] != m["to"]]
    print(f"Applying: {len(todo)} files to move. Nothing will be deleted.")

    made: set[str] = set()
    moved = skipped = 0
    failures: list[tuple[str, str]] = []
    emptied: set[Path] = set()
    # Append, never truncate. Truncating would erase the history of an earlier run
    # and make the library unrestorable after a retry.
    rb = WORK / "rollback.csv"
    new_file = not rb.exists()
    with rb.open("a", newline="") as fh:
        w = csv.writer(fh)
        if new_file:
            w.writerow(["name", "moved_from", "moved_to", "at"])
        for m in todo:
            src = root / m["path"]
            if not src.exists() and not src.is_symlink():
                skipped += 1
                continue
            dest_dir = root / m["to"]
            if m["to"] not in made:
                try:
                    dest_dir.mkdir(parents=True, exist_ok=True)
                    force_case(dest_dir)
                    set_finder_tag(dest_dir, m["category"])
                except OSError as e:
                    failures.append((m["name"], f"could not create {m['to']}: {e.strerror}"))
                    continue
                made.add(m["to"])
                print(f"  {m['to']}")
            dest = dest_dir / m["name"]
            # Never overwrite. Compare the paths themselves, not their resolved
            # targets — a symlink pointing AT the destination resolves equal to it,
            # which would skip the guard and clobber the real file.
            if (dest.exists() or dest.is_symlink()) and dest != src:
                stem, ext, n = dest.stem, dest.suffix, 2
                while dest.exists() or dest.is_symlink():
                    dest = dest_dir / f"{stem}-{n}{ext}"
                    n += 1
            # One file failing must not abandon the rest half-moved, and the log must
            # only ever claim moves that really happened — so move first, then record.
            try:
                shutil.move(str(src), str(dest))
            except Exception as e:
                failures.append((m["name"], f"{type(e).__name__}: {e}"))
                continue
            w.writerow([dest.name, m["from"], m["to"],
                        datetime.now().isoformat(timespec="seconds")])
            fh.flush()
            emptied.add((root / m["from"]) if m["from"] != "." else root)
            moved += 1

    # Only clear folders this plan actually emptied, and only when they are truly
    # empty. Sweeping every empty folder under the root would delete folders the
    # member made on purpose and had nothing to do with the move.
    removed = 0
    candidates = {p for p in emptied if p != root}
    while candidates:
        nxt: set[Path] = set()
        for d in candidates:
            if not d.is_dir() or d == root or root not in d.parents:
                continue
            if any(True for _ in d.iterdir()):
                continue          # anything at all left, including junk — leave it
            parent = d.parent
            try:
                d.rmdir()
                removed += 1
                if parent != root:
                    nxt.add(parent)
            except OSError:
                pass
        candidates = nxt

    plan["approved"] = True
    plan["approved_by"] = approver
    plan["applied_at"] = datetime.now().isoformat(timespec="seconds")
    plan_path.write_text(json.dumps(plan, indent=2))

    print(f"\nDone. {moved} files moved, 0 deleted.")
    if skipped:
        print(f"  {skipped} files were already gone (moved by an earlier run).")
    print(f"  {removed} emptied folders cleared away.")
    if failures:
        print(f"\n  {len(failures)} files could NOT be moved and are untouched where they were:")
        for name, why in failures[:10]:
            print(f"    {name} — {why}")
        if len(failures) > 10:
            print(f"    …and {len(failures) - 10} more")
        print("  Re-run apply to retry just those.")
    print(f"Rollback log: {rb}")


# ---------------------------------------------------------------- transcribe

def video_minutes(p: Path) -> float:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "default=nw=1:nk=1", str(p)],
                       capture_output=True, text=True)
    try:
        return float(r.stdout.strip()) / 60
    except ValueError:
        return 0.0


def cmd_transcribe(args) -> None:
    plan = json.loads((WORK / "plan.json").read_text())
    if not plan.get("approved"):
        raise SystemExit(
            "The structure has not been approved yet, so there is nothing settled to\n"
            "index. Run scan, plan, visualise and apply first — transcribing before the\n"
            "files have moved would write the index into folders that are about to change.")
    root = Path(plan["root"]["path"])
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        raise SystemExit("ffmpeg is needed to pull audio out of video.\n"
                         "  Mac:   brew install ffmpeg\n"
                         "  Win:   winget install ffmpeg\n"
                         "  Linux: sudo apt install ffmpeg")

    videos = sorted(p for p in root.rglob("*")
                    if p.is_file() and not p.is_symlink()
                    and p.suffix.lower() in VIDEO_EXTS and not is_junk(p))
    links = [p for p in root.rglob("*")
             if p.is_symlink() and p.suffix.lower() in VIDEO_EXTS]
    if links:
        print(f"Skipping {len(links)} shortcut(s) — they point outside this folder and "
              f"will not be sent anywhere.")
    if not videos:
        raise SystemExit("No videos found. Run scan and apply first.")

    todo = []
    for v in videos:
        index_dir = v.parent.parent / "_Index" if v.parent.name in CATEGORIES else v.parent / "_Index"
        if (index_dir / f"{v.name}.transcript.md").exists():
            continue
        todo.append((v, index_dir))

    if not todo:
        print("Every video already has a transcript. Nothing to do.")
        return

    print(f"Measuring {len(todo)} videos…")
    minutes = sum(video_minutes(v) for v, _ in todo)
    cost = minutes * WHISPER_USD_PER_MIN
    mins = f"{minutes:.0f}" if minutes >= 10 else f"{minutes:.1f}"
    total_bytes = sum(v.stat().st_size for v, _ in todo if v.exists())
    print(f"\n  {len(todo)} videos, {mins} minutes of audio")
    print(f"  Estimated cost: ${max(cost, 0.01):.2f} USD (OpenAI {WHISPER_MODEL}, "
          f"${WHISPER_USD_PER_MIN}/min)")
    print("  This is billed to your own OpenAI account.")

    # Drive for Desktop streams by default: reading a video pulls the whole file down.
    # On a big library that can fill the disk long before the API bill matters.
    free = shutil.disk_usage(root).free
    print(f"\n  Reads {human(total_bytes)} of video. On a streaming Drive that downloads"
          f" each file as it goes.")
    print(f"  Free disk right now: {human(free)}.")
    if total_bytes > free * 0.8:
        print("\n  WARNING: that is close to or more than the free space available.")
        print("  Do it in batches — transcribe one event folder at a time by pointing")
        print("  scan at that folder, or free up space first. Drive normally evicts its")
        print("  cache as it goes, but do not count on it with this little headroom.")
    print()

    if not args.yes:
        raise SystemExit("Nothing has been sent. Re-run with --yes to go ahead.")

    if not os.environ.get("OPENAI_API_KEY"):
        raise SystemExit("OPENAI_API_KEY is not set.\n"
                         "  Get a key at https://platform.openai.com/api-keys\n"
                         '  Then: export OPENAI_API_KEY="sk-..."')
    try:
        from openai import OpenAI
    except ImportError:
        raise SystemExit("The OpenAI library is missing. Run: pip3 install openai")

    client = OpenAI()
    # Paid text is banked here the moment it arrives, so a later disk or permission
    # failure never turns into paying OpenAI twice for the same audio.
    bank = WORK / "transcribed"
    bank.mkdir(parents=True, exist_ok=True)

    done = failed = 0
    for i, (v, index_dir) in enumerate(todo, 1):
        print(f"  [{i}/{len(todo)}] {v.name}")
        banked = bank / f"{v.name}.txt"
        chunks: list[Path] = []
        try:
            if banked.exists():
                print("      already paid for on an earlier run — reusing, no charge")
                text = banked.read_text()
            else:
                # 16kHz mono at 32kbps holds about an hour inside the 25MB request cap.
                # Anything longer has to be split or the API rejects the whole file.
                audio = WORK / "tmp-audio.mp3"
                subprocess.run(["ffmpeg", "-y", "-i", str(v), "-vn", "-ac", "1",
                                "-ar", "16000", "-b:a", "32k", str(audio)],
                               capture_output=True, check=True)
                CAP = 24 * 1024 * 1024
                if audio.stat().st_size > CAP:
                    seg = WORK / "chunk-%03d.mp3"
                    subprocess.run(["ffmpeg", "-y", "-i", str(audio), "-f", "segment",
                                    "-segment_time", "3000", "-c", "copy", str(seg)],
                                   capture_output=True, check=True)
                    chunks = sorted(WORK.glob("chunk-*.mp3"))
                    print(f"      long recording — sent in {len(chunks)} parts")
                else:
                    chunks = [audio]

                parts = []
                for c in chunks:
                    with c.open("rb") as fh:
                        r = client.audio.transcriptions.create(
                            model=WHISPER_MODEL, file=fh, response_format="text")
                    parts.append(r if isinstance(r, str) else getattr(r, "text", ""))
                text = "\n".join(parts)
                banked.write_text(text)   # money spent — record it before anything else

            # Only now, so a folder of unreadable files does not leave empty _Index dirs.
            index_dir.mkdir(parents=True, exist_ok=True)
            set_finder_tag(index_dir, "_Index")
            (index_dir / f"{v.name}.transcript.md").write_text(
                f"# Transcript — {v.name}\n\n{text.strip()}\n")
            done += 1
        except subprocess.CalledProcessError:
            print("      could not read that file, skipping")
            failed += 1
        except Exception as e:
            print(f"      failed: {type(e).__name__}. Re-run to retry just this one.")
            failed += 1
        finally:
            (WORK / "tmp-audio.mp3").unlink(missing_ok=True)
            for c in chunks:
                if c.name.startswith("chunk-"):
                    c.unlink(missing_ok=True)

    print(f"\nTranscribed {done} videos" + (f", {failed} failed" if failed else "") + ".")
    print("Re-run this command any time — finished ones are skipped.")


# ---------------------------------------------------------------- main

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("check", help="what is installed, what is still needed")
    c.set_defaults(func=cmd_check)

    s = sub.add_parser("scan", help="read-only survey of a folder")
    s.add_argument("folder")
    s.set_defaults(func=cmd_scan)

    p = sub.add_parser("plan", help="build the proposed structure (no writes)")
    p.add_argument("--group-by", choices=["event", "flat"], default=None,
                   help="auto-detected when omitted")
    p.set_defaults(func=cmd_plan)

    v = sub.add_parser("visualise", help="render the two approval visuals")
    v.add_argument("--no-open", action="store_true")
    v.set_defaults(func=cmd_visualise)

    a = sub.add_parser("apply", help="move the files — needs approval")
    a.add_argument("--approved-by", default="")
    a.set_defaults(func=cmd_apply)

    t = sub.add_parser("transcribe", help="make it searchable (costs a few dollars)")
    t.add_argument("--yes", action="store_true", help="confirm the cost and go ahead")
    t.set_defaults(func=cmd_transcribe)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
