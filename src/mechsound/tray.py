"""Run mechsound from an icon in the system tray (next to the clock).

Left-click the icon to turn the sound on or off; right-click for volume and
quit. Installed as the windowless ``mechsound-tray`` program, so there is no
console window to keep open.
"""

from __future__ import annotations

import argparse
import socket
import sys
from pathlib import Path

from mechsound.recordings import EXTENSIONS, scan
from mechsound.synth import DEFAULT_PROFILE, PROFILES, build_bank

# Holding this local port open marks the tray app as running, so a second
# double-click doesn't start a second copy playing every sound twice.
_INSTANCE_PORT = 47913

VOLUMES = (0.25, 0.5, 0.75, 1.0)

# The ``sounds`` folder of the project this package was installed from.
PROJECT_SOUNDS = Path(__file__).resolve().parents[2] / "sounds"


def default_sounds_dir(candidate: Path = PROJECT_SOUNDS) -> Path | None:
    """``candidate`` if it holds any recordings, else None (use built-in sounds)."""
    if candidate.is_dir() and any(p.suffix.lower() in EXTENSIONS for p in candidate.iterdir()):
        return candidate
    return None


def make_icon_image(on: bool, size: int = 64):
    """A keycap: bright when the sound is on, grey with a slash when muted."""
    from PIL import Image, ImageDraw

    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    s = size / 64
    side, top = ((52, 168, 83), (98, 205, 125)) if on else ((110, 110, 110), (160, 160, 160))
    draw.rounded_rectangle([4 * s, 8 * s, 60 * s, 58 * s], radius=10 * s, fill=side)
    draw.rounded_rectangle([12 * s, 10 * s, 52 * s, 46 * s], radius=7 * s, fill=top)
    # A small "legend" bar on the keycap.
    draw.rounded_rectangle([24 * s, 24 * s, 40 * s, 30 * s], radius=3 * s, fill=(255, 255, 255))
    if not on:
        draw.line([8 * s, 56 * s, 56 * s, 6 * s], fill=(220, 50, 50), width=max(2, int(6 * s)))
    return img


def _show_error(message: str) -> None:
    """Pop up an error: the tray app has no console to print to."""
    if sys.platform == "win32":
        import ctypes

        ctypes.windll.user32.MessageBoxW(None, message, "mechsound", 0x10)
    else:
        print(f"mechsound: {message}", file=sys.stderr)


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="mechsound-tray", description="Run mechsound from a system tray icon."
    )
    parser.add_argument("-p", "--profile", choices=sorted(PROFILES), default=DEFAULT_PROFILE)
    parser.add_argument("-v", "--volume", type=float, default=0.75)
    parser.add_argument(
        "-s", "--sounds", type=Path, help=f"recordings folder (default: {PROJECT_SOUNDS})"
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    lock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        lock.bind(("127.0.0.1", _INSTANCE_PORT))
    except OSError:
        _show_error("Keyboard sounds are already running. Look for the key icon next to the clock.")
        return 1

    try:
        sounds = args.sounds or default_sounds_dir()
        bank = scan(sounds) if sounds else build_bank(PROFILES[args.profile])

        import pystray

        from mechsound.cli import make_listener
        from mechsound.player import Player

        player = Player(bank, volume=args.volume)
    except Exception as exc:  # anything here would otherwise vanish silently
        _show_error(f"Could not start: {exc}")
        return 1

    source = f"your sounds ({player.sound_count()})" if sounds else f"'{args.profile}' sounds"

    def title() -> str:
        state = "off" if player.muted else "on"
        return f"Keyboard sounds {state} - {source}"

    def refresh(icon) -> None:
        icon.icon = make_icon_image(not player.muted)
        icon.title = title()
        icon.update_menu()

    def toggle(icon, _item) -> None:
        player.muted = not player.muted
        refresh(icon)

    def set_volume(value):
        def action(icon, _item) -> None:
            player.volume = value
            player.muted = False
            refresh(icon)

        return action

    def quit_app(icon, _item) -> None:
        icon.stop()

    menu = pystray.Menu(
        pystray.MenuItem(
            "Sound on", toggle, checked=lambda _item: not player.muted, default=True
        ),
        pystray.MenuItem(
            "Volume",
            pystray.Menu(
                *(
                    pystray.MenuItem(
                        f"{int(v * 100)}%",
                        set_volume(v),
                        checked=lambda _item, v=v: abs(player.volume - v) < 0.01,
                        radio=True,
                    )
                    for v in VOLUMES
                )
            ),
        ),
        pystray.MenuItem("Quit", quit_app),
    )
    icon = pystray.Icon("mechsound", make_icon_image(True), title(), menu)

    listener = make_listener(player, release=True, repeat=False)
    listener.daemon = True
    listener.start()
    try:
        icon.run()
    finally:
        listener.stop()
        player.close()
        lock.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
