#!/usr/bin/env bash
# Offline contract check for media-library-setup.
# No Drive calls, no network, no writes outside a temp dir.
set -euo pipefail

skill_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

python3 -c "import ast,sys; ast.parse(open(sys.argv[1]).read())" "$skill_dir/scripts/library.py"

python3 - "$skill_dir" <<'PY'
import importlib.util
import json
import pathlib
import sys
import tempfile

root = pathlib.Path(sys.argv[1])
skill = (root / "SKILL.md").read_text()
setup_prompt = (root / "SETUP-PROMPT.md").read_text()
readme = (root / "README.md").read_text() if (root / "README.md").exists() else ""
rules = (root / "references" / "structure-rules.md").read_text()
both = skill + rules

spec = importlib.util.spec_from_file_location("lib", root / "scripts" / "library.py")
lib = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lib)
src = (root / "scripts" / "library.py").read_text()

# --- the approval gate must be enforced in code, not just described in prose
class A:
    approved_by = ""
gate_errors = []
with tempfile.TemporaryDirectory() as td:
    lib.WORK = pathlib.Path(td)
    try:
        lib.cmd_apply(A())
        gate_errors.append("apply ran with no plan.json")
    except SystemExit:
        pass
    # plan present, visuals absent -> must still refuse
    (lib.WORK / "plan.json").write_text(json.dumps({"root": {"id": "x", "name": "x"}, "moves": []}))
    try:
        lib.cmd_apply(A())
        gate_errors.append("apply ran without the visuals being generated")
    except SystemExit:
        pass
    # visuals present but no approver -> must still refuse
    (lib.WORK / "1-folder-structure.html").write_text("x")
    (lib.WORK / "2-where-things-are-stored.html").write_text("x")
    try:
        lib.cmd_apply(A())
        gate_errors.append("apply ran with no --approved-by")
    except SystemExit:
        pass
    # whitespace is not a name
    class W: approved_by = "   "
    try:
        lib.cmd_apply(W())
        gate_errors.append("apply accepted whitespace as an approver")
    except SystemExit:
        pass
    # a plan that changed since the visuals were shown must be refused
    class N: approved_by = "Real Person"
    stale = {"root": {"path": str(lib.WORK), "name": "x"},
             "group_by": "flat",
             "moves": [{"path": "a.mp4", "to": "Videos", "from": ".", "name": "a.mp4",
                        "category": "Videos", "event": ""}]}
    stale["shown_digest"] = "0000000000000000"
    (lib.WORK / "plan.json").write_text(json.dumps(stale))
    try:
        lib.cmd_apply(N())
        gate_errors.append("apply ran on a plan that changed after the visuals")
    except SystemExit:
        pass
    # transcribe must not run before the structure is approved
    class T: yes = True
    (lib.WORK / "plan.json").write_text(json.dumps({**stale, "approved": False}))
    try:
        lib.cmd_transcribe(T())
        gate_errors.append("transcribe ran before apply was approved")
    except SystemExit:
        pass

# --- shape detection must not mistake a single event for a library
one_event = {"folders": [{"name": n, "depth": 1, "path": n, "id": n} for n in
                         ("Videos", "Photos", "_Index")],
             "files": [{"parent_path": "Videos"}]}
a_library = {"folders": [{"name": n, "depth": 1, "path": n, "id": n} for n in
                         ("Brisbane May", "Sydney June", "Perth July")],
             "files": [{"parent_path": "Brisbane May"}]}

# Phrases that must never appear in the shipped docs: personal contacts, and any
# "go ask a human" fallback. Assembled from words so this list does not itself trip
# a publishing scan looking for those same phrases.
BANNED = tuple(" ".join(w) for w in (
    ("@gmail.com",), ("@selrai",), ("@selrgroup",), ("+61",), ("Luke",),
    ("ask", "us"), ("contact", "us"), ("message", "us"), ("reach", "out"),
    ("if", "you", "get", "stuck"), ("tell", "Luke"), ("ask", "Luke")))

checks = {
    "approval gate enforced in code": not gate_errors,
    "single event detected as flat": lib.detect_shape(one_event) == "flat",
    "library detected as event": lib.detect_shape(a_library) == "event",
    "two-level ceiling stated": "Two levels" in skill or "two levels" in skill.lower(),
    "structure rules are routed to": "structure-rules.md" in skill,
    "four canonical folders defined": set(lib.CATEGORIES) == {
        "Videos", "Photos", "Documents", "_Index"},
    "every category has a finder colour": set(lib.FINDER_TAGS) == set(lib.CATEGORIES),
    "cost is quoted per minute": lib.WHISPER_USD_PER_MIN > 0,
    "setup guide is routed to": "setup.md" in skill,
    "preflight check exists and is first": "cmd_check" in src and skill.index("check") < skill.index("scan"),
    "check covers every prerequisite": all(k in src for k in
        ("find_drive_folders", "ffmpeg", "openai", "OPENAI_API_KEY")),
    "cost is explained before setup": skill.index("$0.36") < skill.index("transcribe --yes"),
    "tells Claude not to hand commands to the user": "run it yourself" in skill,
    "ends by handing over the report": "skill-install-report" in skill,
    "key is never echoed back": "Never print the key back" in skill,
    "opens visuals on every platform": all(k in src for k in ("os.startfile", "xdg-open", '"open"')),
    "never silently skips the approval visuals": "Could not open them automatically" in src,
    "windows instructions present": "winget" in skill and "setx" in skill,
    "honest that colours are mac-only": "Mac-only" in skill or "a Mac feature" in src,
    "cost is stated before spending": "cost" in skill.lower() and "--yes" in skill,
    "os junk files are ignored": lib.is_junk(pathlib.Path(".DS_Store"))
                                 and not lib.is_junk(pathlib.Path("clip.mp4")),
    "a real ._ file is not treated as junk": not lib.is_junk(
        pathlib.Path("/nonexistent-dir/._family-archive.mp4")),
    "rollback appends, never truncates": 'rb.open("a"' in src,
    "move happens before the log claims it": src.index("shutil.move(str(src)") <
                                             src.index('w.writerow([m["name"], dest.name'),
    "transcript name keeps the extension": 'f"{v.name}.transcript.md"' in src
                                           and 'f"{v.stem}.transcript.md"' not in src,
    "paid text is banked before any disk work": "banked.write_text(text)" in src,
    "long audio is chunked under the API cap": "segment_time" in src,
    "symlinks are never uploaded": "not p.is_symlink()" in src,
    "html is escaped in the visuals": "html.escape" in src,
    "approval binds to the plan shown": "shown_digest" in src and "plan_digest" in src,
    "categorises by extension": (lib.category(pathlib.Path("a.mp4")) == "Videos"
                                 and lib.category(pathlib.Path("a.jpg")) == "Photos"
                                 and lib.category(pathlib.Path("a.pdf")) == "Documents"
                                 and lib.category(pathlib.Path("a.transcript.md")) == "_Index"),
    "no-delete promise stated": "No file is ever deleted" in skill,
    "rollback documented": "rollback.csv" in skill,
    "no-delete boundary is explicit": "Never delete a file" in skill,
    "transcription is built in": "transcribe" in skill,
    "uses Drive for Desktop, not the API": "Drive for Desktop" in skill,
    "self-heals rather than escalating": "self-heal" in skill.lower(),
    "publishing firewall: no names or contacts": not any(b in both for b in BANNED),
    # --- hardening round 1: one check per issue found, so none can come back
    "each library gets its own state folder": "library_slug" in src and "use_library" in src,
    "state dir is overridable for testing": "MEDIA_LIBRARY_WORK_DIR" in src,
    "empty library stops at scan": "no photos, videos or documents" in src,
    "never asks approval for a no-op": "nothing to approve" in src,
    "transcribe is honest when there are no videos": "nothing to transcribe" in src
                                                     and "Run scan and apply first" not in src,
    "layout message handles no-subfolder case": "everything sits in one folder" in src,
    "docs agree that nothing is renamed": "Nothing is renamed" in rules
                                          and "Files get renamed to" not in rules,
    "organising is stated as free of prerequisites": "Only Google Drive for Desktop is required" in skill,
    # --- hardening round 2
    "rollback command exists": "cmd_rollback" in src and '"rollback"' in src,
    "rollback is documented for the owner": "library.py rollback" in skill,
    "rollback log records the original name": '"original_name"' in src,
    "status command exists": "cmd_status" in src,
    "cost preview exits clean, not as an error": "Nothing has been sent and nothing has been charged" in src,
    "delete promise distinguishes files from folders": "No file is ever deleted" in skill,
    "folder-cleared stat counts what apply really clears": "will_clear" in src,
    "says it works on any folder, not only Drive": "any folder on their computer" in skill,
    # --- hardening round 3
    "rollback preview exits clean, not as an error": "Nothing has moved. To go ahead" in src
                                                     and "raise SystemExit(\n            '\\nNothing has moved" not in src,
    "status is truthful after an undo": "rolled_back_at" in src,
    "unreadable video is named, not silently priced": "they may be damaged" in src and "unreadable" in src,
    "renames are decided at plan time, before approval": '"renames"' in src
                                                         and 'm["final_name"]' in src,
    "apply uses the name the plan showed": 'm.get("final_name", m["name"])' in src,
    "partial undo does not claim full success": 'else:\n        print("The library is back' in src,
    # --- independent review of the rollback and per-library code
    "partial undo keeps failed rows retryable": "unfinished" in src,
    "status distinguishes a partial undo": "partial_rollback_at" in src,
    "apply names the library it will change": "About to change:" in src,
    "library can be pinned explicitly": '"--library"' in src and "def current_library(pin" in src,
    "collision names skip ones already taken": "already claimed by a real file" in src,
    "case correction does not fake a collision": "samefile(src)" in src,
    "paths split on both separators": 're.split(r"[\\\\/]"' in src,
    "a fresh scan invalidates the old plan": "A fresh scan invalidates any plan" in src,
    "the log survives power loss": "os.fsync(fh.fileno())" in src,
    "undo restores original folder casing": "Every component, outermost first" in src,
    "digest covers source folder and original name": 'm["from"], m["name"], m["to"]' in src,
    "approval digest covers renames too": 'm.get("final_name", m["name"])] ' in src
                                          or 'final_name", m["name"])\n' in src,
}

# The install prompt quotes the number of checks. If that number goes stale, the very
# first thing the owner runs looks broken. Assert the docs match what actually prints.
import re as _re
_docs = [("SETUP-PROMPT.md", setup_prompt), ("README.md", readme)]
_quoted = [(lbl, int(n)) for lbl, d in _docs
           for n in _re.findall(r"ok: (\d+) media-library-setup contract checks", d)]
TOTAL = len(checks) + len(_quoted)
for lbl, n in _quoted:
    checks[f"{lbl} quotes the real check count"] = (n == TOTAL)

failed = [name for name, ok in checks.items() if not ok]
if failed:
    raise SystemExit("failed: " + ", ".join(failed) +
                     (("  | gate: " + "; ".join(gate_errors)) if gate_errors else ""))
print(f"ok: {len(checks)} media-library-setup contract checks")
PY

test -s "$skill_dir/references/structure-rules.md"
