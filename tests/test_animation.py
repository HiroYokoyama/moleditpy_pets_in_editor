from pets_in_editor.animation import default_tracks
from pets_in_editor.pet_loader import Pet
from pathlib import Path


def fake_pet(rows=9):
    return Pet(
        identifier="sample",
        name="Sample",
        description="",
        atlas=Path("unused.png"),
        manifest={},
        folder=Path("."),
        frame_width=192,
        frame_height=208,
        columns=8,
        rows=rows,
    )


def test_codex_direction_rows_are_correct():
    tracks = default_tracks(fake_pet())
    assert tracks["idle"].frames == (0, 1, 2, 3, 4, 5)
    assert tracks["running-right"].frames == tuple(range(8, 16))
    assert tracks["running-left"].frames == tuple(range(16, 24))


def test_codex_state_rows_are_correct():
    tracks = default_tracks(fake_pet())
    assert tracks["waving"].frames == (24, 25, 26, 27)
    assert tracks["jumping"].frames == (32, 33, 34, 35, 36)
    assert tracks["failed"].frames == tuple(range(40, 48))
    assert tracks["waiting"].frames == tuple(range(48, 54))
    assert tracks["running"].frames == tuple(range(56, 62))
    assert tracks["review"].frames == tuple(range(64, 70))
