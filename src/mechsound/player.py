"""Low-latency playback through pygame.mixer.

The bank maps ``(kind, is_press)`` to either synthesised sample arrays or
paths of audio files to load.
"""

from __future__ import annotations

import os
import random
from pathlib import Path

from mechsound.recordings import trim_silence
from mechsound.synth import SAMPLE_RATE, KeyKind, to_int16_stereo


class Player:
    def __init__(self, bank: dict, volume: float = 0.7, channels: int = 32) -> None:
        os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
        import pygame

        # A small buffer keeps the delay between keypress and sound unnoticeable.
        pygame.mixer.pre_init(SAMPLE_RATE, -16, 2, 256)
        pygame.mixer.init()
        pygame.mixer.set_num_channels(channels)
        self._sounds = {
            key: [self._load(pygame, source) for source in variants]
            for key, variants in bank.items()
        }
        self.volume = volume

    @staticmethod
    def _load(pygame, source):
        if isinstance(source, Path):
            try:
                sound = pygame.mixer.Sound(str(source))
            except pygame.error as exc:
                raise ValueError(f"could not load {source.name}: {exc}") from None
            samples = trim_silence(pygame.sndarray.array(sound))
            return pygame.sndarray.make_sound(samples.copy(order="C"))
        return pygame.sndarray.make_sound(to_int16_stereo(source))

    @property
    def volume(self) -> float:
        return self._volume

    @volume.setter
    def volume(self, value: float) -> None:
        self._volume = max(0.0, min(1.0, value))
        for variants in self._sounds.values():
            for sound in variants:
                sound.set_volume(self._volume)

    def play(self, kind: KeyKind, press: bool = True) -> None:
        variants = self._sounds.get((kind, press))
        if variants:
            random.choice(variants).play()

    def close(self) -> None:
        import pygame

        pygame.mixer.quit()
