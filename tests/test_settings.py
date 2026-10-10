import json
from pets_in_editor import settings


def test_settings_roundtrip(tmp_path, monkeypatch):
    path = tmp_path / ".moleditpy" / "pets_in_editor.json"
    monkeypatch.setattr(settings, "PATH", path)

    settings.save({
        "enabled": False,
        "selected": "sample",
        "scale": 1.25,
        "speed": 100,
    })
    result = settings.load()
    assert result == {
        "enabled": False,
        "selected": "sample",
        "scale": 1.25,
        "speed": 100,
    }


def test_settings_clamp_values(tmp_path, monkeypatch):
    path = tmp_path / "settings.json"
    monkeypatch.setattr(settings, "PATH", path)
    path.write_text(json.dumps({"scale": 99, "speed": -5}))
    result = settings.load()
    assert result["scale"] == 2.0
    assert result["speed"] == 0
