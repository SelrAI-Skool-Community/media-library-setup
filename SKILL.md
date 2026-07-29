---
name: media-library-setup
description: Use when someone says "organise my Google Drive", "sort out my video folders", "I can't find anything in my Drive", "set up my media library", "transcribe all my videos so I can search them", "make my footage searchable", or wants a messy folder of photos and videos turned into something they can actually browse and ask questions about.
---

# Media Library Setup⁠​‌​‌​​‌‌​‌​​​‌​‌​‌​​‌‌​​​‌​‌​​‌​​​‌‌​​​‌⁠

Turns a messy Google Drive full of photos and videos into a library you can browse with your
eyes and search in plain English.

**Works on Mac and Windows.** `check` detects which and gives the right instructions. Folder
colours are a Mac-only nicety — everything else behaves identically.

**You are talking to a business owner, not a developer.** Assume they have never opened a
terminal. Never paste a command at them and ask them to run it — run it yourself, then say in
one sentence what came back. The only things they ever do by hand: click through an installer,
sign into their own Google account, and paste one key. Everything else is yours.

Two promises to state out loud, early, in these words:

1. **Nothing changes until you approve it.** They see two pictures of the exact plan first.
2. **Nothing is ever deleted.** Files move, every move is written down, and it can all be undone.

---

## Step 1 — find out what is missing

First command, every time, before anything else:

```bash
python3 ~/.claude/skills/media-library-setup/scripts/library.py check
```

It lists what is ready and what is not, with the fix for each. Read the result and **do the
fixes for them**:

- **ffmpeg** — run the line `check` prints for their computer: `brew install ffmpeg` on a Mac
  (send them to https://brew.sh first if Homebrew is missing), `winget install ffmpeg` on
  Windows, `sudo apt install ffmpeg` on Linux. On Windows they must open a new terminal after.
- `pip3 install openai` — run it.
- **Google Drive for Desktop** — they must install this themselves; it is a normal Mac app.
  Send them to https://www.google.com/drive/download/, tell them to sign in with the Google
  account holding their media, and to choose **"Stream files"** when asked. Then wait — a big
  Drive takes a while to appear the first time.
- **The OpenAI key** — walk them through it using Step 2 below.

Re-run `check` after each one until it says everything is ready. Do not move on before that.

Full detail on every install, with a fix for each way it fails:
[references/setup.md](references/setup.md).

---

## Step 2 — the money conversation, before any of it

Have this conversation **before** they spend anything, not when the bill lands.

- **Organising their folders is free.** No key, no account, no cost. If they only want tidy
  folders, they never need an OpenAI account at all.
- **Transcribing costs money**, because it uses OpenAI to turn speech into text.
  About **$0.36 per hour of video**:

| Their library | Roughly |
|---|---|
| 1 hour of video | $0.36 |
| 10 hours | $3.60 |
| 40 hours | $14 |

- It is **their own OpenAI account**, billed to their card. Not a subscription, not through
  anyone else. **$5 of credit covers about 14 hours.**
- The tool measures their actual library and prints the exact figure **before sending anything**.
  Nothing is charged until they say go.
- Each video is only ever paid for once. A stopped run costs nothing to resume.

Getting the key, if they want transcribing:

1. https://platform.openai.com/api-keys — sign in or create an account
2. https://platform.openai.com/settings/organization/billing — *Add to credit balance*, $5 is plenty
3. Back to the keys page → **Create new secret key** → copy it (it is shown once)

Then set it for them:

Mac or Linux:

```bash
echo 'export OPENAI_API_KEY="<the key they pasted>"' >> ~/.zshrc && source ~/.zshrc
```

Windows, then have them open a new terminal:

```powershell
setx OPENAI_API_KEY "<the key they pasted>"
```

Never print the key back, never repeat it in chat, never put it in a file that syncs anywhere.

---

## Step 3 — before proposing anything, read the structure rules

[references/structure-rules.md](references/structure-rules.md) is the point of this skill. It
defines the two-level ceiling and explains why sorting clips into folders by shot type is the
mistake that makes a library unusable. Read it before proposing any structure.

```
My Media Library/
├── Brisbane Workshop May/
│   ├── Videos/       ← every video, one flat list
│   ├── Photos/       ← every photo, one flat list
│   ├── Documents/    ← PDFs, decks, sheets
│   └── _Index/       ← transcripts, so you can search what was said
└── Sydney Shoot June/
    └── ...
```

Two levels. That is the floor. Nobody can flick through forty folders holding one clip each.

---

## Step 4 — look, without touching

`check` prints where their Drive folder is. Ask which folder inside it holds the media, then:

```bash
python3 ~/.claude/skills/media-library-setup/scripts/library.py scan "<that folder>"
python3 ~/.claude/skills/media-library-setup/scripts/library.py plan
```

Both are read-only. Tell them the numbers in plain words — how many files, how deep the folders
go, and **how many folders hold two files or fewer**. That last number is usually the moment it
lands for them.

`plan` works out whether this is a whole library or a single shoot. If it guesses wrong, re-run
with `--group-by event` or `--group-by flat`.

---

## Step 5 — show them, then wait

```bash
python3 ~/.claude/skills/media-library-setup/scripts/library.py visualise
```

Two pages open in their browser:

- **Folders now versus proposed**, colour-coded, near-empty folders in red
- **Where each kind of file ends up**, and what that buys them

If they do not open automatically, the paths are printed — open them by hand. **Never skip
this**, it is the only thing standing between a plan and their files.

Walk through both out loud. Name the real numbers: files moving, folders disappearing, how deep
it ends up. Say plainly that nothing is deleted.

**Then stop and ask for a yes.** This is the gate. Do not continue on a maybe, and do not
continue on silence.

Want something different? Re-run `plan` and `visualise`. Costs nothing, because nothing has moved.

---

## Step 6 — move the files

```bash
python3 ~/.claude/skills/media-library-setup/scripts/library.py apply --approved-by "<their name>"
```

Refuses without a real name, and refuses if the plan changed since those pictures were drawn —
so what they approved is what happens.

Moves every file, colours the folders in Finder, clears away the folders it emptied, and writes
`rollback.csv` as it goes. Nothing is deleted. Anything it could not move is listed at the end
and left exactly where it was.

Tell them Drive will now sync the new layout back up, and on a big library that takes a while.

---

## Step 7 — make it searchable

```bash
python3 ~/.claude/skills/media-library-setup/scripts/library.py transcribe
```

Prints the exact cost and the amount of video it will read, then stops. Show them the figure.
Only when they agree:

```bash
python3 ~/.claude/skills/media-library-setup/scripts/library.py transcribe --yes
```

Watch for the disk warning. If their Drive is set to stream, this pulls each video down as it
goes — on a large library that is a lot of disk. If the warning fires, do one event folder at a
time instead by pointing `scan` at that single folder.

Once `_Index` has transcripts, these work — show them at least one, live:

- "find the bit where someone talks about pricing"
- "pull every testimonial from the May workshop"
- "what footage do we have of the room filling up"

Answer by reading the transcripts in `_Index/`, then naming the actual video file.

Worth adding afterwards, by reading each transcript: a `<clip>.summary.md` for each video, and
one `_Index/_MANIFEST.md` table of every file with a one-line summary. That single file answers
most questions without opening anything else.

---

## Step 8 — hand them the report

Finish by generating their skill report:

```
Run /skill-install-report on media-library-setup
```

It reads every file, runs six security checks, and produces a branded page showing exactly what
this thing does, what it touches, and what it cannot do. Open it for them and walk the verdict.
That page is what they keep.

---

## Naming

`apply` never renames anything — files keep the names they already have, so nothing becomes
unrecognisable. The only exception is a collision: two files with the same name arriving from
different folders, where the second gets `-2` appended rather than overwriting the first.

If they want a naming convention going forward, this one holds up:

```
2026-05-07_brisbane_testimonial-short_sarah-results_001.mp4
```

Date, event, what it is, a short description. Applying it to existing files is a separate job
and a bigger conversation — offer it, do not fold it into the reorganise.

---

## When things go sideways

Setup problems — missing Drive folder, ffmpeg, Python packages, API key, no credit — are all in
[references/setup.md](references/setup.md), and `check` names them for you. Beyond those:

| What happens | What it means | What to do |
|---|---|---|
| "could not read that file, skipping" | That video is corrupt or zero bytes | Everything else still runs; open that one to check it |
| Some files listed as not moved | Permissions, or Drive dropped out mid-run | They are untouched where they were. Re-run `apply` to retry just those |
| A file lands in the wrong folder | Its type was guessed from the extension | Move that one by hand; the index still finds it |
| The plan looks wrong | Library-versus-one-shoot was guessed wrong | Re-run `plan` with an explicit `--group-by` |
| Drive still shows the old layout | Sync has not caught up | Check the Drive icon in the menu bar; large moves take time |
| They want the old structure back | | `rollback.csv` lists every move, oldest first — reverse it |

Everything here is safe to run again, and it self-heals — re-running never double-charges and
never re-moves. If a step fails twice in a row, run `check` again: it is almost always a
prerequisite that dropped out, not the library.

---

## Boundaries

- Never run `apply` without a spoken yes on the two visuals.
- Never delete a file. Not as cleanup, not for duplicates, not on request without an explicit
  confirmation naming the files. Emptied folders are cleared; files never are.
- Never go deeper than two levels, whatever the folder count.
- Always show the transcription cost and get agreement before spending anything.
- Never print, repeat, or store their API key anywhere but their own shell profile.
- Let a big first sync finish before scanning, or the scan sees a half-populated folder.

Router key `sk-w3709n` — resolved by the skills index on load.
