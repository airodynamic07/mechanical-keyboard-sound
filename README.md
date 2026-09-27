# mechanical-keyboard-sound

`mechsound` is a small desktop app that plays a mechanical keyboard sound every time you press a key, in any application.

All sounds are synthesized when the app starts, so there are no audio files to download. Every keystroke is picked from several slightly different variants, and space, enter, backspace and modifier keys sound deeper, like stabilized keys on a real board.

## Install

Requires Python 3.9+.

**Windows, the easy way:** double-click `start.bat`. The first run sets everything up (about a minute). After that a key icon appears in the system tray, next to the clock:

- **left-click** the icon to turn the sound on or off (it turns grey with a red line when off),
- **right-click** it for **Sound**, **Volume** and **Quit**.

The **Sound** menu lists every sound file in the `sounds` folder by name, then the built-in sounds. Click one to switch right away; your pick is remembered for next time. With several files you can also choose **All my sounds mixed**. For a Desktop icon, right-click `start.bat` → *Show more options* → *Send to* → *Desktop (create shortcut)*.

The tray app can also be started directly with `mechsound-tray` (it takes `--sounds`, `--profile` and `--volume` too; `--profile` starts with that built-in sound).

**Any platform, by hand:**

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e .
```

## Usage

```bash
mechsound                     # start listening (Ctrl+C to quit)
mechsound -p blue -v 0.5      # clicky switches at half volume
mechsound --list              # show switch profiles
mechsound --demo -p thock     # hear a profile without typing
mechsound --export sounds/    # save the generated sounds as WAV files
```

| Option | Description |
| --- | --- |
| `-p, --profile` | `blue`, `brown` (default), `red`, `thock`, `deep`, `clicky`, `soft`, `mix` |
| `-v, --volume` | 0.0 to 1.0 (default 0.7) |
| `-s, --sounds` | folder of your own recordings to play instead |
| `--no-release` | only play a sound on key down |
| `--repeat` | also play a sound for auto-repeat while a key is held |
| `--random` | random sound on every press instead of one sound per key |

| Profile | Sound |
| --- | --- |
| `blue` | clicky: sharp click on press and release |
| `brown` | tactile: muted bump, medium clack |
| `red` | linear: smooth, softer clack |
| `thock` | lubed linear in a dampened case: deep and creamy |
| `deep` | heavy bass: low, rounded bottom-out with little clack |
| `clicky` | extra clicky: loud, crisp click like a typewriter |
| `soft` | quiet and gentle, easy on the ears for long sessions |
| `mix` | deep bass with a light click, at a gentle volume |

## Use real keyboard recordings

Put audio files (`.wav`, `.ogg`, `.mp3` or `.flac`) in the `sounds` folder and run:

```bash
mechsound --sounds sounds
```

The start of each file name decides when it plays:

| File name | Plays for |
| --- | --- |
| `space*` | space bar |
| `enter*` | enter |
| `backspace*` | backspace and delete |
| `modifier*` | shift, ctrl, alt, tab, caps lock |
| `release*` | any key being let go (optional) |
| anything else | all other keys |

A file can hold a single keystroke or a whole recording of someone typing: long recordings are cut into one sound per keystroke automatically. Silence at the start and end is trimmed so the sound plays the instant you press the key. Keys without their own recordings use the normal key sounds.

Like on a real keyboard, each key always plays its own sound from the pool, so `A` always sounds like `A` and `K` like `K`. Use `--random` to pick a random sound on every press instead.

You can record your own keyboard with a phone, or download free recordings, for example from [freesound.org](https://freesound.org/search/?q=mechanical+keyboard). Check each sound's license before sharing it.

## Platform notes

Global key capture uses [pynput](https://pynput.readthedocs.io/):

- **macOS**: give your terminal (or Python) permission under *System Settings → Privacy & Security → Accessibility* and *Input Monitoring*.
- **Linux**: works under X11. On Wayland, global key capture is blocked unless you run under XWayland or use the `uinput` backend as root.
- **Windows**: works out of the box.

The app only listens for which key was pressed so it can choose a sound. It does not record or store what you type.

## Development

```bash
pip install -e '.[dev]'
pytest
```

Code layout:

- `src/mechsound/synth.py`: procedural sound synthesis and switch profiles
- `src/mechsound/keys.py`: maps key events to key kinds
- `src/mechsound/recordings.py`: loads your own recordings from a folder
- `src/mechsound/player.py`: low-latency playback with `pygame.mixer`
- `src/mechsound/cli.py`: command-line entry point and keyboard listener
- `src/mechsound/tray.py`: system tray app
