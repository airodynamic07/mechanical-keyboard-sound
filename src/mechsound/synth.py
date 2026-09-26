"""Procedural synthesis of mechanical switch sounds.

Every sound is generated at startup from a few layered components, so the
app ships without any audio files:

* a filtered noise burst for the plastic "clack" of the keycap,
* a decaying low tone for the "thock" of the switch bottoming out,
* an optional sharp high click (clicky switches such as blues),
* a delayed rattle for stabilised keys (space, enter, backspace, shift).

Small random variations per render keep repeated keystrokes from sounding
like a machine gun.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass

import numpy as np

SAMPLE_RATE = 44100


class KeyKind(enum.Enum):
    NORMAL = "normal"
    SPACE = "space"
    ENTER = "enter"
    BACKSPACE = "backspace"
    MODIFIER = "modifier"


# Stabilised keys are bigger and sound lower and longer than alphas.
_KIND_PITCH = {
    KeyKind.NORMAL: 1.0,
    KeyKind.MODIFIER: 0.92,
    KeyKind.BACKSPACE: 0.85,
    KeyKind.ENTER: 0.8,
    KeyKind.SPACE: 0.7,
}
_STABILISED = {KeyKind.SPACE, KeyKind.ENTER, KeyKind.BACKSPACE, KeyKind.MODIFIER}


@dataclass(frozen=True)
class SwitchProfile:
    name: str
    description: str
    clack_freq: float  # centre frequency of the keycap noise burst (Hz)
    clack_gain: float
    thock_freq: float  # frequency of the bottom-out tone (Hz)
    thock_gain: float
    decay: float  # overall decay time constant (seconds)
    click_gain: float = 0.0  # high click leaf, clicky switches only
    release_gain: float = 0.45


PROFILES: dict[str, SwitchProfile] = {
    p.name: p
    for p in (
        SwitchProfile(
            name="blue",
            description="Clicky: sharp click on press and release",
            clack_freq=3800,
            clack_gain=0.55,
            thock_freq=420,
            thock_gain=0.35,
            decay=0.018,
            click_gain=0.9,
            release_gain=0.6,
        ),
        SwitchProfile(
            name="brown",
            description="Tactile: muted bump, medium clack",
            clack_freq=2600,
            clack_gain=0.7,
            thock_freq=320,
            thock_gain=0.5,
            decay=0.024,
        ),
        SwitchProfile(
            name="red",
            description="Linear: smooth, softer clack",
            clack_freq=2200,
            clack_gain=0.6,
            thock_freq=280,
            thock_gain=0.55,
            decay=0.026,
            release_gain=0.35,
        ),
        SwitchProfile(
            name="thock",
            description="Lubed linear in a dampened case: deep and creamy",
            clack_freq=1300,
            clack_gain=0.45,
            thock_freq=170,
            thock_gain=0.9,
            decay=0.04,
            release_gain=0.25,
        ),
    )
}

DEFAULT_PROFILE = "brown"


def _time(duration: float) -> np.ndarray:
    return np.arange(int(duration * SAMPLE_RATE)) / SAMPLE_RATE


def _band_noise(rng: np.random.Generator, n: int, centre: float, width: float) -> np.ndarray:
    """White noise band-passed with a Gaussian mask in the frequency domain."""
    spectrum = np.fft.rfft(rng.standard_normal(n))
    freqs = np.fft.rfftfreq(n, 1 / SAMPLE_RATE)
    spectrum *= np.exp(-0.5 * ((freqs - centre) / width) ** 2)
    out = np.fft.irfft(spectrum, n)
    peak = np.max(np.abs(out))
    return out / peak if peak > 0 else out


def _place(buf: np.ndarray, sound: np.ndarray, offset: float) -> None:
    start = int(offset * SAMPLE_RATE)
    end = min(len(buf), start + len(sound))
    if start < end:
        buf[start:end] += sound[: end - start]


def _normalise(buf: np.ndarray, level: float) -> np.ndarray:
    peak = np.max(np.abs(buf))
    if peak > 0:
        buf = buf * (level / peak)
    # Short fade-in/out so sounds never start or end with a pop.
    fade = min(len(buf) // 4, int(0.002 * SAMPLE_RATE))
    if fade:
        ramp = np.linspace(0.0, 1.0, fade)
        buf[:fade] *= ramp
        buf[-fade:] *= ramp[::-1]
    return buf.astype(np.float32)


def render_press(
    profile: SwitchProfile, kind: KeyKind, rng: np.random.Generator
) -> np.ndarray:
    """Render one key-down sound as mono float32 samples in [-1, 1]."""
    pitch = _KIND_PITCH[kind] * rng.uniform(0.94, 1.06)
    decay = profile.decay / _KIND_PITCH[kind]
    length = decay * 8 + (0.06 if kind in _STABILISED else 0.0)
    t = _time(length)
    buf = np.zeros_like(t)

    offset = 0.0
    if profile.click_gain:
        # The click leaf snaps a few ms before the switch bottoms out.
        click_t = _time(0.006)
        click = _band_noise(rng, len(click_t), 5500 * pitch, 900) * np.exp(-click_t / 0.0012)
        _place(buf, click * profile.click_gain, 0.0)
        offset = rng.uniform(0.004, 0.007)

    clack = _band_noise(rng, len(t), profile.clack_freq * pitch, profile.clack_freq * 0.35)
    clack *= np.exp(-t / decay)
    _place(buf, clack * profile.clack_gain, offset)

    thock = np.sin(2 * np.pi * profile.thock_freq * pitch * t) * np.exp(-t / (decay * 2.5))
    _place(buf, thock * profile.thock_gain, offset)

    if kind in _STABILISED:
        rattle_t = _time(decay * 3)
        rattle = _band_noise(rng, len(rattle_t), 1800 * pitch, 600) * np.exp(-rattle_t / (decay * 0.7))
        _place(buf, rattle * 0.25, offset + rng.uniform(0.012, 0.02))

    return _normalise(buf, rng.uniform(0.8, 0.95))


def render_release(
    profile: SwitchProfile, kind: KeyKind, rng: np.random.Generator
) -> np.ndarray:
    """Render one key-up sound: a lighter, higher top-out clack."""
    pitch = _KIND_PITCH[kind] * rng.uniform(0.94, 1.06)
    decay = profile.decay * 0.6
    t = _time(decay * 8)
    buf = _band_noise(rng, len(t), profile.clack_freq * 1.2 * pitch, profile.clack_freq * 0.3)
    buf *= np.exp(-t / decay)
    if profile.click_gain:
        buf += _band_noise(rng, len(t), 5000 * pitch, 900) * np.exp(-t / 0.001) * 0.6
    return _normalise(buf, profile.release_gain * rng.uniform(0.85, 1.0))


SoundBank = dict[tuple[KeyKind, bool], list[np.ndarray]]


def build_bank(profile: SwitchProfile, variants: int = 6, seed: int | None = None) -> SoundBank:
    """Pre-render ``variants`` press and release sounds for every key kind.

    Keys are ``(kind, is_press)``.
    """
    rng = np.random.default_rng(seed)
    bank: SoundBank = {}
    for kind in KeyKind:
        bank[(kind, True)] = [render_press(profile, kind, rng) for _ in range(variants)]
        bank[(kind, False)] = [render_release(profile, kind, rng) for _ in range(variants)]
    return bank


def to_int16_stereo(samples: np.ndarray) -> np.ndarray:
    """Convert mono float samples to the interleaved int16 layout pygame expects."""
    mono = np.clip(samples, -1.0, 1.0)
    pcm = (mono * 32767).astype(np.int16)
    return np.ascontiguousarray(np.column_stack((pcm, pcm)))
