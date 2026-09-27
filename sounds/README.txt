Put your keyboard recordings in this folder. With start.bat, right-click the
key icon next to the clock and pick one under "Sound" to switch between them.

From the command line, run:

    mechsound --sounds sounds

Supported formats: .wav .ogg .mp3 .flac

How files are used (by the start of the file name):

    key1.wav, key2.wav, ...   normal keys (any other name works too)
    space.wav                 space bar
    enter.wav                 enter
    backspace.wav             backspace / delete
    modifier.wav              shift, ctrl, alt, tab, caps lock
    release.wav               when a key is let go (optional)

Tips:
- The easiest option: one recording of someone typing on a mechanical
  keyboard. It is cut into single keystrokes automatically, and every key
  on your keyboard gets its own sound from it.
- You can also add separate files with one keystroke each (key1, key2...).
  Silence at the start and end is cut off automatically.
- Missing space/enter/backspace/modifier files are fine: normal key sounds
  are used instead.
