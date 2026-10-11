from dataclasses import replace
from pathlib import Path

from pets_in_editor.animation import Animator, default_tracks
from pets_in_editor.pet_loader import Pet


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


def test_short_sheet_never_references_missing_rows():
    pet = fake_pet(rows=1)
    tracks = default_tracks(pet)
    assert set(tracks) == {"idle"}
    assert all(frame < pet.frame_count for track in tracks.values() for frame in track.frames)


def test_animator_custom_timing_and_large_elapsed_time(pet_asset):
    pet = replace(
        pet_asset,
        manifest={
            "animations": {"idle": {"frames": [2, 3], "fps": 10}},
        },
    )
    animator = Animator(pet)
    animator.advance(150)
    assert animator.index == 1
    assert animator.elapsed == 50
    animator.advance(1_000_000)
    assert animator.index == 1
    assert animator.elapsed == 50
    assert not animator.pixmap().isNull()
    animator.set_state("running-right")
    assert animator.index == 0
    assert animator.elapsed == 0


def test_short_sheet_animator_falls_back_to_idle(pet_asset):
    animator = Animator(replace(pet_asset, rows=1))
    animator.set_state("running-left")
    assert animator.track("running-left") == animator.track("idle")
    assert not animator.pixmap().isNull()
