# media-library-setup Changelog

## 0.4.0 — 2026-07-29

Cross-platform. It was Mac-only in one way that mattered.

- **On Windows the two approval visuals never opened.** The open call was wrapped in a macOS
  platform check, so a Windows member was told "two pages open in your browser" and nothing
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
  English with the fix for each, instead of the member discovering them one failed command
  at a time. Finds Google Drive for Desktop across all its mount locations, and covers
  Python, the openai package, ffmpeg and the API key.
- SKILL.md rewritten as a guided run, step 1 to 8. It now tells the agent to do the installs
  rather than paste commands at the member, and to have the cost conversation up front rather
  than at the moment of spending.
- Costs stated before setup, not at the till: what is free, what is paid, per-hour rate, a
  table, and that $5 covers about 14 hours. Key setup walked through with real links.
- setup.md gained the Python and openai-package step that was assumed but never covered, and
  a fix for each of its failure modes.
- Ends by generating the member's install report, so they finish holding a document that
  says what the thing does and what it cannot do.
- Smoke test 28 -> 34 checks, the new ones covering the preflight, cost-before-spend ordering,
  the do-not-hand-commands-over rule, and the key never being echoed.

## 0.2.1 — 2026-07-29

Fixed seven release blockers found by an independent Codex review — rollback truncation on
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
- **Transcription is built in** — OpenAI `whisper-1`, the same model the reference pipeline uses.
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
