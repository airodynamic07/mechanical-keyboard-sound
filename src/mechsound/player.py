"""Low-latency playback of a pre-rendered sound bank through pygame.mixer."""

from __future__ import annotations

import random

from mechsound.synth import SAMPLE_RATE, KeyKind, SoundBank, to_int16_stereo


class Player:
    def __init__(self, bank: SoundBank, volume: float = 0.7, channels: int = 32) -> None:
        import pygame

        # A small buffer keeps the delay between keypress and sound unnoticeable.
        pygame.mixer.pre_init(SAMPLE_RATE, -16, 2, 256)
        pygame.mixer.init()
        pygame.mixer.set_num_channels(channels)
        self._sounds = {
            key: [pygame.sndarray.make_sound(to_int16_stereo(s)) for s in variants]
            for key, variants in bank.items()
        }
        self.volume = volume

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
        random.choice(self._sounds[(kind, press)]).play()

    def close(self) -> None:
        import pygame

        pygame.mixer.quit()
