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


class _FakeIcon:
    def __init__(self, fail_show=0, fail_notify=False):
        # fail_show: how many attempts to show the icon fail before one works.
        self.fail_show, self.fail_notify = fail_show, fail_notify
        self.notified = None
        self._visible = False

    @property
    def visible(self):
        return self._visible

    @visible.setter
    def visible(self, value):
        if self.fail_show:
            self.fail_show -= 1
            raise OSError("Shell_NotifyIcon failed")
        self._visible = value

    def notify(self, message, title=None):
        if self.fail_notify:
            raise RuntimeError("no notifications")
        self.notified = message


def test_show_icon_notifies_on_success(monkeypatch):
    errors = []
    monkeypatch.setattr(tray, "_show_error", errors.append)
    icon = _FakeIcon()
    tray.show_icon(icon, "hello")
    assert icon.visible and icon.notified == "hello" and errors == []


def test_show_icon_reports_failure_instead_of_dying_silently(monkeypatch):
    errors = []
    monkeypatch.setattr(tray, "_show_error", errors.append)
    tray.show_icon(_FakeIcon(fail_show=99), "hello", attempts=3, delay=0)
    assert len(errors) == 1 and "Shell_NotifyIcon failed" in errors[0]


def test_show_icon_retries_when_taskbar_is_busy(monkeypatch):
    errors = []
    monkeypatch.setattr(tray, "_show_error", errors.append)
    icon = _FakeIcon(fail_show=2)
    tray.show_icon(icon, "hello", attempts=5, delay=0)
    assert icon.visible and icon.notified == "hello" and errors == []


def test_check_tray_add_only_raises_for_failed_add(monkeypatch):
    import ctypes

    monkeypatch.setattr(ctypes, "WinError", lambda: OSError("refused"), raising=False)
    assert tray._check_tray_add(1, None, (tray._NIM_ADD, None)) == 1
    assert tray._check_tray_add(0, None, (2, None)) == 0  # failed delete: ignore
    with pytest.raises(OSError, match="refused"):
        tray._check_tray_add(0, None, (tray._NIM_ADD, None))


def test_failed_notification_is_not_an_error(monkeypatch):
    errors = []
    monkeypatch.setattr(tray, "_show_error", errors.append)
    icon = _FakeIcon(fail_notify=True)
    tray.show_icon(icon, "hello")
    assert icon.visible and errors == []


def test_logging_writes_crashes_to_file(tmp_path, monkeypatch):
    import sys
    import threading

    monkeypatch.setattr(tray, "_show_error", lambda m: None)
    monkeypatch.setattr(sys, "excepthook", sys.excepthook)
    monkeypatch.setattr(threading, "excepthook", threading.excepthook)
    log_file = tmp_path / "mechsound.log"
    tray._setup_logging(log_file)
    try:
        t = threading.Thread(target=lambda: 1 / 0, name="setup")
        t.start()
        t.join()
        for h in tray.log.handlers:
            h.flush()
        text = log_file.read_text()
        assert "crash in setup" in text and "ZeroDivisionError" in text
    finally:
        for h in list(tray.log.handlers):
            tray.log.removeHandler(h)
            h.close()
