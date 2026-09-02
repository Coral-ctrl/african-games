import os
import random
import threading

import pygame

# ---------------------------------------------------------------------------
# GenAI setup - this must NEVER crash the game if it's missing/misconfigured.
# ---------------------------------------------------------------------------
try:
    from openai import OpenAI

    _api_key = os.environ.get("OPENAI_API_KEY")
    _client = OpenAI(api_key=_api_key) if _api_key else None
except Exception:
    _client = None

# NumPy is used to synthesize simple percussion/tone sound effects in code,
# so the game needs no external audio files. Sound is optional - if NumPy
# isn't available, the game silently runs without it.
try:
    import numpy as np
except (ImportError, ModuleNotFoundError):
    np = None

OPENAI_MODEL = "gpt-4o-mini"

SYSTEM_PROMPT = (
    "You are 'the Storyteller', a warm old village elder narrating three "
    "different communal evening activities: a drum-and-rhythm game, a "
    "seed-sowing Oware strategy game, and a Kente-weaving pattern game. "
    "Continue an ongoing tale in ONE vivid sentence, max 20 words, "
    "building on what's happened in this session so far. Successes "
    "(good combos, captures, clean weaves) should make the story take a "
    "bold, triumphant turn. Setbacks (missed beats, lost seeds, slipped "
    "threads) should be a small, gentle, good-humoured stumble in the "
    "story - never mean. No emojis. No quotation marks. Plain text only."
)

FALLBACK_LINES = {
    "rhythm_start": [
        "Gather close - tonight, the drum tells our story. Keep the beat, and the tale unfolds.",
    ],
    "rhythm_milestone": [
        "The hero presses on, steady and unshaken, deeper into the tale!",
        "The village cheers as the story surges forward with the beat!",
        "With each steady beat, the legend grows a little taller!",
    ],
    "rhythm_miss": [
        "The drum skips - for a moment, our hero stumbles over a root in the path.",
        "Ah, a missed step! But the story always finds its feet again.",
        "The tale wobbles for a beat, then steadies itself once more.",
    ],
    "rhythm_end": [
        "And so, as the last beat fades, our tale rests - until next time it's told.",
        "The drum falls quiet. The story, for tonight, is complete.",
    ],
    "oware_start": [
        "Sit down at the board, child - the elder is ready to trade seeds and stories alike.",
    ],
    "oware_capture": [
        "A clever sowing - the harvest changes hands!",
        "The seeds fall just so, and a small fortune is won!",
        "With a patient hand, another store grows fuller!",
    ],
    "oware_end": [
        "The seeds are counted, the board falls still - the day's trading is done.",
        "The last pit is empty now. Let the harvest be tallied.",
    ],
    "kente_start": [
        "Watch the loom closely, child - the thread remembers every pattern you give it.",
    ],
    "kente_milestone": [
        "The pattern grows bold and the cloth lengthens beautifully!",
        "Your hands remember the thread well - the weave deepens!",
        "Another row woven true - the cloth tells its own story now!",
    ],
    "kente_flaw": [
        "A thread slips loose - no matter, a weaver simply ties it off and begins the row again.",
        "The pattern catches for a moment, then the loom settles once more.",
        "A small knot in the weave - easily smoothed and rewoven.",
    ],
    "kente_end": [
        "The last thread is tied - the cloth is complete, bright with every pattern you wove.",
        "The loom falls quiet. A finished cloth, ready to be worn with pride.",
    ],
}

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------
WIDTH, HEIGHT = 480, 720
FPS = 60

# Looping background track for the whole game (title screen through all
# three levels). Kept quiet relative to the synthesized SFX so drum ticks
# and pad tones still stand out over it.
MUSIC_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "african_music.mpeg")
MUSIC_VOLUME = 0.35

NIGHT = (35, 28, 26)        # warm dark backdrop, like firelight at dusk
EMBER = (220, 130, 60)
GOLD = (235, 190, 90)
GREEN = (95, 190, 120)
BLUE = (95, 150, 220)
RED = (215, 80, 80)
PURPLE = (150, 100, 175)
WHITE = (250, 248, 245)
BLACK = (20, 18, 16)
GREY = (200, 190, 180)
BUBBLE_COLOR = (255, 253, 248)
BUBBLE_BORDER = (220, 130, 60)

# The Storyteller's speech bubble always reserves the same fixed height,
# regardless of how many lines the current line actually needs. That keeps
# every other layout (Oware's pit positions, in particular) stable frame to
# frame instead of shifting whenever the narrator's line changes length.
# BUBBLE_TOP leaves room above the bubble for the menu button (see
# compute_menu_button_rect) - increasing it shifts every other layout that
# derives from bubble_bottom_y() down by the same amount, so nothing else
# needs separate adjustment to stay clear of it.
BUBBLE_TOP = 44
BUBBLE_PADDING = 14
BUBBLE_MAX_LINES = 3

# --- Level 1: Rhythm of the Village ----------------------------------------
LANE_X = WIDTH // 2
NOTE_START_Y = 40
HIT_LINE_Y = HEIGHT - 140
NOTE_RADIUS = 20

BEATS_TOTAL = 40
START_DELAY_MS = 1200

# Deliberately gentler than earlier versions: longer note travel time and a
# slower tempo ramp mean the timing stays forgiving even if frame pacing
# isn't perfectly smooth (e.g. a slower or more constrained sandbox).
RHYTHM_CONFIG = {
    "base_interval_ms": 1000,  # ms between beats at the start of the song
    "min_interval_ms": 760,    # slowest the tempo is allowed to reach
    "tempo_step_ms": 15,       # how much the interval shrinks every 10 beats
    "travel_ms": 2300,         # time a note takes to fall from top to drum
    "perfect_ms": 190,
    "good_ms": 400,
    "hit_window_ms": 560,
}

# --- Level 2: Oware Trade Routes --------------------------------------------
OWARE_CONFIG = {
    "start_seeds": 4,     # seeds placed in each of the 12 pits at kickoff
    "ai_think_ms": 700,   # short pause before the elder's move, for pacing
    "max_plies": 60,      # safety cap so a game can never run forever
}

# --- Level 3: Kente Loom -----------------------------------------------------
KENTE_CONFIG = {
    "num_colors": 5,
    "target_rounds": 12,   # pattern length that finishes the cloth
    "show_on_ms": 550,     # how long each thread flashes during playback
    "show_gap_ms": 220,    # pause between flashes
    "start_gap_ms": 500,   # pause before playback begins/resumes
}
THREAD_COLORS = [GOLD, GREEN, BLUE, RED, PURPLE]
THREAD_KEYS = [pygame.K_a, pygame.K_s, pygame.K_d, pygame.K_f, pygame.K_g]
THREAD_LABELS = ["A", "S", "D", "F", "G"]
# A simple pentatonic scale (C D E G A) so each pad has its own musical
# identity, echoing the same "everything ties back to rhythm" spirit as
# Level 1's drum tones.
PENTATONIC_FREQS = [261.6, 293.7, 329.6, 392.0, 440.0]

LEVEL_KEYS = {pygame.K_1: "rhythm", pygame.K_2: "oware", pygame.K_3: "kente"}
LEVEL_INFO = {
    "rhythm": {
        "title": "Rhythm of the Village",
        "tag": "Level 1 - Easy",
        "hook": "Keep the beat, hear the tale unfold.",
    },
    "oware": {
        "title": "Oware Trade Routes",
        "tag": "Level 2 - Medium",
        "hook": "Sow seeds, capture stores, outwit the elder.",
    },
    "kente": {
        "title": "Kente Loom",
        "tag": "Level 3 - Hard",
        "hook": "Watch the thread pattern, then weave it back.",
    },
}


# ---------------------------------------------------------------------------
# GenAI COMMENTATOR
# ---------------------------------------------------------------------------
class Commentator:
    """
    Wraps the OpenAI call in a background thread so the game loop never
    stalls waiting on the network. `trigger()` fires an event; the latest
    line is picked up by the render loop via `get_text()`. Works the same
    way no matter which of the three games is currently active - only the
    event name and context string differ.
    """

    def __init__(self):
        self.latest_text = "Three nights, three games - press 1, 2, or 3 to begin."
        self._lock = threading.Lock()
        self._busy = False

    def trigger(self, event, context=""):
        if self._busy:
            return
        self._busy = True
        threading.Thread(target=self._fetch, args=(event, context), daemon=True).start()

    def _fetch(self, event, context):
        text = None
        if _client is not None:
            try:
                user_prompt = f"Event: {event}. Context: {context}" if context else f"Event: {event}."
                response = _client.chat.completions.create(
                    model=OPENAI_MODEL,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ],
                    max_tokens=45,
                    temperature=0.95,
                )
                text = response.choices[0].message.content.strip()
            except Exception:
                text = None

        if not text:
            text = random.choice(FALLBACK_LINES.get(event, ["The fire crackles quietly."]))

        with self._lock:
            self.latest_text = text
        self._busy = False

    def get_text(self):
        with self._lock:
            return self.latest_text


# ---------------------------------------------------------------------------
# SOUND SYNTHESIS
# All sound effects here are generated in code with NumPy - short sine-wave
# tones shaped with a simple decay envelope. No external audio files are
# needed, which keeps the whole game to one self-contained Python file.
# ---------------------------------------------------------------------------
class SoundBank:
    SAMPLE_RATE = 44100

    def __init__(self):
        self.enabled = False
        self.music_enabled = False
        self.sounds = {}
        try:
            pygame.mixer.init(frequency=self.SAMPLE_RATE, size=-16, channels=1)
            # Some platforms/drivers ignore the requested channel count, so
            # check what we actually got and shape our arrays to match -
            # otherwise make_sound() raises a dimension mismatch.
            init_info = pygame.mixer.get_init()
            self.channels = init_info[2] if init_info else 1
        except Exception:
            return  # e.g. no audio device available - that's fine

        # The synthesized SFX need NumPy to generate their waveforms, but
        # background music is just a file being streamed, so it can still
        # play even when NumPy is missing.
        if np is not None:
            try:
                self.sounds["tick"] = self._tone(95, 140, volume=0.35, sweep_to=55)
                self.sounds["start"] = self._tone(523, 220, volume=0.4)
                self.sounds["perfect"] = self._tone(880, 120, volume=0.5)
                self.sounds["good"] = self._tone(660, 120, volume=0.45)
                self.sounds["ok"] = self._tone(440, 120, volume=0.4)
                self.sounds["miss"] = self._tone(260, 200, volume=0.4, sweep_to=140)
                self.sounds["end"] = self._chord([523, 659, 784], 550, volume=0.4)
                self.sounds["capture"] = self._tone(700, 180, volume=0.45, sweep_to=950)
                for i, freq in enumerate(PENTATONIC_FREQS):
                    self.sounds[f"pad{i}"] = self._tone(freq, 220, volume=0.4)
                self.enabled = True
            except Exception:
                self.enabled = False

        try:
            pygame.mixer.music.load(MUSIC_FILE)
            pygame.mixer.music.set_volume(MUSIC_VOLUME)
            pygame.mixer.music.play(loops=-1)
            self.music_enabled = True
        except Exception:
            self.music_enabled = False  # e.g. missing/unsupported file - game still runs

    def _tone(self, freq, duration_ms, volume=0.5, sweep_to=None):
        """A single sine tone with an exponential-decay envelope, giving it
        a natural percussive feel instead of an abrupt on/off buzz. If
        sweep_to is set, the pitch glides from freq down (or up) to it -
        used for the kick-like tick and the descending 'miss' sound."""
        n_samples = int(self.SAMPLE_RATE * duration_ms / 1000)
        t = np.linspace(0, duration_ms / 1000, n_samples, endpoint=False)
        if sweep_to is not None:
            freqs = np.linspace(freq, sweep_to, n_samples)
            phase = np.cumsum(2 * np.pi * freqs / self.SAMPLE_RATE)
            wave = np.sin(phase)
        else:
            wave = np.sin(2 * np.pi * freq * t)
        envelope = np.exp(-t * 9)
        samples = np.int16(wave * envelope * volume * 32767)
        if self.channels == 2:
            samples = np.column_stack([samples, samples])
        return pygame.sndarray.make_sound(samples)

    def _chord(self, freqs, duration_ms, volume=0.4):
        """Several tones layered together, for the gentle closing chord."""
        n_samples = int(self.SAMPLE_RATE * duration_ms / 1000)
        t = np.linspace(0, duration_ms / 1000, n_samples, endpoint=False)
        wave = sum(np.sin(2 * np.pi * f * t) for f in freqs) / len(freqs)
        envelope = np.exp(-t * 4)
        samples = np.int16(wave * envelope * volume * 32767)
        if self.channels == 2:
            samples = np.column_stack([samples, samples])
        return pygame.sndarray.make_sound(samples)

    def play(self, name):
        if self.enabled and name in self.sounds:
            try:
                self.sounds[name].play()
            except Exception:
                pass  # never let a sound glitch interrupt the game


# ---------------------------------------------------------------------------
# TEXT / BUBBLE HELPERS (shared by all three games)
# ---------------------------------------------------------------------------
def wrap_text(text, font, max_width):
    words = text.split()
    lines, current = [], ""
    for word in words:
        trial = f"{current} {word}".strip()
        if font.size(trial)[0] <= max_width:
            current = trial
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines or [""]


def bubble_bottom_y(font):
    """The same fixed-height formula draw_speech_bubble uses, exposed on
    its own so per-level layouts can reserve space for the bubble without
    needing to draw it first - draw order and click hit-testing must agree
    on where the bubble ends, even before a given frame is rendered."""
    line_height = font.get_linesize()
    return BUBBLE_TOP + line_height * BUBBLE_MAX_LINES + BUBBLE_PADDING * 2


def draw_speech_bubble(surface, text, font):
    max_width = WIDTH - 40 - BUBBLE_PADDING * 2
    # Cap at BUBBLE_MAX_LINES so the bubble's height never depends on the
    # actual text - see bubble_bottom_y for why that stability matters.
    lines = wrap_text(text, font, max_width)[:BUBBLE_MAX_LINES]
    line_height = font.get_linesize()
    bubble_height = line_height * BUBBLE_MAX_LINES + BUBBLE_PADDING * 2
    bubble_rect = pygame.Rect(20, BUBBLE_TOP, WIDTH - 40, bubble_height)

    pygame.draw.rect(surface, BUBBLE_COLOR, bubble_rect, border_radius=14)
    pygame.draw.rect(surface, BUBBLE_BORDER, bubble_rect, width=3, border_radius=14)

    for i, line in enumerate(lines):
        rendered = font.render(line, True, BLACK)
        surface.blit(rendered, (bubble_rect.x + BUBBLE_PADDING, bubble_rect.y + BUBBLE_PADDING + i * line_height))

    return bubble_rect.bottom


# ---------------------------------------------------------------------------
# LEVEL 1: RHYTHM OF THE VILLAGE
# ---------------------------------------------------------------------------
def build_beat_schedule(now, cfg=None):
    """Pre-compute the target hit time (ms since pygame start) for every
    beat in the song. Tempo nudges up slightly every 10 beats, down to the
    configured floor."""
    cfg = cfg or RHYTHM_CONFIG
    times = []
    t = now + START_DELAY_MS
    interval = cfg["base_interval_ms"]
    for i in range(BEATS_TOTAL):
        times.append(t)
        t += interval
        if (i + 1) % 10 == 0:
            interval = max(cfg["min_interval_ms"], interval - cfg["tempo_step_ms"])
    return times


def start_rhythm(now):
    return {
        "beat_times": build_beat_schedule(now),
        "spawn_index": 0,
        "notes": [],
        "score": 0,
        "combo": 0,
        "max_combo": 0,
        "last_milestone": 0,
        "perfects": 0,
        "goods": 0,
        "oks": 0,
        "misses": 0,
        "last_hit_time": -9999,
        "finished": False,
    }


def update_rhythm(sub, now, space_pressed, storyteller, sounds):
    cfg = RHYTHM_CONFIG

    # Spawn any notes whose fall should have already begun.
    while (
        sub["spawn_index"] < len(sub["beat_times"])
        and now >= sub["beat_times"][sub["spawn_index"]] - cfg["travel_ms"]
    ):
        target_time = sub["beat_times"][sub["spawn_index"]]
        sub["notes"].append(
            {"target_time": target_time, "judged": False, "result": None, "judged_at": None, "tick_played": False}
        )
        sub["spawn_index"] += 1

    # Play a metronome tick exactly when each beat lands, whether or not
    # the player has hit it yet - this is what gives the falling notes an
    # actual audible rhythm to follow.
    for note in sub["notes"]:
        if not note["tick_played"] and now >= note["target_time"]:
            note["tick_played"] = True
            sounds.play("tick")

    # Handle a SPACE press: judge the nearest un-judged note in range.
    if space_pressed:
        best_note, best_diff = None, None
        for note in sub["notes"]:
            if note["judged"]:
                continue
            diff = abs(now - note["target_time"])
            if diff <= cfg["hit_window_ms"] and (best_diff is None or diff < best_diff):
                best_note, best_diff = note, diff

        if best_note is not None:
            if best_diff <= cfg["perfect_ms"]:
                result, points = "PERFECT", 150
            elif best_diff <= cfg["good_ms"]:
                result, points = "GOOD", 90
            else:
                result, points = "OK", 40

            best_note["judged"] = True
            best_note["result"] = result
            best_note["judged_at"] = now
            sub["last_hit_time"] = now
            sounds.play(result.lower())

            sub["combo"] += 1
            sub["max_combo"] = max(sub["max_combo"], sub["combo"])
            sub["score"] += points + sub["combo"] * 2
            if result == "PERFECT":
                sub["perfects"] += 1
            elif result == "GOOD":
                sub["goods"] += 1
            else:
                sub["oks"] += 1

            if sub["combo"] % 5 == 0 and sub["combo"] != sub["last_milestone"]:
                sub["last_milestone"] = sub["combo"]
                storyteller.trigger("rhythm_milestone", f"combo {sub['combo']}")

    # Auto-miss any note that's fallen well past the hit window unjudged.
    for note in sub["notes"]:
        if not note["judged"] and now > note["target_time"] + cfg["hit_window_ms"]:
            note["judged"] = True
            note["result"] = "MISS"
            note["judged_at"] = now
            sounds.play("miss")
            dropped_combo = sub["combo"]
            sub["combo"] = 0
            sub["last_milestone"] = 0
            sub["misses"] += 1
            storyteller.trigger("rhythm_miss", f"combo was {dropped_combo}")

    # Drop notes a little while after they've been judged (visual fade).
    sub["notes"] = [n for n in sub["notes"] if not n["judged"] or now - n["judged_at"] < 500]

    # Song finished: every beat spawned, judged, and faded.
    if sub["spawn_index"] >= len(sub["beat_times"]) and not sub["notes"]:
        sub["finished"] = True
        sounds.play("end")
        storyteller.trigger("rhythm_end", f"final score {sub['score']}, max combo {sub['max_combo']}")


def draw_rhythm(screen, sub, bubble_bottom, now, fonts):
    font_small, font_med, font_big = fonts
    cfg = RHYTHM_CONFIG

    # Falling-note lane guide
    pygame.draw.line(screen, (70, 55, 50), (LANE_X, bubble_bottom + 10), (LANE_X, HIT_LINE_Y + 40), 2)

    # Hit line / drum
    pulse = max(0, 26 - (now - sub["last_hit_time"]) // 12)
    drum_radius = 34 + min(pulse, 14)
    pygame.draw.circle(screen, (110, 70, 45), (LANE_X, HIT_LINE_Y), drum_radius)
    pygame.draw.circle(screen, EMBER, (LANE_X, HIT_LINE_Y), drum_radius, 4)
    pygame.draw.line(screen, GOLD, (LANE_X - 60, HIT_LINE_Y), (LANE_X + 60, HIT_LINE_Y), 2)

    # Notes should never spawn underneath the story bubble - clamp their
    # start position to whichever is lower, the usual NOTE_START_Y or just
    # past wherever the bubble currently ends.
    note_start_y = max(NOTE_START_Y, bubble_bottom + 20)
    for note in sub["notes"]:
        if not note["judged"]:
            fraction = 1 - (note["target_time"] - now) / cfg["travel_ms"]
            fraction = max(0.0, min(1.2, fraction))
            y = note_start_y + fraction * (HIT_LINE_Y - note_start_y)
            pygame.draw.circle(screen, GOLD, (LANE_X, int(y)), NOTE_RADIUS)
            pygame.draw.circle(screen, BLACK, (LANE_X, int(y)), NOTE_RADIUS, 2)
        else:
            # Floating judgement feedback, fading upward briefly.
            age = now - note["judged_at"]
            color = {"PERFECT": GOLD, "GOOD": GREEN, "OK": BLUE, "MISS": RED}[note["result"]]
            label = font_small.render(note["result"], True, color)
            y_offset = HIT_LINE_Y - 60 - age // 6
            screen.blit(label, label.get_rect(center=(LANE_X, y_offset)))

    # HUD
    score_text = font_med.render(f"Score: {sub['score']}", True, WHITE)
    combo_text = font_med.render(f"Combo: {sub['combo']}", True, GOLD if sub["combo"] > 0 else GREY)
    screen.blit(score_text, (16, HEIGHT - 40))
    screen.blit(combo_text, (WIDTH - combo_text.get_width() - 16, HEIGHT - 40))

    progress = font_small.render(f"Beat {min(sub['spawn_index'], BEATS_TOTAL)} / {BEATS_TOTAL}", True, GREY)
    screen.blit(progress, progress.get_rect(center=(WIDTH / 2, HEIGHT - 40)))


# ---------------------------------------------------------------------------
# LEVEL 2: OWARE TRADE ROUTES
# ---------------------------------------------------------------------------
# Board layout: 12 pits in a single conceptual circle. Indices 0-5 are the
# player's row; indices 6-11 are the elder's row. Sowing always moves in
# increasing index order, wrapping from 11 back to 0 - that single rule is
# what makes the two rows feel like one connected loop.
def sow_seeds(pits, start_idx):
    """Distribute all seeds from `pits[start_idx]` one-by-one into the
    following pits, moving counter-clockwise around the board. Returns the
    index of the pit that received the last seed, which is what matters
    for working out captures. Note: this is a simplified sowing rule - if
    a pit holds enough seeds to loop all the way around, seeds can land
    back in the pit they started from, which some official rule sets
    forbid. That's a deliberate simplification for a casual mini-game."""
    seeds = pits[start_idx]
    pits[start_idx] = 0
    idx = start_idx
    for _ in range(seeds):
        idx = (idx + 1) % 12
        pits[idx] += 1
    return idx


def resolve_capture(pits, last_idx, mover_side):
    """After sowing, capture seeds from consecutive opponent pits ending at
    last_idx, as long as each pit (after sowing) holds exactly 2 or 3
    seeds. Capturing stops as soon as a pit breaks that rule or the chain
    reaches the mover's own side of the board. Returns the total seeds
    captured (already removed from `pits`)."""
    opponent_range = range(6, 12) if mover_side == "player" else range(0, 6)
    captured = 0
    idx = last_idx
    while idx in opponent_range and pits[idx] in (2, 3):
        captured += pits[idx]
        pits[idx] = 0
        idx -= 1  # step backward through the chain, toward where sowing began
    return captured


def apply_move(pits, idx, side):
    """Sow from `idx` (must belong to `side`) and resolve any resulting
    capture. Mutates `pits` in place and returns the number of seeds
    captured. Shared by both the player's real moves and the elder AI's
    real moves (and reused, on a copied board, for the AI's lookahead)."""
    last_idx = sow_seeds(pits, idx)
    opponent_range = range(6, 12) if side == "player" else range(0, 6)
    if last_idx in opponent_range:
        return resolve_capture(pits, last_idx, side)
    return 0


def legal_moves(pits, side):
    idx_range = range(0, 6) if side == "player" else range(6, 12)
    return [i for i in idx_range if pits[i] > 0]


def remaining_seeds(pits, side):
    idx_range = range(0, 6) if side == "player" else range(6, 12)
    return sum(pits[i] for i in idx_range)


def ai_choose_move(pits):
    """Small heuristic AI: simulate every legal move on a copy of the
    board, prefer whichever captures the most seeds this turn, and break
    ties randomly so the elder doesn't feel robotic."""
    moves = legal_moves(pits, "ai")
    if not moves:
        return None
    best_moves, best_capture = [], -1
    for move in moves:
        trial = pits.copy()
        last_idx = sow_seeds(trial, move)
        captured = resolve_capture(trial, last_idx, "ai") if last_idx in range(0, 6) else 0
        if captured > best_capture:
            best_capture, best_moves = captured, [move]
        elif captured == best_capture:
            best_moves.append(move)
    return random.choice(best_moves)


def split_remaining(sub):
    """Used only when the turn cap is hit: each side simply keeps whatever
    seeds are still sitting in their own row."""
    sub["player_store"] += remaining_seeds(sub["pits"], "player")
    sub["ai_store"] += remaining_seeds(sub["pits"], "ai")
    sub["pits"] = [0] * 12


def finish_oware(sub, storyteller):
    if sub["player_store"] > sub["ai_store"]:
        sub["winner"] = "player"
    elif sub["ai_store"] > sub["player_store"]:
        sub["winner"] = "ai"
    else:
        sub["winner"] = "tie"
    storyteller.trigger(
        "oware_end",
        f"final harvest - you {sub['player_store']}, the elder {sub['ai_store']}",
    )


def compute_oware_layout(font_small):
    """Pit positions, derived the same way whether we're drawing this
    frame or hit-testing a click that arrived before it - see
    bubble_bottom_y for why that stability matters. Each element's y is
    stacked explicitly off the one before it (rather than each being
    separately reverse-derived from the pit row, which is what let the
    status/harvest text drift into overlapping the bubble)."""
    status_y = bubble_bottom_y(font_small) + 28
    ai_label_y = status_y + 26
    ai_row_y = ai_label_y + 55
    row_gap = 250
    player_row_y = ai_row_y + row_gap
    margin = 40
    usable_width = WIDTH - margin * 2
    pit_radius = 30
    spacing = usable_width / 6

    pit_rects = {}
    for i in range(6):
        cx = margin + spacing * (i + 0.5)
        rect = pygame.Rect(0, 0, pit_radius * 2, pit_radius * 2)
        rect.center = (int(cx), int(player_row_y))
        pit_rects[i] = rect
    for i in range(6):
        # The elder's row is drawn left-to-right as pits 11..6, so pit 6
        # sits directly above the player's pit 5 - matching how seeds
        # actually flow around the circular board.
        cx = margin + spacing * (i + 0.5)
        pit_index = 11 - i
        rect = pygame.Rect(0, 0, pit_radius * 2, pit_radius * 2)
        rect.center = (int(cx), int(ai_row_y))
        pit_rects[pit_index] = rect

    return {
        "pit_rects": pit_rects,
        "pit_radius": pit_radius,
        "ai_row_y": ai_row_y,
        "player_row_y": player_row_y,
        "status_y": status_y,
        "ai_label_y": ai_label_y,
    }


def start_oware(now):
    seeds = OWARE_CONFIG["start_seeds"]
    return {
        "pits": [seeds] * 12,
        "player_store": 0,
        "ai_store": 0,
        "phase": "PLAYER_TURN",
        "ai_move_at": None,
        "ply_count": 0,
        "last_move_note": "",
        "last_move_at": -9999,
        "winner": None,
    }


def handle_oware_click(sub, pos, font_small, storyteller, sounds, now):
    if sub["phase"] != "PLAYER_TURN":
        return
    layout = compute_oware_layout(font_small)
    for i in range(0, 6):
        if not layout["pit_rects"][i].collidepoint(pos) or sub["pits"][i] == 0:
            continue

        captured = apply_move(sub["pits"], i, "player")
        sub["player_store"] += captured
        sub["ply_count"] += 1
        sub["last_move_at"] = now
        sounds.play("capture" if captured > 0 else "tick")

        if captured > 0:
            sub["last_move_note"] = f"You captured {captured} seed{'s' if captured != 1 else ''}!"
            storyteller.trigger("oware_capture", f"you captured {captured}, your harvest now {sub['player_store']}")
        else:
            sub["last_move_note"] = "You sow your seeds around the board."

        if not legal_moves(sub["pits"], "ai"):
            # The elder has nothing left to play - by the starvation rule,
            # you collect whatever remains on your own side and the game
            # ends here.
            sub["player_store"] += remaining_seeds(sub["pits"], "player")
            sub["pits"] = [0] * 12
            sub["phase"] = "GAME_OVER"
            finish_oware(sub, storyteller)
        elif sub["ply_count"] >= OWARE_CONFIG["max_plies"]:
            split_remaining(sub)
            sub["phase"] = "GAME_OVER"
            finish_oware(sub, storyteller)
        else:
            sub["phase"] = "AI_THINKING"
            sub["ai_move_at"] = now + OWARE_CONFIG["ai_think_ms"]
        return  # only one pit can be clicked per event


def update_oware(sub, now, storyteller, sounds):
    if sub["phase"] != "AI_THINKING" or now < sub["ai_move_at"]:
        return

    move = ai_choose_move(sub["pits"])
    if move is None:
        # Shouldn't happen - we only enter AI_THINKING when the elder has
        # a legal move - but guard against it rather than crash.
        sub["phase"] = "PLAYER_TURN"
        return

    captured = apply_move(sub["pits"], move, "ai")
    sub["ai_store"] += captured
    sub["ply_count"] += 1
    sub["last_move_at"] = now
    sounds.play("capture" if captured > 0 else "tick")

    if captured > 0:
        sub["last_move_note"] = f"The elder captures {captured} seed{'s' if captured != 1 else ''}."
        storyteller.trigger("oware_capture", f"the elder captured {captured}, their harvest now {sub['ai_store']}")
    else:
        sub["last_move_note"] = "The elder sows seeds around the board."

    if not legal_moves(sub["pits"], "player"):
        sub["ai_store"] += remaining_seeds(sub["pits"], "ai")
        sub["pits"] = [0] * 12
        sub["phase"] = "GAME_OVER"
        finish_oware(sub, storyteller)
    elif sub["ply_count"] >= OWARE_CONFIG["max_plies"]:
        split_remaining(sub)
        sub["phase"] = "GAME_OVER"
        finish_oware(sub, storyteller)
    else:
        sub["phase"] = "PLAYER_TURN"


def draw_oware(screen, sub, now, fonts):
    font_small, font_med, font_big = fonts
    layout = compute_oware_layout(font_small)

    status_lines = {
        "PLAYER_TURN": "Your move - click a pit to sow its seeds.",
        "AI_THINKING": "The elder considers the board...",
        "GAME_OVER": "The trading day is done.",
    }
    status = font_small.render(status_lines.get(sub["phase"], ""), True, GREY)
    screen.blit(status, status.get_rect(center=(WIDTH / 2, layout["status_y"])))

    ai_label = font_small.render(f"Elder's harvest: {sub['ai_store']}", True, GOLD)
    screen.blit(ai_label, ai_label.get_rect(center=(WIDTH / 2, layout["ai_label_y"])))

    for i in range(6, 12):
        rect = layout["pit_rects"][i]
        seeds = sub["pits"][i]
        color = EMBER if seeds > 0 else (70, 55, 50)
        pygame.draw.circle(screen, color, rect.center, layout["pit_radius"])
        pygame.draw.circle(screen, GOLD, rect.center, layout["pit_radius"], 2)
        label = font_med.render(str(seeds), True, WHITE)
        screen.blit(label, label.get_rect(center=rect.center))

    for i in range(0, 6):
        rect = layout["pit_rects"][i]
        seeds = sub["pits"][i]
        if seeds == 0:
            color = (70, 55, 50)
        elif sub["phase"] == "PLAYER_TURN":
            color = GREEN  # a gentle highlight showing these pits are playable
        else:
            color = EMBER
        pygame.draw.circle(screen, color, rect.center, layout["pit_radius"])
        pygame.draw.circle(screen, GOLD, rect.center, layout["pit_radius"], 2)
        label = font_med.render(str(seeds), True, WHITE)
        screen.blit(label, label.get_rect(center=rect.center))

    player_label = font_small.render(f"Your harvest: {sub['player_store']}", True, GOLD)
    screen.blit(player_label, player_label.get_rect(center=(WIDTH / 2, layout["player_row_y"] + 55)))

    if sub["last_move_note"] and now - sub["last_move_at"] < 2500:
        note = font_small.render(sub["last_move_note"], True, GREY)
        screen.blit(note, note.get_rect(center=(WIDTH / 2, layout["player_row_y"] + 85)))


# ---------------------------------------------------------------------------
# LEVEL 3: KENTE LOOM
# ---------------------------------------------------------------------------
def compute_kente_layout():
    pad_count = KENTE_CONFIG["num_colors"]
    margin = 30
    usable_width = WIDTH - margin * 2
    slot_width = usable_width / pad_count
    pad_width = slot_width - 12
    pad_height = 90
    y = HEIGHT - 160

    rects = []
    for i in range(pad_count):
        x = margin + i * slot_width + 6
        rects.append(pygame.Rect(int(x), y, int(pad_width), pad_height))
    return rects


def start_kente(now):
    return {
        "sequence": [random.randrange(KENTE_CONFIG["num_colors"])],
        "phase": "SHOWING",
        "show_index": 0,
        "show_started_at": now + KENTE_CONFIG["start_gap_ms"],
        "input_index": 0,
        "best_round": 1,
        "flaws": 0,
        "highlight_pad": None,
        "highlight_until": 0,
        "message": "Watch the thread pattern closely...",
    }


def update_kente(sub, now, storyteller, sounds):
    if sub["phase"] != "SHOWING":
        return

    if sub["highlight_pad"] is not None and now >= sub["highlight_until"]:
        sub["highlight_pad"] = None  # end of the current flash

    if sub["highlight_pad"] is None and now >= sub["show_started_at"]:
        if sub["show_index"] < len(sub["sequence"]):
            color = sub["sequence"][sub["show_index"]]
            sub["highlight_pad"] = color
            sub["highlight_until"] = now + KENTE_CONFIG["show_on_ms"]
            sub["show_started_at"] = now + KENTE_CONFIG["show_on_ms"] + KENTE_CONFIG["show_gap_ms"]
            sub["show_index"] += 1
            sounds.play(f"pad{color}")
        else:
            sub["phase"] = "INPUT"
            sub["input_index"] = 0
            sub["message"] = "Now weave it back - repeat the pattern."


def handle_kente_keydown(sub, key, storyteller, sounds, now):
    if sub["phase"] != "INPUT" or key not in THREAD_KEYS:
        return

    pressed = THREAD_KEYS.index(key)
    sub["highlight_pad"] = pressed
    sub["highlight_until"] = now + 220
    sounds.play(f"pad{pressed}")

    expected = sub["sequence"][sub["input_index"]]
    if pressed == expected:
        sub["input_index"] += 1
        if sub["input_index"] < len(sub["sequence"]):
            return  # more of this pattern still to go

        # A full pattern woven correctly - the cloth grows a row.
        completed_round = len(sub["sequence"])
        sub["best_round"] = max(sub["best_round"], completed_round)
        if completed_round >= KENTE_CONFIG["target_rounds"]:
            sub["phase"] = "COMPLETE"
            sub["message"] = "The cloth is complete!"
            return

        if completed_round % 3 == 0:
            storyteller.trigger("kente_milestone", f"round {completed_round} woven cleanly")

        sub["sequence"].append(random.randrange(KENTE_CONFIG["num_colors"]))
        sub["phase"] = "SHOWING"
        sub["show_index"] = 0
        sub["show_started_at"] = now + KENTE_CONFIG["start_gap_ms"]
        sub["message"] = "Watch the thread pattern closely..."
    else:
        sub["flaws"] += 1
        storyteller.trigger("kente_flaw", f"a thread slipped at pattern length {len(sub['sequence'])}")
        # A gentle stumble, not a stop: the pattern eases back by one
        # thread and the player gets another go at the shorter version.
        if len(sub["sequence"]) > 1:
            sub["sequence"].pop()
        sub["phase"] = "SHOWING"
        sub["show_index"] = 0
        sub["show_started_at"] = now + KENTE_CONFIG["start_gap_ms"]
        sub["message"] = "A thread slipped - watch closely and try again."


def handle_kente_click(sub, pos, storyteller, sounds, now):
    if sub["phase"] != "INPUT":
        return
    for i, rect in enumerate(compute_kente_layout()):
        if rect.collidepoint(pos):
            handle_kente_keydown(sub, THREAD_KEYS[i], storyteller, sounds, now)
            return


def draw_kente(screen, sub, now, fonts):
    font_small, font_med, font_big = fonts
    current_length = len(sub["sequence"])

    # Positioned relative to the bubble's actual bottom edge (the same
    # pattern compute_oware_layout uses) rather than fixed pixel values,
    # so this stays correctly spaced if the bubble's height ever changes.
    base_y = bubble_bottom_y(font_small) + 40

    status_lines = {
        "SHOWING": "Watch the loom...",
        "INPUT": "Your turn - repeat the pattern.",
        "COMPLETE": "The cloth is complete!",
    }
    status = font_small.render(status_lines.get(sub["phase"], ""), True, GREY)
    screen.blit(status, status.get_rect(center=(WIDTH / 2, base_y)))

    round_render = font_med.render(f"Pattern length: {current_length} / {KENTE_CONFIG['target_rounds']}", True, GOLD)
    screen.blit(round_render, round_render.get_rect(center=(WIDTH / 2, base_y + 35)))

    # Progress bar representing the growing cloth.
    bar_rect = pygame.Rect(60, int(base_y + 65), WIDTH - 120, 18)
    pygame.draw.rect(screen, (70, 55, 50), bar_rect, border_radius=9)
    fill_width = int(bar_rect.width * min(1.0, sub["best_round"] / KENTE_CONFIG["target_rounds"]))
    if fill_width > 0:
        pygame.draw.rect(screen, GOLD, (bar_rect.x, bar_rect.y, fill_width, bar_rect.height), border_radius=9)

    flaw_render = font_small.render(f"Flaws: {sub['flaws']}", True, GREY)
    screen.blit(flaw_render, flaw_render.get_rect(center=(WIDTH / 2, base_y + 100)))

    message_render = font_small.render(sub["message"], True, WHITE)
    screen.blit(message_render, message_render.get_rect(center=(WIDTH / 2, base_y + 150)))

    for i, rect in enumerate(compute_kente_layout()):
        base_color = THREAD_COLORS[i]
        lit = sub["highlight_pad"] == i and now < sub["highlight_until"]
        color = tuple(min(255, c + 60) for c in base_color) if lit else base_color
        pygame.draw.rect(screen, color, rect, border_radius=14)
        pygame.draw.rect(screen, BLACK, rect, width=3, border_radius=14)
        label = font_med.render(THREAD_LABELS[i], True, BLACK)
        screen.blit(label, label.get_rect(center=rect.center))


# ---------------------------------------------------------------------------
# TITLE / END SCREENS
# ---------------------------------------------------------------------------
def draw_title(screen, fonts):
    font_small, font_med, font_big = fonts

    title = font_big.render("Village Nights", True, GOLD)
    screen.blit(title, title.get_rect(center=(WIDTH / 2, 90)))
    subtitle = font_small.render("Choose a level - each one is a different game.", True, GREY)
    screen.blit(subtitle, subtitle.get_rect(center=(WIDTH / 2, 130)))

    y = 220
    for key in ("1", "2", "3"):
        level = LEVEL_KEYS[getattr(pygame, f"K_{key}")]
        info = LEVEL_INFO[level]
        header = font_med.render(f"{key} - {info['title']}", True, GOLD)
        screen.blit(header, header.get_rect(center=(WIDTH / 2, y)))
        tag = font_small.render(info["tag"], True, EMBER)
        screen.blit(tag, tag.get_rect(center=(WIDTH / 2, y + 26)))
        hook = font_small.render(info["hook"], True, GREY)
        screen.blit(hook, hook.get_rect(center=(WIDTH / 2, y + 50)))
        y += 130

    hint = font_small.render("Press 1, 2, or 3 to begin.", True, WHITE)
    screen.blit(hint, hint.get_rect(center=(WIDTH / 2, y + 20)))


MENU_BUTTON_LABEL = "Menu (Esc)"


def compute_menu_button_rect(font_small):
    """Top-right corner, inside the strip reserved above the Storyteller's
    bubble (see BUBBLE_TOP). Drawn and hit-tested from this exact same
    rect - the same pattern used for Oware's pits and Kente's pads - so a
    click always lands on what's actually on screen. It's a pure function
    of the font, not of draw order, so it can be called just as safely
    from event handling (before this frame is drawn) as from drawing."""
    label = font_small.render(MENU_BUTTON_LABEL, True, WHITE)
    pad_x, pad_y = 14, 6
    rect = pygame.Rect(0, 0, label.get_width() + pad_x * 2, label.get_height() + pad_y * 2)
    rect.topright = (WIDTH - 12, 6)
    return rect


def draw_menu_button(screen, font_small, mouse_pos):
    """Draw the return-to-menu button, lit up on hover so it reads as an
    actual clickable control rather than an instructional label."""
    rect = compute_menu_button_rect(font_small)
    hovered = rect.collidepoint(mouse_pos)
    pygame.draw.rect(screen, EMBER if hovered else (70, 55, 50), rect, border_radius=8)
    pygame.draw.rect(screen, GOLD, rect, width=2, border_radius=8)
    label = font_small.render(MENU_BUTTON_LABEL, True, WHITE)
    screen.blit(label, label.get_rect(center=rect.center))


def draw_story_end_overlay(screen, game, fonts):
    font_small, font_med, font_big = fonts
    overlay = pygame.Surface((WIDTH, HEIGHT))
    overlay.set_alpha(150)
    overlay.fill(BLACK)
    screen.blit(overlay, (0, 0))

    level, sub = game["level"], game["sub"]

    heading_text = {
        "rhythm": "The Tale Rests",
        "oware": "The Trading Day Ends",
        "kente": "The Cloth is Finished",
    }[level]
    heading = font_big.render(heading_text, True, GOLD)
    screen.blit(heading, heading.get_rect(center=(WIDTH / 2, HEIGHT / 2 - 110)))

    if level == "rhythm":
        lines = [
            f"Final Score: {sub['score']}",
            f"Best Combo: {sub['max_combo']}",
            f"Perfect: {sub['perfects']}   Good: {sub['goods']}   OK: {sub['oks']}   Missed: {sub['misses']}",
        ]
    elif level == "oware":
        if sub["winner"] == "player":
            result_line = "You won the day's trade!"
        elif sub["winner"] == "ai":
            result_line = "The elder outwitted you this time."
        else:
            result_line = "An even trade - a tie!"
        lines = [
            f"Your harvest: {sub['player_store']}   Elder's harvest: {sub['ai_store']}",
            result_line,
        ]
    else:  # kente
        lines = [
            f"Longest pattern woven: {sub['best_round']} / {KENTE_CONFIG['target_rounds']}",
            f"Flaws: {sub['flaws']}",
        ]

    y = HEIGHT / 2 - 50
    for line in lines:
        rendered = font_small.render(line, True, WHITE)
        screen.blit(rendered, rendered.get_rect(center=(WIDTH / 2, y)))
        y += 30

    retry = font_small.render("SPACE to replay   -   1 / 2 / 3 for a different game", True, GREY)
    screen.blit(retry, retry.get_rect(center=(WIDTH / 2, y + 20)))


# ---------------------------------------------------------------------------
# MAIN GAME
# ---------------------------------------------------------------------------
def main():
    pygame.init()
    pygame.display.set_caption("Village Nights")
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    clock = pygame.time.Clock()

    font_small = pygame.font.SysFont("arial", 18)
    font_med = pygame.font.SysFont("arial", 24, bold=True)
    font_big = pygame.font.SysFont("arial", 40, bold=True)
    fonts = (font_small, font_med, font_big)

    storyteller = Commentator()
    sounds = SoundBank()

    starters = {"rhythm": start_rhythm, "oware": start_oware, "kente": start_kente}

    def new_game(level, now):
        """Build a fresh top-level game state for the chosen level and
        kick off the Storyteller's opening line for it."""
        sub = starters[level](now)
        storyteller.trigger(f"{level}_start", LEVEL_INFO[level]["title"])
        sounds.play("start")
        return {"state": "PLAYING", "level": level, "sub": sub}

    game = {"state": "TITLE", "level": None, "sub": None}
    running = True

    while running:
        now = pygame.time.get_ticks()
        mouse_pos = pygame.mouse.get_pos()
        space_pressed = False

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if game["state"] in ("PLAYING", "STORY_END"):
                        game = {"state": "TITLE", "level": None, "sub": None}
                    else:
                        running = False
                elif event.key in LEVEL_KEYS and game["state"] in ("TITLE", "STORY_END"):
                    game = new_game(LEVEL_KEYS[event.key], now)
                elif event.key == pygame.K_SPACE and game["state"] == "STORY_END":
                    game = new_game(game["level"], now)
                elif game["state"] == "PLAYING" and game["level"] == "rhythm" and event.key == pygame.K_SPACE:
                    space_pressed = True
                elif game["state"] == "PLAYING" and game["level"] == "kente":
                    handle_kente_keydown(game["sub"], event.key, storyteller, sounds, now)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if game["state"] in ("PLAYING", "STORY_END") and compute_menu_button_rect(font_small).collidepoint(event.pos):
                    game = {"state": "TITLE", "level": None, "sub": None}
                elif game["state"] == "PLAYING" and game["level"] == "oware":
                    handle_oware_click(game["sub"], event.pos, font_small, storyteller, sounds, now)
                elif game["state"] == "PLAYING" and game["level"] == "kente":
                    handle_kente_click(game["sub"], event.pos, storyteller, sounds, now)

        # --- UPDATE ------------------------------------------------------
        if game["state"] == "PLAYING":
            level, sub = game["level"], game["sub"]
            if level == "rhythm":
                update_rhythm(sub, now, space_pressed, storyteller, sounds)
                if sub["finished"]:
                    game["state"] = "STORY_END"
            elif level == "oware":
                update_oware(sub, now, storyteller, sounds)
                if sub["phase"] == "GAME_OVER":
                    game["state"] = "STORY_END"
            elif level == "kente":
                update_kente(sub, now, storyteller, sounds)
                if sub["phase"] == "COMPLETE":
                    game["state"] = "STORY_END"
                    sounds.play("end")
                    storyteller.trigger("kente_end", f"longest pattern {sub['best_round']}, flaws {sub['flaws']}")

        # --- DRAW ----------------------------------------------------------
        screen.fill(NIGHT)

        if game["state"] == "TITLE":
            draw_title(screen, fonts)
        else:
            bubble_bottom = draw_speech_bubble(screen, storyteller.get_text(), font_small)
            level, sub = game["level"], game["sub"]
            if level == "rhythm":
                draw_rhythm(screen, sub, bubble_bottom, now, fonts)
            elif level == "oware":
                draw_oware(screen, sub, now, fonts)
            elif level == "kente":
                draw_kente(screen, sub, now, fonts)

            if game["state"] == "STORY_END":
                draw_story_end_overlay(screen, game, fonts)

            # Drawn last so it's always fully lit, never dimmed by the
            # STORY_END overlay drawn just above.
            draw_menu_button(screen, font_small, mouse_pos)

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()


if __name__ == "__main__":
    main()