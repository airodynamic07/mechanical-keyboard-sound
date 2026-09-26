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
