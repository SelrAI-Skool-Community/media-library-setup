# media-library-setup Changelog

## 0.8.0 — 2026-07-29

Independent review of the rollback and per-library code, none of which existed when
the last review ran. 12 findings, every one traced and reproduced before fixing.

Two were serious:

- **A partial undo destroyed its own retry path.** If one file could not be found — because
  the owner had moved or renamed it — the whole log was archived anyway. The files that did
  not come back could never be retried, and `status` reported "nothing pending". The rows that
  fail now stay live, `status` says the undo is only partly done, and running it again picks up
  exactly those files.
- **An approval could land on the wrong library.** Scanning a second library silently made it
  the current one, so an approval given for library A would move library B. `apply` and
  `rollback` now print the full path of the library they are about to change, and take
  `--library` to pin it explicitly.

The rest, all confirmed by tracing:

- A generated `-2` name could collide with a real file already called that, so apply quietly
  used `-2-2` and executed something the owner never approved. Collision names now skip any
  name already claimed.
- Correcting a folder's case (`videos` to `Videos`) made a file look like a collision with
  itself and renamed it `-2`. Guarded with a same-file check.
- Undo restored files correctly but left the folder casing apply had changed, so a library was
  not truly back as it was. Every path component is now restored.
- A fresh scan left an already-approved plan valid, so apply could run against files that had
  changed underneath it. Scanning now clears the old plan and visuals.
- The approval fingerprint ignored the source folder and original filename, so editing either
  would pass. Both are covered now.
- Windows paths were split on forward slashes only, putting event folders one level too deep.
- The move log is fsynced, so a power cut cannot leave a moved file with no way back.

63 -> 74 contract checks.

## 0.7.0 — 2026-07-29

Third hardening round, attacking the new undo. It held: a library comes back
byte-for-byte identical, including one with five files sharing a name across five
folders.

- **The undo preview exited as an error.** Same bug class as the cost preview,
  missed on rollback. Exits 0 now.
- **`status` still said "waiting for approval" after an undo**, which reads as though
  the organise never happened. Now says it was put back, with the date.
- **Damaged videos were silently priced.** A file that could not be read measured as
  zero minutes and disappeared into the quote. They are now named, skipped, and the quote
  says $0.00 rather than a rounded-up cent.
- **Renames happened after approval**, which undermines the core guarantee.
  Two files with the same name landing in one folder got a `-2` suffix decided inside
  apply — after the owner had approved. So "you see the exact plan first" was not true for
  renames. They are now worked out at plan time, printed in the plan, shown as their own
  tile in the visual, and covered by the approval fingerprint. `apply` uses the name the
  plan showed rather than inventing one.

56 -> 62 contract checks.

## 0.6.0 — 2026-07-29

Second hardening round, attacking the round-1 fixes. The two-library fix held.
Six new issues:

- **There was no way to undo.** The headline promise is "it can all be put back", and no
  `rollback` command existed — there was only a CSV the owner was expected to reverse
  by hand. `rollback` now exists: previews what it would restore, changes nothing without
  a named approval, puts every file back under its ORIGINAL name, and clears the folders it
  empties. `rollback.csv` gained an `original_name` column, without which a collision-renamed
  file could never be restored correctly. Verified: a library with a duplicate filename came back
  byte-identical to how it started.
- **The cost preview exited as an error.** `transcribe` without `--yes` succeeded but
  returned exit 1, indistinguishable from a real failure like missing ffmpeg. Exits 0 now.
- **"Nothing is ever deleted" conflicted with empty folders being cleared.** Reworded
  everywhere to "no file is ever deleted", and the folder cleanup is now stated up front.
- **The visual promised to remove folders it would not touch.** It showed the raw count of
  near-empty folders rather than the folders the plan actually empties. Now computed exactly, and
  checked against what apply really clears.
- **Framed as Google-Drive-only.** It works on any folder — an external drive, a local
  Projects folder. Drive for Desktop is only how a Drive gets onto the machine.
- Added `status`: which library is active, its state, and whether an undo is available.

48 -> 56 contract checks.

## 0.5.0 — 2026-07-29

First hardening round, run against a spread of awkward libraries with no help
available — the position a non-technical owner is actually in.

- **One shared state folder for every library.** All state lived in a single
  `~/active/media-library-setup`, so scanning a second library silently overwrote the first
  library's plan and mixed both libraries into one rollback log. Anyone with two client shoots
  would have lost their undo history. Each library now gets its own state folder keyed to its
  path, and `MEDIA_LIBRARY_WORK_DIR` overrides the base so it can be tested anywhere.
- **An empty or already-tidy library walked the owner through approving nothing.** scan
  now stops with "this folder has nothing to organise", and apply refuses a no-op outright
  rather than asking for a signature on zero moves.
- **The docs contradicted each other on renaming.** structure-rules.md said files get
  renamed; SKILL.md said they never are. The code never renamed. Docs now agree with the code.
- **The layout message was nonsense on edge cases** — a folder with no subfolders was
  told "its subfolders are already categories". Now says what it actually means.
- **The setup gate contradicted the pricing.** It said not to proceed until everything was
  installed, while also saying organising is free. Only Drive for Desktop is required now, and
  `check` says which items are optional.
- **Transcribe blamed the owner for a step they had just done** — "Run scan and apply
  first" on a photos-only library. Now says there are no videos and nothing to pay for.

40 -> 48 contract checks, one per issue above, so none of them can come back.

## 0.4.0 — 2026-07-29

Cross-platform. It was Mac-only in one way that mattered.

- **On Windows the two approval visuals never opened.** The open call was wrapped in a macOS
  platform check, so a Windows owner was told "two pages open in your browser" and nothing
  happened — silently removing the approval step the whole design rests on. Now opens on Mac,
  Windows and Linux, and if it cannot, it prints the paths and says they must be looked at.
- `check` detects the computer and prints that computer's install line: brew, winget or apt.
  It says which platform it detected, so a wrong guess is visible rather than confusing.
- API key instructions for Windows (`setx`, plus the reminder to open a new terminal).
- setup.md carries Mac, Windows and Linux paths for the Drive folder, ffmpeg and the key, and
  is honest that Google ships no Drive for Desktop on Linux.
- Folder colours are Mac-only. Rather than failing quietly, it now says so once and explains
  the folders are organised identically without them.
- Smoke test 34 -> 38 checks, including one that fails if the visuals can ever be skipped
  silently again.

Each platform branch verified by forcing the platform flags and asserting which opener runs:
Mac `open`, Windows `os.startfile`, Linux `xdg-open`.

## 0.3.0 — 2026-07-29

Plug-and-play pass. Aimed at a business owner who has never opened a terminal.

- New `check` command as step one. Reports every missing prerequisite at once in plain
  English with the fix for each, instead of them being discovered one failed command
  at a time. Finds Google Drive for Desktop across all its mount locations, and covers
  Python, the openai package, ffmpeg and the API key.
- SKILL.md rewritten as a guided run, step 1 to 8. It now tells Claude to do the installs
  rather than paste commands at the owner, and to have the cost conversation up front rather
  than at the moment of spending.
- Costs stated before setup, not at the till: what is free, what is paid, per-hour rate, a
  table, and that $5 covers about 14 hours. Key setup walked through with real links.
- setup.md gained the Python and openai-package step that was assumed but never covered, and
  a fix for each of its failure modes.
- Ends by generating the owner's install report, so they finish holding a document that
  says what the thing does and what it cannot do.
- Smoke test 28 -> 34 checks, the new ones covering the preflight, cost-before-spend ordering,
  the do-not-hand-commands-over rule, and the key never being echoed.

## 0.2.1 — 2026-07-29

Fixed seven release blockers found by an independent code review — rollback truncation on
retry, a half-moved library on any single failure, over-broad junk and empty-folder deletion,
a symlink that could overwrite its own destination, an approval gate that accepted whitespace
and was never bound to the plan shown, a transcript name collision that billed twice, and
re-billing after a local write failure. Plus HTML escaping, the 25MB audio cap, transcribe
running without approval, and three claims in the docs the code did not keep.

## 0.2.0 — 2026-07-28

Switched from the Google Drive API to a local folder.

- Works on a **Google Drive for Desktop** folder instead of the Drive API. Removes the Google
  Cloud project, OAuth consent screen and `gcloud` install that a non-technical person was never
  getting through. Reorganising locally syncs back to Drive on its own.
- **Transcription is built in** — OpenAI `whisper-1`.
  `transcribe` measures every video and prints the exact cost, and sends nothing until `--yes`.
  Already-transcribed videos are skipped, so an interrupted run costs nothing to resume.
- Folder colours are now **macOS Finder tags** (Videos purple, Photos blue, Documents orange,
  `_Index` grey), since Drive's own folder colours do not apply to a synced folder.
- `apply` clears away the folders it empties, and forces canonical casing — on a
  case-insensitive filesystem `mkdir("Videos")` silently reuses an existing `videos`.
- Same-named files arriving from different folders are suffixed, never overwritten.
- OS junk (`.DS_Store`, `._*`, `desktop.ini`) is ignored in counts and moves.
- New `references/setup.md`: the three installs with real links, a check after each, the cost
  table, and a fix for every way each step fails.

Verified end to end on a folder rebuilt to match the original mess — 28 folders three levels
deep with one file each, collapsed to 8 folders two levels deep, plus a real transcription
round-trip against the OpenAI API.

## 0.1.0 — 2026-07-28

First release. Four-step flow with the approval gate, two visuals, Drive API via `gws`.
