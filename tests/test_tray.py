import socket

import pytest

from mechsound import tray


def test_icon_images_differ_by_state():
    on = tray.make_icon_image(True)
    off = tray.make_icon_image(False)
    assert on.size == off.size == (64, 64)
    assert on.tobytes() != off.tobytes()


def test_default_sounds_dir(tmp_path):
    assert tray.default_sounds_dir(tmp_path / "missing") is None
    (tmp_path / "README.txt").write_text("instructions only")
    assert tray.default_sounds_dir(tmp_path) is None
    (tmp_path / "typing.MP3").write_bytes(b"")
    assert tray.default_sounds_dir(tmp_path) == tmp_path


def test_project_sounds_folder_is_found():
    assert tray.PROJECT_SOUNDS.name == "sounds"
    assert (tray.PROJECT_SOUNDS / "README.txt").exists()


def test_second_copy_refuses_to_start(monkeypatch):
    messages = []
    monkeypatch.setattr(tray, "_show_error", messages.append)
    holder = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        holder.bind(("127.0.0.1", tray._INSTANCE_PORT))
    except OSError:
        pytest.skip("port in use by something else")
    try:
        assert tray.main([]) == 1
        assert "already running" in messages[0]
    finally:
        holder.close()


def test_muted_player_is_silent(monkeypatch):
    monkeypatch.setenv("SDL_AUDIODRIVER", "dummy")
    from mechsound.player import Player
    from mechsound.synth import PROFILES, KeyKind, build_bank

    player = Player(build_bank(PROFILES["red"], variants=1, seed=0))
    try:
        played = []
        monkeypatch.setattr(player, "pick", lambda *a, **k: played.append(a))
        player.muted = True
        player.play(KeyKind.NORMAL, key="a")
        assert played == []
        player.muted = False
        player.play(KeyKind.NORMAL, key="a")
        assert len(played) == 1
    finally:
        player.close()


def test_sound_choices_list_each_file_then_builtins(tmp_path):
    for name in ("typing-blue.wav", "typing-red.mp3", "space.wav", "release.wav"):
        (tmp_path / name).write_bytes(b"")
    choices = tray.sound_choices(tmp_path)
    assert choices[:3] == [
        ("file:typing-blue.wav", "typing-blue"),
        ("file:typing-red.mp3", "typing-red"),
        (tray.ALL_FILES, "All my sounds mixed"),
    ]
    assert ("profile:brown", "Built-in: brown") in choices
    # No folder: only the built-in sounds.
    assert all(c.startswith("profile:") for c, _ in tray.sound_choices(None))


def test_initial_choice(tmp_path):
    assert tray.initial_choice(None, None, None) == f"profile:{tray.DEFAULT_PROFILE}"
    (tmp_path / "one.wav").write_bytes(b"")
    assert tray.initial_choice(None, tmp_path, None) == "file:one.wav"
    (tmp_path / "two.wav").write_bytes(b"")
    assert tray.initial_choice(None, tmp_path, None) == tray.ALL_FILES
    assert tray.initial_choice(None, tmp_path, "file:two.wav") == "file:two.wav"
    # A remembered file that was deleted is ignored.
    assert tray.initial_choice(None, tmp_path, "file:gone.wav") == tray.ALL_FILES
    assert tray.initial_choice("blue", tmp_path, "file:two.wav") == "profile:blue"


def test_choice_is_remembered(tmp_path):
    path = tmp_path / "choice"
    assert tray.read_choice(path) is None
    tray.save_choice("file:two.wav", path)
    assert tray.read_choice(path) == "file:two.wav"


def test_switching_sounds_while_running(tmp_path, monkeypatch):
    monkeypatch.setenv("SDL_AUDIODRIVER", "dummy")
    from mechsound.cli import main as cli_main
    from mechsound.player import Player
    from mechsound.synth import KeyKind

    wav_dir = tmp_path / "wav"
    cli_main(["--export", str(wav_dir), "-p", "blue"])
    sounds = tmp_path / "sounds"
    sounds.mkdir()
    for i, dst in enumerate(("a.wav", "b.wav")):
        (sounds / dst).write_bytes((wav_dir / f"normal_press_{i}.wav").read_bytes())

    player = Player(tray.load_bank("file:a.wav", sounds), volume=0.5)
    try:
        assert player.sound_count() == 1
        player.set_bank(tray.load_bank(tray.ALL_FILES, sounds))
        assert player.sound_count() == 2
        assert player.pick(KeyKind.NORMAL, key="a").get_volume() == pytest.approx(0.5, abs=0.01)
        player.set_bank(tray.load_bank("profile:red", sounds))
        assert player.sound_count() > 2
    finally:
        player.close()
