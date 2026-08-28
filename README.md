# Village Nights

A small anthology of three Pygame mini-games, loosely inspired by communal West African traditions of drumming, strategy play, and weaving. One old village Storyteller — narrated live by a GenAI model — spins a single ongoing tale across whichever game you're playing, growing bolder when you're doing well and stumbling gently (never cruelly) when you slip.

## The three games

Pressing 1, 2, or 3 from the title screen doesn't just change the difficulty — it's a genuinely different game each time.

| Level      | Game                      | Type                                                                                         |
| ---------- | ------------------------- | -------------------------------------------------------------------------------------------- |
| 1 (Easy)   | **Rhythm of the Village** | Drum-and-beat rhythm game — hit SPACE in time with falling notes                             |
| 2 (Medium) | **Oware Trade Routes**    | A simplified single-player _Oware_ (Mancala-family strategy game), played against a small AI |
| 3 (Hard)   | **Kente Loom**            | A Simon-Says-style memory game themed around Kente cloth weaving                             |

## Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
python3 main.py
```

## Requirements

- Python 3.9+
- `pygame`
- `numpy`

`openai` is optional — only needed if you want the Storyteller's lines generated live. Without it, the game automatically falls back to a set of pre-written narrator lines and is fully playable either way.

## Controls

**Title / end screen**

- `1` / `2` / `3` — choose a level
- `SPACE` — replay the same level (once one has ended)
- `ESC` — quit

**Level 1 — Rhythm of the Village**

- `SPACE` — hit a beat, timed to when it reaches the drum

**Level 2 — Oware Trade Routes**

- Click a pit on your (bottom) row to sow its seeds

**Level 3 — Kente Loom**

- `A` / `S` / `D` / `F` / `G` — repeat the flashed pattern (or click the matching pad)

## Enabling the live AI narrator (optional)

Set an `OPENAI_API_KEY` environment variable before launching:

```bash
export OPENAI_API_KEY=sk-...          # macOS / Linux
$env:OPENAI_API_KEY="sk-..."          # Windows PowerShell
```

Without a key set, the Storyteller still comments on every milestone, miss, and ending — just using the built-in fallback lines instead of a live model call.

## How the games work

- **Sound**: every sound effect (drum ticks, hit feedback, capture chimes, the Kente pentatonic pad tones) is synthesized in code with NumPy — no external audio files. If NumPy or an audio device isn't available, the game just runs silently instead of crashing.
- **Storyteller**: at key moments (starting a level, a milestone, a miss/flaw, or finishing) the game asks a GenAI model to continue the tale in one sentence. The call runs on a background thread so none of the three games ever freeze waiting on a network response.

## A couple of honesty notes

- **Oware ruleset**: this is a casual simplification for a mini-game, not a tournament-accurate ruleset. Notably, it doesn't implement the "grand slam" restriction some official rule sets use (which forbids a move that would capture every seed on the opponent's side), and seeds can loop back into their own starting pit on a long sow.
- **Kente colors**: the thread colors are decorative rather than tied to specific traditional meanings — real-world color symbolism in Kente weaving varies by source, so nothing specific is asserted here.

## Project structure

```
.
├── main.py             # the whole game — title screen, all three levels, Storyteller, sound synthesis
├── requirements.txt    # pygame, numpy (openai optional)
├── .gitignore
└── README.md
```
