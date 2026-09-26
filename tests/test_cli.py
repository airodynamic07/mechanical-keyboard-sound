from mechsound.cli import main


def test_list(capsys):
    assert main(["--list"]) == 0
    out = capsys.readouterr().out
    assert "blue" in out and "(default)" in out


def test_export(tmp_path):
    assert main(["--profile", "thock", "--export", str(tmp_path)]) == 0
    files = list(tmp_path.glob("*.wav"))
    assert files
    assert (tmp_path / "space_press_0.wav").exists()
