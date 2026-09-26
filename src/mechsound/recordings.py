"""Use real keyboard recordings instead of synthesised sounds.

Put audio files in a folder and pass it with ``--sounds``. The start of each
file name decides when it plays:

* ``space*``, ``enter*``, ``backspace*``, ``modifier*`` play for those keys,
* ``release*`` plays when any key is let go,
* every other file plays for normal keys.

Keys without their own recordings fall back to the normal-key sounds. With
several files for the same key, one is picked at random on each press.
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
