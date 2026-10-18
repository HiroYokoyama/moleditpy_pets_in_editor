"""Sprite extraction and animation timing."""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtGui import QPixmap


@dataclass(frozen=True)
class Track:
    frames: tuple[int, ...]
    durations_ms: tuple[int, ...]


def _row(columns: int, row: int, count: int, duration: int, final: int) -> Track:
    count = min(count, columns)
    frames = tuple(row * columns + column for column in range(count))
    durations = tuple(final if column == count - 1 else duration for column in range(count))
    return Track(frames, durations)


def default_tracks(pet) -> dict[str, Track]:
    """Codex-compatible default rows for the standard 8x9/8x11 sheets."""
    columns = pet.columns

    # Current Codex defaults:
    # row 0 idle
    # row 1 running/move right
    # row 2 running/move left
    # row 3 waving
    # row 4 jumping
    # row 5 failed
    # row 6 waiting
    # row 7 generic running/activity
    # row 8 review
    tracks = {
        "idle": Track(
            tuple(range(min(6, columns))),
            (1680, 660, 660, 840, 840, 1920)[: min(6, columns)],
        ),
        "running-right": _row(columns, 1, 8, 120, 220),
        "running-left": _row(columns, 2, 8, 120, 220),
        "waving": _row(columns, 3, 4, 140, 280),
        "jumping": _row(columns, 4, 5, 140, 280),
        "failed": _row(columns, 5, 8, 140, 240),
        "waiting": _row(columns, 6, 6, 150, 260),
        "running": _row(columns, 7, 6, 120, 220),
        "review": _row(columns, 8, 6, 150, 280),
    }
    return {
        name: track
        for name, track in tracks.items()
        if track.frames and all(frame < pet.frame_count for frame in track.frames)
    }


def _manifest_track(pet, state: str) -> Track | None:
    animations = pet.manifest.get("animations")
    if not isinstance(animations, dict):
        return None
    spec = animations.get(state)
    if not isinstance(spec, dict):
        return None
    frames = spec.get("frames")
    if not isinstance(frames, list) or not frames:
        return None

    clean = tuple(
        value
        for value in frames
        if isinstance(value, int) and not isinstance(value, bool) and 0 <= value < pet.frame_count
    )
    if not clean:
        return None

    fps = spec.get("fps", 8)
    try:
        fps = max(0.1, min(60.0, float(fps)))
    except (TypeError, ValueError):
        fps = 8.0
    duration = max(1, round(1000.0 / fps))
    return Track(clean, tuple(duration for _ in clean))


class Animator:
    def __init__(self, pet):
        self.pet = pet
        self.sheet = QPixmap(str(pet.atlas))
        if self.sheet.isNull():
            raise ValueError("Unable to decode sprite sheet; check Qt image support")

        self._defaults = default_tracks(pet)
        self._tracks = {
            state: _manifest_track(pet, state) or track for state, track in self._defaults.items()
        }
        for state in pet.manifest.get("animations", {}) or {}:
            custom = _manifest_track(pet, state)
            if custom is not None:
                self._tracks[state] = custom
        self._frames = {}
        self.state = "idle"
        self.index = 0
        self.elapsed = 0

    def track(self, state: str) -> Track:
        return self._tracks.get(state, self._tracks["idle"])

    def set_state(self, state: str):
        if state != self.state:
            self.state = state
            self.index = 0
            self.elapsed = 0

    def advance(self, milliseconds: int):
        track = self.track(self.state)
        if not track.frames:
            return

        self.elapsed += max(0, int(milliseconds))
        self.elapsed %= sum(track.durations_ms)
        while self.elapsed >= track.durations_ms[self.index]:
            self.elapsed -= track.durations_ms[self.index]
            self.index = (self.index + 1) % len(track.frames)

    def pixmap(self):
        track = self.track(self.state)
        frame = track.frames[self.index % len(track.frames)]
        column = frame % self.pet.columns
        row = frame // self.pet.columns
        if frame not in self._frames:
            self._frames[frame] = self.sheet.copy(
                column * self.pet.frame_width,
                row * self.pet.frame_height,
                self.pet.frame_width,
                self.pet.frame_height,
            )
        return self._frames[frame]
