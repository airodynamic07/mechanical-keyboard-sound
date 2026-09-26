"""Use real keyboard recordings instead of synthesised sounds.

Put audio files in a folder and pass it with ``--sounds``. The start of each
file name decides when it plays:

* ``space*``, ``enter*``, ``backspace*``, ``modifier*`` play for those keys,
* ``release*`` plays when any key is let go,
* every other file plays for normal keys.

Keys without their own recordings fall back to the normal-key sounds. With
several sounds for the same kind of key, each key gets its own one. A file
with a recording of someone typing is cut into single keystrokes.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from mechsound.synth import SAMPLE_RATE, KeyKind

EXTENSIONS = {".wav", ".ogg", ".mp3", ".flac"}

_PREFIXES = {
    "space": KeyKind.SPACE,
    "enter": KeyKind.ENTER,
    "backspace": KeyKind.BACKSPACE,
    "modifier": KeyKind.MODIFIER,
}

RecordingBank = dict[tuple[KeyKind, bool], list[Path]]


def scan(directory: Path) -> RecordingBank:
    """Group the audio files in ``directory`` by the key they belong to."""
    if not directory.is_dir():
        raise FileNotFoundError(f"sound folder not found: {directory}")

    bank: RecordingBank = {}
    for path in sorted(directory.iterdir()):
        if path.suffix.lower() not in EXTENSIONS:
            continue
        stem = path.stem.lower()
        if stem.startswith("release"):
            key = (KeyKind.NORMAL, False)
        else:
            kind = next((k for p, k in _PREFIXES.items() if stem.startswith(p)), KeyKind.NORMAL)
            key = (kind, True)
        bank.setdefault(key, []).append(path)

    if (KeyKind.NORMAL, True) not in bank:
        raise ValueError(
            f"no key sounds in {directory}: add at least one audio file "
            f"({', '.join(sorted(EXTENSIONS))}) not starting with space/enter/backspace/modifier/release"
        )

    for kind in KeyKind:
        bank.setdefault((kind, True), bank[(KeyKind.NORMAL, True)])
        if (KeyKind.NORMAL, False) in bank:
            bank.setdefault((kind, False), bank[(KeyKind.NORMAL, False)])
    return bank


def trim_silence(samples: np.ndarray, threshold: float = 0.02) -> np.ndarray:
    """Cut quiet lead-in so the sound starts the instant a key is pressed.

    Recordings usually begin with a little silence, which would be heard as
    lag. ``threshold`` is relative to the loudest sample.
    """
    level = np.abs(samples.astype(np.float32))
    if level.ndim > 1:
        level = level.max(axis=1)
    peak = level.max() if len(level) else 0
    if peak == 0:
        return samples
    loud = np.nonzero(level >= peak * threshold)[0]
    start = max(0, loud[0] - int(0.001 * SAMPLE_RATE))
    end = loud[-1] + 1
    return samples[start:end]


def split_keystrokes(
    samples: np.ndarray,
    rate: int = SAMPLE_RATE,
    min_gap: float = 0.06,
    max_length: float = 0.35,
    max_clips: int = 200,
) -> list[np.ndarray]:
    """Cut a recording of someone typing into one clip per keystroke.

    Keystrokes are found as jumps in loudness above the background noise,
    at least ``min_gap`` seconds apart. A recording with a single keystroke
    comes back as one clip.
    """
    whole = [trim_silence(samples)]
    level = np.abs(samples.astype(np.float32))
    if level.ndim > 1:
        level = level.max(axis=1)
    hop = max(1, int(0.005 * rate))
    frames = len(level) // hop
    if frames < 2:
        return whole
    energy = level[: frames * hop].reshape(frames, hop).max(axis=1)
    floor = np.percentile(energy, 20)
    top = np.percentile(energy, 99.5)
    if top <= floor:
        return whole
    threshold = floor + 0.2 * (top - floor)

    onsets: list[int] = []
    gap = int(min_gap * rate / hop)
    for i in range(1, frames):
        if energy[i] >= threshold > energy[i - 1] and (not onsets or i - onsets[-1] >= gap):
            onsets.append(i)
    if len(onsets) <= 1:
        return whole

    pad = int(0.002 * rate)
    fade = int(0.01 * rate)
    clips = []
    for n, onset in enumerate(onsets[:max_clips]):
        start = max(0, onset * hop - pad)
        end = start + int(max_length * rate)
        if n + 1 < len(onsets):
            end = min(end, onsets[n + 1] * hop - pad)
        clip = trim_silence(samples[start:end])
        if len(clip) < int(0.015 * rate):
            continue
        clip = clip.astype(np.float32)
        # Fade out so a clip cut short by the next keystroke doesn't pop.
        n_fade = min(fade, len(clip) // 2)
        ramp = np.linspace(1.0, 0.0, n_fade)
        clip[-n_fade:] *= ramp[:, None] if clip.ndim > 1 else ramp
        clips.append(clip.astype(samples.dtype))
    return clips or whole
