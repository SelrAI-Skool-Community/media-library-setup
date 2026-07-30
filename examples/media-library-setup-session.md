# media-library-setup — worked session

A real run, condensed. Shows the approval gate doing its job.

---

**Them:** My Drive is a disaster. I can never find the video I want.

**Claude:** Your Drive is already on this machine via Drive for Desktop, so I can
work on it as a normal folder. Scanning — read only, nothing will change.

```
Scanned 'Footage' — read only, nothing changed.
  3412 files (742GB) in 109 folders, 2 levels deep
  48 folders hold 2 files or fewer
  Videos       1596
  Photos       1539
  Documents     277
```

48 of your 109 folders hold two files or fewer. That is the thing making this hard to use —
not the number of files.

Working out a structure. Still not changing anything.

```
Treating this as a library of events — its subfolders look like separate events.
  109 folders (2 deep)  ->  82 folders (2 deep)
  3412 files will move, 0 already correct
  Nothing is deleted. Every move is logged and reversible.
```

Two pictures opened in your browser:

1. **Folder structure** — your folders now versus proposed. Red rows are the near-empty ones.
2. **Where everything is stored** — what lands where, and what it buys you.

The short version: one folder per event, and inside each, four folders — Videos, Photos,
Documents, and `_Index` for the searchable text. Nothing goes deeper than that.

3,412 files move. 27 near-empty folders disappear. **Nothing is deleted** — every move is
written to a rollback file as it happens, so this is fully reversible.

Have a look at both, and tell me to go ahead when you are happy.

---

**Them:** Why not sort the videos by type? Interviews, b-roll, that sort of thing.

**Claude:** Tried that, and it is the trap. Your footage classifies into 37 shot types — sorting
by type would turn 1,596 videos into roughly 37 folders per event, most holding one or two
clips. That is what you already have, and it is why you cannot find anything.

The type is not lost. It is in the filename:

```
2026-05-07_brisbane_testimonial-short_sarah-results_001.mp4
```

So searching still finds it, and you get to scroll one folder of thumbnails instead of opening
forty. If you still want the split after seeing that, say so and I will build it.

---

**Them:** No, makes sense. Go ahead.

**Claude:**

```
About to change:  ~/Library/CloudStorage/GoogleDrive-…/My Drive/Footage
Applying: 3412 files to move. Nothing will be deleted.
  Brisbane 1 — 2026-05-07/Videos
  Brisbane 1 — 2026-05-07/Photos
  ...
Done. 3412 files moved, 0 deleted.
  27 emptied folders cleared away.
Rollback log: ~/active/media-library-setup/footage-4c1d8ba9/rollback.csv
```

Done. On a Mac the folders are colour-tagged in Finder — Videos purple, Photos blue,
Documents orange, `_Index` grey. On Windows they are organised identically, without colours. Drive for Desktop is syncing the new layout back up now.

Next: transcribing, so you can ask for a moment instead of a filename. I measure it first:

```
  1596 videos, 4210 minutes of audio
  Estimated cost: $25.26 USD (OpenAI whisper-1, $0.006/min)
  This is billed to your own OpenAI account.

Nothing has been sent and nothing has been charged.
To go ahead:  library.py transcribe --yes
```

Your call. Once that is done, this works:

> find the bit where someone talks about pricing

---

## What to notice

- Three read-only steps before anything moved.
- The visuals came before the ask, not after.
- The pushback on shot-type folders was answered with the actual count, then handed back to them.
- Nothing was deleted, and the rollback path was named up front.
- The transcription cost was quoted in dollars before a single request went out.
