import os

import numpy as np
import pytest

from mechsound.cli import main
from mechsound.recordings import scan, trim_silence
from mechsound.synth import KeyKind


def _touch(directory, *names):
    for name in names:
        (directory / name).write_bytes(b"")


def test_scan_groups_by_file_name(tmp_path):
    _touch(tmp_path, "key1.wav", "Key2.MP3", "space.wav", "release.ogg", "notes.txt")
    bank = scan(tmp_path)
    assert [p.name for p in bank[(KeyKind.NORMAL, True)]] == ["Key2.MP3", "key1.wav"]
    assert [p.name for p in bank[(KeyKind.SPACE, True)]] == ["space.wav"]
    # No enter recording: falls back to the normal key sounds.
    assert bank[(KeyKind.ENTER, True)] == bank[(KeyKind.NORMAL, True)]
    assert [p.name for p in bank[(KeyKind.SPACE, False)]] == ["release.ogg"]


def test_scan_without_release_files_has_no_release_sounds(tmp_path):
    _touch(tmp_path, "a.wav")
    bank = scan(tmp_path)
    assert (KeyKind.NORMAL, False) not in bank


def test_scan_errors(tmp_path):
    with pytest.raises(FileNotFoundError):
        scan(tmp_path / "missing")
    _touch(tmp_path, "space.wav", "readme.txt")
    with pytest.raises(ValueError):
        scan(tmp_path)


def test_trim_silence_removes_quiet_lead_in_and_tail():
    samples = np.zeros((44100, 2), dtype=np.int16)
    samples[20000:20100] = 10000
    trimmed = trim_silence(samples)
    assert len(trimmed) < 200
    assert np.abs(trimmed).max() == 10000


def test_trim_silence_keeps_all_silent_input():
    samples = np.zeros(100, dtype=np.int16)
    assert len(trim_silence(samples)) == 100


def test_player_loads_real_files(tmp_path, monkeypatch):
    monkeypatch.setenv("SDL_AUDIODRIVER", "dummy")
    wav_dir = tmp_path / "wav"
    main(["--export", str(wav_dir)])
    sounds = tmp_path / "sounds"
    sounds.mkdir()
    for src, dst in [("normal_press_0.wav", "key.wav"), ("space_press_0.wav", "space.wav"),
                     ("normal_release_0.wav", "release.wav")]:
        (sounds / dst).write_bytes((wav_dir / src).read_bytes())

    from mechsound.player import Player

    player = Player(scan(sounds))
    try:
        player.play(KeyKind.NORMAL)
        player.play(KeyKind.ENTER)
        player.play(KeyKind.SPACE, press=False)
    finally:
        player.close()


def test_cli_reports_bad_folder(tmp_path, capsys):
    assert main(["--sounds", str(tmp_path / "nope"), "--demo"]) == 1
    assert "not found" in capsys.readouterr().err


def _typing(n_keys, rate=44100, spacing=0.18):
    """Fake recording: quiet hiss with ``n_keys`` decaying clicks."""
    rng = np.random.default_rng(0)
    samples = rng.normal(0, 50, int(rate * (0.3 + n_keys * spacing)))
    t = np.arange(int(0.05 * rate)) / rate
    for i in range(n_keys):
        start = int((0.2 + i * spacing) * rate)
        samples[start:start + len(t)] += 12000 * rng.uniform(0.6, 1.0) * np.exp(-t / 0.008) * rng.normal(0, 1, len(t))
    pcm = np.clip(samples, -32767, 32767).astype(np.int16)
    return np.column_stack((pcm, pcm))


def test_split_keystrokes_finds_each_key():
    from mechsound.recordings import split_keystrokes

    clips = split_keystrokes(_typing(12))
    assert len(clips) == 12
    for clip in clips:
        assert clip.dtype == np.int16 and clip.shape[1] == 2
        assert len(clip) < 0.2 * 44100


def test_split_keeps_single_keystroke_whole_but_trimmed():
    from mechsound.recordings import split_keystrokes

    clips = split_keystrokes(_typing(1))
    assert len(clips) == 1
    assert len(clips[0]) < 0.1 * 44100  # lead-in silence removed


def test_long_file_becomes_many_sounds_and_keys_keep_their_sound(tmp_path, monkeypatch):
    import wave

    monkeypatch.setenv("SDL_AUDIODRIVER", "dummy")
    with wave.open(str(tmp_path / "typing.wav"), "wb") as f:
        f.setnchannels(2)
        f.setsampwidth(2)
        f.setframerate(44100)
        f.writeframes(_typing(20).tobytes())

    from mechsound.player import Player

    player = Player(scan(tmp_path))
    try:
        assert player.sound_count() == 20
        # The space bar falls back to the same file without loading it twice.
        assert player.sound_count(KeyKind.SPACE) == 20

        a = [player.pick(KeyKind.NORMAL, key="a") for _ in range(3)]
        assert a[0] is a[1] is a[2]
        others = {id(player.pick(KeyKind.NORMAL, key=k)) for k in "bcdefghijk"}
        assert len(others) > 5  # different keys spread over different sounds

        player.per_key = False
        assert len({id(player.pick(KeyKind.NORMAL, key="a")) for _ in range(30)}) > 1
    finally:
        player.close()


def test_scan_only_one_key_file(tmp_path):
    _touch(tmp_path, "a.wav", "b.wav", "space.wav")
    bank = scan(tmp_path, only="b.wav")
    assert [p.name for p in bank[(KeyKind.NORMAL, True)]] == ["b.wav"]
    assert [p.name for p in bank[(KeyKind.SPACE, True)]] == ["space.wav"]
