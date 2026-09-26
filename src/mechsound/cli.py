"""Command-line entry point: ``mechsound [--profile NAME] [--volume V] ...``."""

from __future__ import annotations

import argparse
import sys
import threading
import time
import wave
from pathlib import Path

from mechsound import __version__
from mechsound.keys import classify, key_id
from mechsound.synth import (
    DEFAULT_PROFILE,
    PROFILES,
    SAMPLE_RATE,
    KeyKind,
    build_bank,
    to_int16_stereo,
)


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="mechsound",
        description="Play mechanical keyboard sounds for every key you press.",
    )
    parser.add_argument("-p", "--profile", choices=sorted(PROFILES), default=DEFAULT_PROFILE)
    parser.add_argument(
        "-v", "--volume", type=float, default=0.7, help="0.0 to 1.0 (default: 0.7)"
    )
    parser.add_argument(
        "--no-release", action="store_true", help="only play a sound on key down"
    )
    parser.add_argument(
        "--repeat", action="store_true", help="play a sound for every auto-repeat of a held key"
    )
    parser.add_argument("--list", action="store_true", help="list switch profiles and exit")
    parser.add_argument(
        "--demo", action="store_true", help="play a short typing demo instead of listening"
    )
    parser.add_argument(
        "--export", metavar="DIR", type=Path, help="write the rendered sounds as WAV files to DIR"
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser.parse_args(argv)


def _export(bank, directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    for (kind, press), variants in bank.items():
        for i, samples in enumerate(variants):
            path = directory / f"{kind.value}_{'press' if press else 'release'}_{i}.wav"
            with wave.open(str(path), "wb") as f:
                f.setnchannels(2)
                f.setsampwidth(2)
                f.setframerate(SAMPLE_RATE)
                f.writeframes(to_int16_stereo(samples).tobytes())
    print(f"Wrote {sum(len(v) for v in bank.values())} files to {directory}")


def _demo(player, release: bool) -> None:
    text = "hello world, this is mechsound.\n"
    for ch in text:
        kind = {" ": KeyKind.SPACE, "\n": KeyKind.ENTER}.get(ch, KeyKind.NORMAL)
        player.play(kind, press=True)
        time.sleep(0.07)
        if release:
            player.play(kind, press=False)
        time.sleep(0.03 + (0.12 if ch in " .,\n" else 0.0))
    time.sleep(0.3)


def _listen(player, release: bool, repeat: bool) -> None:
    from pynput import keyboard

    held: set[str] = set()
    lock = threading.Lock()

    def on_press(key) -> None:
        ident = key_id(key)
        with lock:
            if ident in held and not repeat:
                return
            held.add(ident)
        player.play(classify(ident), press=True)

    def on_release(key) -> None:
        ident = key_id(key)
        with lock:
            held.discard(ident)
        if release:
            player.play(classify(ident), press=False)

    with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
        listener.join()


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    if args.list:
        for name in sorted(PROFILES):
            marker = " (default)" if name == DEFAULT_PROFILE else ""
            print(f"{name:<8}{PROFILES[name].description}{marker}")
        return 0

    bank = build_bank(PROFILES[args.profile])

    if args.export:
        _export(bank, args.export)
        return 0

    from mechsound.player import Player

    player = Player(bank, volume=args.volume)
    try:
        if args.demo:
            _demo(player, release=not args.no_release)
        else:
            print(f"mechsound: '{args.profile}' switches at volume {player.volume:.2f}. Ctrl+C to quit.")
            _listen(player, release=not args.no_release, repeat=args.repeat)
    except KeyboardInterrupt:
        pass
    finally:
        player.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
