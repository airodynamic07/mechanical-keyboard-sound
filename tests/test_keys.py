from types import SimpleNamespace

from mechsound.keys import classify, key_id
from mechsound.synth import KeyKind


def test_key_id_prefers_name_then_vk_then_char():
    assert key_id(SimpleNamespace(name="space")) == "space"
    assert key_id(SimpleNamespace(vk=65, char="a")) == "vk65"
    assert key_id(SimpleNamespace(vk=None, char="a")) == "a"


def test_classify():
    assert classify("space") is KeyKind.SPACE
    assert classify("enter") is KeyKind.ENTER
    assert classify("backspace") is KeyKind.BACKSPACE
    assert classify("delete") is KeyKind.BACKSPACE
    assert classify("shift_r") is KeyKind.MODIFIER
    assert classify("ctrl_l") is KeyKind.MODIFIER
    assert classify("vk65") is KeyKind.NORMAL
    assert classify("a") is KeyKind.NORMAL
