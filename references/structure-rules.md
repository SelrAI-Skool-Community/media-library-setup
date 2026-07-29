# The structure rules

The whole point of this skill. Read before proposing anything.

## The rule: never more than two levels

```
My Media Library/              ← level 0, the root you pick
├── Brisbane Workshop May/     ← level 1, one folder per event, project or shoot
│   ├── Videos/                ← level 2, and that is the floor
│   ├── Photos/
│   ├── Documents/
│   └── _Index/
└── Sydney Shoot June/
    ├── Videos/
    └── ...
```

Level 2 is the floor. Nothing nests deeper. Ever.

## Why flat wins

The obvious-looking move is to sort clips into folders by what they are — interviews here,
b-roll there, stage wide, stage close, hands, screens. It feels tidy. It is not.

A real shoot classifies into 30-50 shot types. Sorting by type turns 60 clips into 40 folders
holding one or two files each. Nobody can flick through that. Finding anything means opening
folder after folder, and you lose the one thing a media library is for: **seeing your footage**.

Nothing is lost by flattening, because the folder was never how anyone actually found things.

Most real libraries are full of `IMG_4821.MOV` and `DJI_0043.mp4` — names that tell you nothing.
Sorting those into shot-type folders does not make them findable, it just hides them one level
deeper. The thing that makes a clip findable is `_Index`: a transcript of what was said and a
line on what it shows. That is what answers "the bit about pricing", and it works no matter
which folder the file sits in.

So the folder only has to do the job a folder is good at — letting a person scroll a wall of
thumbnails and recognise something. One folder of 60 beats 40 folders of one or two.

## The four folders

| Folder | Holds | Finder colour |
|---|---|---|
| **Videos** | Every video for that event, one flat list | purple |
| **Photos** | Every photo and image | blue |
| **Documents** | PDFs, decks, sheets, contracts | orange |
| **_Index** | Every `.transcript.md`, `.summary.md`, `.tags.json`, plus `_MANIFEST.md` | grey |

Drop a folder that would be empty. A shoot with no documents gets no `Documents/`.

`_Index` leads with an underscore so it sorts to the top and reads as machine-owned. It is the
only folder a person never needs to open — it is what makes "find the clip where someone talks
about pricing" work.

## Naming

Event folders: `Event Name Month` or `YYYY-MM-DD Event Name`. Pick one and hold it across the
whole library. Mixed conventions are what makes a Drive unsearchable.

**Nothing is renamed.** Files keep the names they already have — the only exception is two
files with the same name arriving from different folders, where the second gets `-2` added
rather than overwriting the first.

If someone wants a naming convention for new work, `{date}_{event}_{type}_{description}_{seq}`
holds up well. Applying it to existing files is a separate job and a bigger conversation.

## When someone asks for deeper folders

They will. The answer is to show them the count: "that would create 38 folders averaging 1.6
files each." Offer the alternative — the same split as a saved search or a section in
`_MANIFEST.md`, which costs no folders and no clicking.

If they still want it after seeing the number, build what they asked for. It is their library.
Note the choice in `_Index/_MANIFEST.md` so the next run does not silently undo it.
