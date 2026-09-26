"""Low-latency playback through pygame.mixer.

The bank maps ``(kind, is_press)`` to either synthesised sample arrays or
paths of audio files to load. A file holding a recording of someone typing
is cut into one sound per keystroke.

By default each key always plays the same sound from the pool, so every
key has its own voice like on a real keyboard.
"""

from __future__ import annotations

import os
import random
import zlib
from pathlib import Path

from mechsound.recordings import split_keystrokes
from mechsound.synth import SAMPLE_RATE, KeyKind, to_int16_stereo


class Player:
    def __init__(
        self, bank: dict, volume: float = 0.7, channels: int = 32, per_key: bool = True
    ) -> None:
        os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
        # Otherwise SDL swallows Ctrl+C and termination requests.
        os.environ.setdefault("SDL_NO_SIGNAL_HANDLERS", "1")
        import pygame

        # A small buffer keeps the delay between keypress and sound unnoticeable.
        pygame.mixer.pre_init(SAMPLE_RATE, -16, 2, 256)
        pygame.mixer.init()
        pygame.mixer.set_num_channels(channels)
        rate = pygame.mixer.get_init()[0]
        files: dict[Path, list] = {}  # the same file can back several key kinds
        self._sounds = {}
        for key, variants in bank.items():
            sounds = []
            for source in variants:
                if isinstance(source, Path):
                    if source not in files:
                        files[source] = self._load_file(pygame, source, rate)
                    sounds.extend(files[source])
                else:
                    sounds.append(pygame.sndarray.make_sound(to_int16_stereo(source)))
            self._sounds[key] = sounds
        self.per_key = per_key
        self.muted = False
        self.volume = volume

    @staticmethod
    def _load_file(pygame, path: Path, rate: int) -> list:
        try:
            sound = pygame.mixer.Sound(str(path))
        except pygame.error as exc:
            raise ValueError(f"could not load {path.name}: {exc}") from None
        clips = split_keystrokes(pygame.sndarray.array(sound), rate)
        return [pygame.sndarray.make_sound(c.copy(order="C")) for c in clips]

    def sound_count(self, kind: KeyKind = KeyKind.NORMAL, press: bool = True) -> int:
        return len(self._sounds.get((kind, press), []))

    @property
    def volume(self) -> float:
        return self._volume

    @volume.setter
    def volume(self, value: float) -> None:
        self._volume = max(0.0, min(1.0, value))
        for variants in self._sounds.values():
            for sound in variants:
                sound.set_volume(self._volume)

    def pick(self, kind: KeyKind, press: bool = True, key: str | None = None):
        """The sound to play for this key, or None if there is none."""
        variants = self._sounds.get((kind, press))
        if not variants:
            return None
        if self.per_key and key is not None:
            # crc32 rather than hash(): stable across runs, so a key keeps its sound.
            return variants[zlib.crc32(key.encode()) % len(variants)]
        return random.choice(variants)

    def play(self, kind: KeyKind, press: bool = True, key: str | None = None) -> None:
        if self.muted:
            return
        sound = self.pick(kind, press, key)
        if sound is not None:
            sound.play()

    def close(self) -> None:
        import pygame

        pygame.mixer.quit()
