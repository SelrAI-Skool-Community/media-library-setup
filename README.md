# Media Library Setup

**Turns a messy Google Drive of photos and videos into something you can actually browse — and
search by what was said in the clip, not just the filename.**

Made by Selr AI.

---

## Who this is for

Anyone whose Drive fills up faster than it gets filed. Event footage, client shoots, workshops,
social content. If finding an old clip currently means twenty minutes of clicking through
folders, this is for you.

You do not need to be technical. You never type a command — Claude does all of it. You install
one app, sign into your own Google account, and paste one key if you want the search feature.

---

## What it actually does

**1. It looks, and changes nothing.** Counts what you have, how deep your folders go, and how
many folders are holding one or two files.

**2. It shows you two pictures.** Your folders now, versus what it proposes. Near-empty folders
marked in red. Where every kind of file would end up.

**3. It waits.** Nothing moves until you say yes. If you want it different, it redraws for free.

**4. Then it tidies.** Everything lands in a simple shape, two levels deep, never more:

```
Your Library/
├── Brisbane Workshop May/
│   ├── Videos/       every video, one scrollable list
│   ├── Photos/       every photo together
│   ├── Documents/    decks, PDFs, contracts
│   └── _Index/       transcripts, so you can search what was said
└── Sydney Shoot June/
```

**5. Optionally, it makes it searchable.** Transcribes your videos so you can ask:

> find the bit where someone talks about pricing

---

## The two promises

- **Nothing changes until you approve it.** You see the exact plan first, as pictures.
- **Nothing is ever deleted.** Files move, every move is written to an undo file, and the whole
  thing can be put back.

---

## What it costs

**Organising your folders is free.** No account, no key, no cost.

**Transcribing costs money** — it uses OpenAI to turn speech into text, billed to your own
OpenAI account at about **$0.36 per hour of video**. $5 of credit covers roughly 14 hours.

You are shown the exact figure for your library before anything is sent, and nothing is charged
until you confirm. Each video is only ever paid for once.

---

## Install

Drop the `media-library-setup` folder into `~/.claude/skills/`, then paste this into Claude Code:

```
Install the media-library-setup skill for me.

1. Confirm SKILL.md exists at ~/.claude/skills/media-library-setup/SKILL.md
2. Run: bash ~/.claude/skills/media-library-setup/scripts/smoke.sh
   It should print "ok: 38 media-library-setup contract checks".
3. Run: python3 ~/.claude/skills/media-library-setup/scripts/library.py check
   Then walk me through installing anything it says is missing.

Do not scan or move anything yet.
```

Works on **Mac and Windows**. Linux works too, though Google does not make Drive for Desktop
for it.

## Then

```
Organise my Google Drive media folder.
```

---

## What is in here

| File | What it is |
|---|---|
| `SKILL.md` | The step-by-step Claude follows, from install to finished library |
| `references/setup.md` | Every install, with links and a fix for each way it fails |
| `references/structure-rules.md` | Why the folders stay flat, and the rule that stops them nesting |
| `scripts/library.py` | Does the work: checking, counting, planning, the pictures, moving, transcribing |
| `scripts/smoke.sh` | A self-test that proves the safety gates still work. Runs offline |
| `SELR-REPORT.html` | A full security and plain-English report on this skill. Open it in a browser |
| `examples/` | A worked example of a real run |
