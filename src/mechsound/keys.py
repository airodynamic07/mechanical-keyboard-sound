"""Map pynput key events onto the key kinds the synthesiser knows about."""

from __future__ import annotations

from mechsound.synth import KeyKind

_BY_NAME = {
    "space": KeyKind.SPACE,
    "enter": KeyKind.ENTER,
    "backspace": KeyKind.BACKSPACE,
    "delete": KeyKind.BACKSPACE,
}
_MODIFIER_PREFIXES = ("shift", "ctrl", "alt", "cmd", "caps_lock", "tab")


def key_id(key: object) -> str:
    """A stable identifier for a pynput ``Key`` or ``KeyCode``.

    Used both to classify the key and to tell auto-repeat apart from a new
    press of a different key.
    """
    name = getattr(key, "name", None)
    if name:
        return name
    vk = getattr(key, "vk", None)
    if vk is not None:
        return f"vk{vk}"
    char = getattr(key, "char", None)
    return char if char is not None else repr(key)


def classify(identifier: str) -> KeyKind:
    if identifier in _BY_NAME:
        return _BY_NAME[identifier]
    if identifier.startswith(_MODIFIER_PREFIXES):
        return KeyKind.MODIFIER
    return KeyKind.NORMAL
