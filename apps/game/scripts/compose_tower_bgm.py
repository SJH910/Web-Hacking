#!/usr/bin/env python3
"""Render the original ambient theme for Yongbeom's Tower as a looping WAV."""

from array import array
import math
from pathlib import Path
import struct
import wave


SAMPLE_RATE = 22050
BPM = 76
BEAT = 60 / BPM
BAR = BEAT * 4
BAR_COUNT = 16
TOTAL_SECONDS = BAR * BAR_COUNT
TOTAL_SAMPLES = round(TOTAL_SECONDS * SAMPLE_RATE)
LEFT = array("f", [0.0]) * TOTAL_SAMPLES
RIGHT = array("f", [0.0]) * TOTAL_SAMPLES


def midi_hz(note: int) -> float:
    return 440 * 2 ** ((note - 69) / 12)


def envelope(position: int, length: int, attack: int, release: int, sustain: float) -> float:
    if position < attack:
        return position / max(1, attack)
    remaining = length - position
    if remaining < release:
        return max(0.0, remaining / max(1, release)) * sustain
    return sustain


def add_tone(
    note: int,
    start_seconds: float,
    duration: float,
    amplitude: float,
    patch: str,
    pan: float = 0.0,
) -> None:
    start = round(start_seconds * SAMPLE_RATE)
    if start >= TOTAL_SAMPLES:
        return
    length = min(round(duration * SAMPLE_RATE), TOTAL_SAMPLES - start)
    frequency = midi_hz(note)
    attacks = {"choir": 1.15, "pad": 2.2, "bell": 0.004, "harp": 0.008}
    releases = {"choir": 1.4, "pad": 2.6, "bell": 0.12, "harp": 0.08}
    attack = round(attacks[patch] * SAMPLE_RATE)
    release = round(releases[patch] * SAMPLE_RATE)
    left_gain = math.sqrt((1 - pan) * 0.5)
    right_gain = math.sqrt((1 + pan) * 0.5)

    if patch == "choir":
        partials = ((1, 1.0), (2, 0.24), (3, 0.12), (4, 0.08), (5, 0.035))
        sustain = 0.66
    elif patch == "pad":
        partials = ((1, 1.0), (2, 0.12), (3, 0.045))
        sustain = 0.55
    elif patch == "bell":
        partials = ((1, 1.0), (2, 0.72), (3, 0.41), (4, 0.25), (5, 0.16), (6, 0.09))
        sustain = 0.8
    else:
        partials = ((1, 1.0), (2, 0.47), (3, 0.25), (4, 0.12), (5, 0.06))
        sustain = 0.72

    for offset in range(length):
        t = offset / SAMPLE_RATE
        env = envelope(offset, length, attack, release, sustain)
        if patch in ("harp", "bell"):
            env *= math.exp((-3.1 if patch == "harp" else -2.0) * t)

        vibrato = 1 + 0.0025 * math.sin(2 * math.pi * 0.18 * t) if patch == "choir" else 1.0
        shimmer = 1 + 0.04 * math.sin(2 * math.pi * 0.11 * t) if patch == "pad" else 1.0

        sample = 0.0
        for harmonic, weight in partials:
            partial_frequency = frequency * harmonic
            if patch == "bell":
                partial_frequency *= 1 + harmonic * harmonic * 0.0017
            sample += weight * math.sin(2 * math.pi * partial_frequency * vibrato * t)
        sample *= amplitude * env * shimmer

        index = start + offset
        LEFT[index] += sample * left_gain
        RIGHT[index] += sample * right_gain


CHORDS = [
    (38, [50, 57, 62, 64, 69]),  # Dm(add9)
    (34, [46, 53, 58, 62, 65]),  # Bbmaj7
    (33, [45, 53, 57, 60, 64]),  # Fmaj7/A
    (36, [48, 55, 60, 62, 67]),  # Csus2
    (31, [43, 50, 55, 58, 62]),  # Gm9
    (29, [41, 50, 53, 57, 62]),  # Dm/F
    (34, [46, 53, 58, 62, 65]),  # Bbmaj7
    (33, [45, 52, 57, 59, 64]),  # Asus4
]

# The second pass resolves gently to D minor for a seamless ambient loop.
ARRANGEMENT = CHORDS + CHORDS[:7] + [(38, [50, 57, 62, 64, 69])]

CELESTA_THEME = [
    [(0.0, 81, 1.25), (2.0, 77, 0.8)],
    [(1.0, 74, 1.0), (2.5, 77, 0.7)],
    [(0.0, 77, 1.15), (2.0, 84, 0.8)],
    [(1.0, 79, 0.9), (3.0, 76, 1.1)],
    [(0.5, 74, 1.0), (2.0, 81, 0.75)],
    [(0.0, 77, 1.0), (2.5, 74, 0.85)],
    [(0.5, 81, 1.2), (2.0, 86, 0.7)],
    [(0.0, 84, 0.9), (2.0, 81, 1.2)],
]


def compose() -> None:
    for bar_index, (bass_note, chord_notes) in enumerate(ARRANGEMENT):
        start = bar_index * BAR
        intensity = 0.78 if bar_index < 4 else 0.9 if bar_index < 12 else 1.0

        for voice_index, note in enumerate(chord_notes):
            add_tone(note + 12, start, BAR * 1.12, 0.035 * intensity, "choir", (voice_index - 2) * 0.18)
            add_tone(note, start, BAR * 1.12, 0.018 * intensity, "pad", (voice_index - 2) * 0.2)

        add_tone(bass_note, start, BAR * 1.05, 0.065 * intensity, "pad", -0.08)
        add_tone(bass_note + 12, start + BEAT * 2, BEAT * 2.0, 0.024 * intensity, "choir", 0.1)

        for beat_offset, note, duration in CELESTA_THEME[bar_index % len(CELESTA_THEME)]:
            note_start = start + beat_offset * BEAT
            add_tone(note, note_start, duration * BEAT, 0.045 * intensity, "bell", 0.18)
            add_tone(note - 12, note_start + 0.035, duration * BEAT * 0.9, 0.014 * intensity, "choir", -0.16)

        if bar_index >= 2:
            for beat_offset, note_index in ((0.5, 1), (2.5, 3)):
                note = chord_notes[note_index % len(chord_notes)] + 24
                add_tone(note, start + beat_offset * BEAT, 1.1 * BEAT, 0.023 * intensity, "harp", 0.42)

    # Add a short deterministic fade so the loop boundary is clean.
    fade_samples = round(0.18 * SAMPLE_RATE)
    for offset in range(fade_samples):
        gain = offset / fade_samples
        LEFT[offset] *= gain
        RIGHT[offset] *= gain
        LEFT[TOTAL_SAMPLES - fade_samples + offset] *= 1 - gain
        RIGHT[TOTAL_SAMPLES - fade_samples + offset] *= 1 - gain


def write_wav(path: Path) -> None:
    peak = max(max(abs(value) for value in LEFT), max(abs(value) for value in RIGHT))
    normalization = 0.88 / peak if peak else 1.0
    path.parent.mkdir(parents=True, exist_ok=True)

    with wave.open(str(path), "wb") as output:
        output.setnchannels(2)
        output.setsampwidth(2)
        output.setframerate(SAMPLE_RATE)

        frames = bytearray()
        for left, right in zip(LEFT, RIGHT):
            frames.extend(struct.pack(
                "<hh",
                round(max(-1, min(1, left * normalization)) * 32767),
                round(max(-1, min(1, right * normalization)) * 32767),
            ))
        output.writeframes(frames)


if __name__ == "__main__":
    compose()
    destination = Path(__file__).resolve().parents[1] / "public" / "audio" / "yongbeom-tower-theme.wav"
    write_wav(destination)
    print(f"Rendered {TOTAL_SECONDS:.1f}s original ambient theme to {destination}")
