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
