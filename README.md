# Village Nights

Three Pygame mini-games in one, loosely inspired by communal West African traditions of drumming, strategy play, and weaving — unified by a single GenAI-narrated Storyteller who comments live on how you're playing.

## Quick start (VS Code — recommended)

1. Unzip the submission folder and open it in VS Code (File > Open Folder).
2. Open a terminal (Terminal > New Terminal) and run:

```bash
python3 -m venv .venv
source .venv/bin/activate       # Windows (PowerShell): .venv\Scripts\Activate.ps1
pip install -r requirements.txt
python3 main.py
```

A window should open on the title screen. Press `1`, `2`, or `3` to pick a level. If nothing happens after `pip install`, jump to **Troubleshooting** below before digging further.

## Alternative: running in JuiceMind (no local install)

If a local Python setup isn't available, [JuiceMind](https://juicemind.com) has a browser-based Pygame IDE that needs nothing installed:

1. Open JuiceMind's [Pygame IDE](https://play.juicemind.com/dashboard/explore/teamsInfo/code?language=pygame) and sign in / create a project.
2. Paste the contents of `main.py` into the editor (or upload it, if your project view supports that).
3. Also add `african_music.mpeg` to the same project (look for an "upload" or "add asset" option) — `main.py` looks for it in the same folder it's running from, so without it there, music won't play there even though it does locally.
4. Click Run.

Three things specific to that environment:

- **Music** needs `african_music.mpeg` uploaded alongside the code (step 3). I couldn't confirm from JuiceMind's public pages whether their Pygame sandbox actually supports adding a second file next to your script — if it doesn't, the game still runs fine, just without background music (the load is wrapped in try/except, so a missing file never crashes anything).
- **Sound effects** need NumPy. That import is wrapped in try/except too, so if NumPy isn't available there, the synthesized SFX just go silent instead of crashing.
- **The optional AI narrator** needs an `OPENAI_API_KEY` environment variable, which a browser sandbox typically won't let you set. That's fine — the Storyteller automatically falls back to its pre-written lines.

## What this is

| Level      | Game                      | Type                                                                                 |
| ---------- | ------------------------- | ------------------------------------------------------------------------------------ |
| 1 (Easy)   | **Rhythm of the Village** | Drum-and-beat rhythm game — hit SPACE in time with falling notes                     |
| 2 (Medium) | **Oware Trade Routes**    | A simplified single-player _Oware_ (Mancala-family strategy game) against a small AI |
| 3 (Hard)   | **Kente Loom**            | A Simon-Says-style memory game themed around Kente cloth weaving                     |

## Requirements

- **Python 3.9+**
- **pygame** — required, this is the game engine
- **numpy** — required for sound effects (all SFX are synthesized in code, no audio files). Without it the game still runs, just silently.
- **openai** — optional, only needed for the live AI-generated Storyteller lines. Without it, the game uses a built-in set of pre-written fallback lines and is fully playable either way.

All of the above install in one shot via `pip install -r requirements.txt`.

## Controls

**Title / end screen**

- `1` / `2` / `3` — choose a level
- `SPACE` — replay the same level (once one has ended)

**Anywhere mid-game**

- Click the **Menu (Esc)** button, top-right corner — or press `ESC` — to return to the title screen at any point, including mid-level or on the end screen

**Level 1 — Rhythm of the Village**

- `SPACE` — hit a beat, timed to when it reaches the drum

**Level 2 — Oware Trade Routes**

- Click a pit on your (bottom) row to sow its seeds

**Level 3 — Kente Loom**

- `A` / `S` / `D` / `F` / `G` — repeat the flashed pattern (or click the matching pad)

## Files included

```
.
├── main.py               # the whole game - title screen, all three levels, Storyteller, sound synthesis
├── african_music.mpeg    # looping background track (optional - game runs fine, just silently, without it)
├── requirements.txt      # pygame, numpy (openai optional - see below)
├── .gitignore
└── README.md
```

## Optional: live AI narrator

Set an `OPENAI_API_KEY` environment variable before launching (VS Code / local terminal only — see the JuiceMind note above for the browser path):

```bash
export OPENAI_API_KEY=sk-...            # macOS / Linux
$env:OPENAI_API_KEY="sk-..."            # Windows PowerShell
```

Skip this entirely if you're short on hackathon time — nothing breaks without it.

## Troubleshooting

- **`ModuleNotFoundError: No module named 'pygame'`** — your virtual environment isn't activated, or you installed into a different one than the terminal (or VS Code) is currently using. Run `pip list` in your active terminal to check what's actually installed there.
- **Multiple venv folders** (`.venv`, `venv`, `.venv0`, ...) — pick one, delete the rest, then in VS Code: `Ctrl+Shift+P` → "Python: Select Interpreter" → confirm it points at the one you kept.
- **No game window appears / it just hangs** — this needs an actual local display. It will not run over SSH, in a devcontainer, or in most cloud IDEs without a virtual display configured. Run it on your own machine, or use the JuiceMind path above instead.
- **No sound** — confirm `numpy` is installed (`pip show numpy`) and that `african_music.mpeg` is sitting in the same folder as `main.py`. Also worth knowing: `.mpeg` is an unusual extension for pygame's audio loader (it generally expects `.ogg`, `.mp3`, or `.wav`) — if the file is silently failing to load, converting it to `.ogg` or `.mp3` (a one-line `ffmpeg` command) is the most likely fix.

## A couple of honesty notes

- **Oware ruleset**: a casual simplification, not tournament-accurate — notably it skips the "grand slam" restriction some official rule sets use, and seeds can loop back into their own starting pit on a long sow.
- **Kente colors**: decorative rather than tied to specific traditional meanings, since real-world color symbolism in Kente weaving varies by source.
