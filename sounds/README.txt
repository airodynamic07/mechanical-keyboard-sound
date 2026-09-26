Put your keyboard recordings in this folder, then run:

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
- Add several different key sounds (key1, key2, key3...). One is picked at
  random each press, which sounds much more natural.
- Each file should contain ONE keystroke. Silence at the start and end is
  cut off automatically.
- Missing space/enter/backspace/modifier files are fine: normal key sounds
  are used instead.
