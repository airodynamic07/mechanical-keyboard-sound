import numpy as np
import pytest

from mechsound.synth import (
    PROFILES,
    KeyKind,
    build_bank,
    render_press,
    to_int16_stereo,
)


@pytest.mark.parametrize("name", sorted(PROFILES))
def test_bank_covers_every_kind_and_stays_in_range(name):
    bank = build_bank(PROFILES[name], variants=2, seed=0)
    assert set(bank) == {(k, p) for k in KeyKind for p in (True, False)}
    for variants in bank.values():
        assert len(variants) == 2
        for s in variants:
            assert s.dtype == np.float32
            assert len(s) > 0
            assert np.all(np.isfinite(s))
            assert np.max(np.abs(s)) <= 1.0
            # Faded in and out, so no click at the edges.
            assert abs(s[0]) < 1e-3 and abs(s[-1]) < 1e-3


def test_seed_is_deterministic():
    a = build_bank(PROFILES["blue"], variants=1, seed=42)
    b = build_bank(PROFILES["blue"], variants=1, seed=42)
    for key in a:
        np.testing.assert_array_equal(a[key][0], b[key][0])


def test_variants_differ():
    bank = build_bank(PROFILES["red"], variants=3, seed=1)
    first, second, _ = bank[(KeyKind.NORMAL, True)]
    assert len(first) != len(second) or not np.array_equal(first, second)


def test_space_is_longer_than_alpha():
    rng = np.random.default_rng(0)
    alpha = render_press(PROFILES["brown"], KeyKind.NORMAL, rng)
    space = render_press(PROFILES["brown"], KeyKind.SPACE, rng)
    assert len(space) > len(alpha)


def test_int16_stereo_layout():
    out = to_int16_stereo(np.array([0.0, 1.0, -1.0, 2.0], dtype=np.float32))
    assert out.shape == (4, 2)
    assert out.dtype == np.int16
    assert out[:, 0].tolist() == [0, 32767, -32767, 32767]
    assert out.flags["C_CONTIGUOUS"]
