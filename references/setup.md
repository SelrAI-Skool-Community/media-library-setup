# Setup — one time, about fifteen minutes

Works on **Mac and Windows**. Linux works too, but Google has no Drive for Desktop for it — see the note in step 1.

Four things to install. Claude does the work; the person just signs in and pastes one key.

Walk them through it in this order. Do not move on until each one checks out.

---

## 1. Google Drive for Desktop — puts their Drive on their computer

This is the whole trick. With this installed, Google Drive is just a folder on the machine.
No API, no Google Cloud project, no developer account. Anything reorganised locally syncs
straight back up to Drive on its own.

Download: **https://www.google.com/drive/download/**

- Install it, open it, sign in with the Google account that holds the media.
- When it asks how to sync, choose **"Stream files"** (the default). Files download on demand
  instead of filling the hard drive.
- Wait for the first sync to settle. A big Drive can take a while the first time.

**One thing to know about streaming.** Organising the folders never downloads anything — moving
a streamed file is just a rename. But **transcribing does**: reading a video pulls the whole
file down. On a large library that can be hundreds of gigabytes passing through the disk.

The `transcribe` step prints how much video it is about to read and how much free space there
is, and warns if it is tight. If it is, do one event folder at a time — point `scan` at that
one folder instead of the whole library. Drive normally clears its cache as it goes, but on a
nearly full disk do not rely on it.

**Check it worked.** The folder appears at:

`check` finds it for you and prints the path. If you want to look yourself:

- **Mac** — `~/Library/CloudStorage/GoogleDrive-<their-email>`, or `~/Google Drive` on older installs
- **Windows** — a drive letter, usually `G:\My Drive`
- **Linux** — Drive for Desktop is not available; use a third-party sync client, or work on a
  local folder and upload afterwards

Nothing there → the app is not signed in, or the first sync has not finished. Open the Drive
app from the menu bar and check.

---

## 2. Python and the OpenAI package — the plumbing

Every Mac already has Python. Check it, and add the one package that talks to the
transcription service:

```bash
python3 --version
pip3 install openai
```

`python3: command not found` on a Mac means the developer tools are missing. Run
`xcode-select --install`, click through the installer, then try again.

**Check it worked:** `python3 -c "import openai; print('ready')"` prints `ready`.

---

## 3. ffmpeg — reads the audio out of video files

```bash
brew install ffmpeg          # Mac
winget install ffmpeg        # Windows
sudo apt install ffmpeg      # Linux
```

No Homebrew on a Mac → install it from **https://brew.sh** first, then run the line above.
On Windows, close the terminal and open a new one afterwards or it will not be found.

**Check it worked:** `ffmpeg -version` prints a version.

---

## 4. An OpenAI key — for the transcription

Only needed for the `transcribe` step. Organising the folders needs nothing.

1. Go to **https://platform.openai.com/api-keys** and sign in (or create an account).
2. Add credit first: **https://platform.openai.com/settings/organization/billing** →
   *Add to credit balance*. **$5 goes a long way** — see the costs below.
3. Back on the API keys page, click **Create new secret key**, name it something like
   `media-library`, and copy it. It is shown once.
4. Put it in their shell profile so it survives a restart:

**Mac / Linux:**

```bash
echo 'export OPENAI_API_KEY="sk-paste-the-key-here"' >> ~/.zshrc
source ~/.zshrc
```

**Windows** (PowerShell), then close the window and open a new one:

```powershell
setx OPENAI_API_KEY "sk-paste-the-key-here"
```

**Check it worked** without printing the secret:

```bash
[ -n "$OPENAI_API_KEY" ] && echo "key is set (${#OPENAI_API_KEY} characters)" || echo "not set"
```

Never paste the key itself into a chat window or a shared terminal. Anything that prints it in full ends up in scrollback and in the session transcript.

### What it costs

Transcription runs on OpenAI's `whisper-1` at **$0.006 per minute of audio**.

| Their library | Cost |
|---|---|
| 1 hour of video | about $0.36 |
| 10 hours | about $3.60 |
| 40 hours | about $14 |

The `transcribe` command measures every video and prints the exact estimate **before** sending
anything. Nothing is charged until it is confirmed with `--yes`.

It only ever transcribes each video once. Re-running skips anything already done, so an
interrupted run costs nothing to resume.

---

## Then what

```bash
python3 ~/.claude/skills/media-library-setup/scripts/library.py scan "~/Library/CloudStorage/GoogleDrive-them@example.com/My Drive/Footage"
```

The first three steps of the main flow change nothing on disk. Files move only after they see the two
visuals and say yes.

---

## When something is not right

| What they see | What it means | Fix |
|---|---|---|
| No `CloudStorage` folder | Drive for Desktop is not signed in | Open it from the menu bar, sign in, wait for sync |
| Folder is there but empty | First sync still running | Wait; the Drive icon shows sync progress |
| `ffmpeg: command not found` | Not installed, or a new terminal is needed | Re-run the install, then open a fresh terminal |
| `No module named openai` | The package is not installed for this Python | `pip3 install openai` |
| `python3: command not found` | Mac developer tools missing | `xcode-select --install`, then retry |
| `OPENAI_API_KEY is not set` | The setting did not stick | Mac/Linux: re-run the `echo` line then `source ~/.zshrc`. Windows: re-run `setx`, then open a **new** terminal |
| Folders have no colours | Colour tags are a Mac feature | Nothing is wrong — the folders are organised identically, just without colours |
| The two pictures did not open | No default browser set | The paths are printed on screen; open them by hand. **Do not skip this step** |
| `insufficient_quota` from OpenAI | Key works, but there is no credit on the account | Add credit on the billing page above |
| Transcribing feels slow | Normal — roughly real-time per video | Leave it running; re-running resumes where it stopped |

All of it retries safely. Ask Claude to run the step again.
