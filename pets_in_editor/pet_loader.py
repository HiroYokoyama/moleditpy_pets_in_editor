"""Codex-compatible pet package loading, discovery, and safe installation."""

from __future__ import annotations

import json
import logging
import re
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from zipfile import ZipFile

from PyQt6.QtGui import QImageReader

ROOT = Path.home() / ".moleditpy" / "pets"

IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")
MAX_FILE_SIZE = 40 * 1024 * 1024
MAX_IMAGE_PIXELS = 16 * 1024 * 1024
logger = logging.getLogger(__name__)

DEFAULT_FRAME = {
    1: {"width": 192, "height": 208, "columns": 8, "rows": 9},
    2: {"width": 192, "height": 208, "columns": 8, "rows": 11},
}


@dataclass(frozen=True)
class Pet:
    identifier: str
    name: str
    description: str
    atlas: Path
    manifest: dict
    folder: Path
    frame_width: int
    frame_height: int
    columns: int
    rows: int

    @property
    def frame_count(self) -> int:
        return self.columns * self.rows


def _manifest_path(folder: Path) -> Path:
    path = folder / "pet.json"
    if not path.is_file():
        raise ValueError("Missing pet.json")
    if path.stat().st_size > MAX_FILE_SIZE:
        raise ValueError("pet.json is too large")
    return path


def _load_manifest(folder: Path) -> dict:
    try:
        manifest = json.loads(_manifest_path(folder).read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid pet.json: {exc}") from exc
    if not isinstance(manifest, dict):
        raise TypeError("pet.json must contain a JSON object")
    return manifest


def _resolve_atlas(folder: Path, manifest: dict) -> Path:
    value = manifest.get("spritesheetPath", "spritesheet.webp")
    if not isinstance(value, str) or not value.strip():
        raise ValueError("spritesheetPath must be a non-empty string")

    relative = Path(value)
    if relative.is_absolute() or ".." in relative.parts or len(relative.parts) != 1:
        raise ValueError("Sprite sheet must be a file inside the pet directory")

    atlas = (folder / relative).resolve()
    if atlas.parent != folder.resolve():
        raise ValueError("Sprite sheet must stay inside the pet directory")
    if atlas.suffix.lower() not in {".png", ".webp"} or not atlas.is_file():
        raise ValueError("Missing PNG/WebP sprite sheet")
    if atlas.stat().st_size > MAX_FILE_SIZE:
        raise ValueError("Sprite sheet is too large")
    return atlas


def _frame_spec(manifest: dict) -> tuple[int, int, int, int]:
    version = manifest.get("spriteVersionNumber", 1)
    if version not in (1, 2):
        raise ValueError("spriteVersionNumber must be 1 or 2")

    default = DEFAULT_FRAME[version]
    custom = manifest.get("frame")
    if custom is None:
        frame = default
    elif isinstance(custom, dict):
        frame = {**default, **custom}
    else:
        raise ValueError("frame must be an object when provided")

    dimensions = tuple(frame[key] for key in ("width", "height", "columns", "rows"))
    if any(not isinstance(value, int) or isinstance(value, bool) for value in dimensions):
        raise ValueError("Frame dimensions and grid counts must be integers")
    width, height, columns, rows = dimensions

    if min(width, height, columns, rows) <= 0:
        raise ValueError("Frame dimensions and grid counts must be positive")
    if columns * rows > 512:
        raise ValueError("Frame count exceeds supported maximum")
    return width, height, columns, rows


def _validate_image(atlas: Path, frame: tuple[int, int, int, int]) -> None:
    reader = QImageReader(str(atlas))
    size = reader.size()
    # Release Qt's file handle before raising: Windows must be able to clean up staging.
    reader.setFileName("")
    if not size.isValid():
        raise ValueError("Unable to read sprite sheet image")
    if size.width() * size.height() > MAX_IMAGE_PIXELS:
        raise ValueError("Sprite sheet exceeds the supported image size")

    width, height, columns, rows = frame
    expected_width = width * columns
    expected_height = height * rows
    if (size.width(), size.height()) != (expected_width, expected_height):
        raise ValueError(
            f"Expected {expected_width}x{expected_height} sprite sheet, "
            f"got {size.width()}x{size.height()}"
        )


def _validate_animations(manifest: dict, frame_count: int) -> None:
    animations = manifest.get("animations")
    if animations is None:
        return
    if not isinstance(animations, dict):
        raise TypeError("animations must be an object")

    for name, spec in animations.items():
        if not isinstance(name, str) or not isinstance(spec, dict):
            raise TypeError("Each animation must be an object")
        frames = spec.get("frames")
        if frames is None:
            continue
        if not isinstance(frames, list) or not frames:
            raise ValueError(f"Animation {name!r} must contain at least one frame")
        for index in frames:
            if not isinstance(index, int) or isinstance(index, bool):
                raise TypeError(f"Animation {name!r} contains a non-integer frame")
            if not 0 <= index < frame_count:
                raise ValueError(
                    f"Animation {name!r} references frame {index}, "
                    f"but the sheet contains {frame_count} frames"
                )
        fps = spec.get("fps", 8)
        try:
            fps = float(fps)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Animation {name!r} has invalid fps") from exc
        if not 0 < fps <= 60:
            raise ValueError(f"Animation {name!r} fps must be between 0 and 60")


def read_pet(folder) -> Pet:
    folder = Path(folder).resolve()
    manifest = _load_manifest(folder)

    identifier = manifest.get("id") or folder.name
    if not isinstance(identifier, str) or not IDENTIFIER.fullmatch(identifier):
        raise ValueError("Invalid pet identifier")

    atlas = _resolve_atlas(folder, manifest)
    frame = _frame_spec(manifest)
    _validate_image(atlas, frame)
    _validate_animations(manifest, frame[2] * frame[3])

    name = manifest.get("displayName") or identifier
    if not isinstance(name, str):
        name = identifier
    description = manifest.get("description", "")
    if not isinstance(description, str):
        description = ""

    return Pet(
        identifier=identifier,
        name=name,
        description=description,
        atlas=atlas,
        manifest=manifest,
        folder=folder,
        frame_width=frame[0],
        frame_height=frame[1],
        columns=frame[2],
        rows=frame[3],
    )


def discover() -> list[Pet]:
    ROOT.mkdir(parents=True, exist_ok=True)
    result = []
    for folder in sorted(ROOT.iterdir(), key=lambda p: p.name.lower()):
        if folder.name.startswith(".") or not folder.is_dir():
            continue
        try:
            result.append(read_pet(folder))
        except (ValueError, TypeError, OSError):
            logger.exception("Skipping invalid pet package: %s", folder)
            continue
    return result


def _copy_directory_package(source: Path, staging: Path) -> None:
    manifest = _load_manifest(source.resolve())
    atlas = _resolve_atlas(source.resolve(), manifest)

    shutil.copy2(source / "pet.json", staging / "pet.json")
    shutil.copy2(atlas, staging / atlas.name)


def _extract_zip_package(source: Path, staging: Path) -> None:
    with ZipFile(source) as archive:
        manifests = [
            info
            for info in archive.infolist()
            if not info.is_dir()
            and (info.filename == "pet.json" or info.filename.endswith("/pet.json"))
        ]
        if len(manifests) != 1:
            raise ValueError("ZIP must contain exactly one pet.json")

        manifest_info = manifests[0]
        if manifest_info.file_size > MAX_FILE_SIZE:
            raise ValueError("pet.json is too large")

        try:
            manifest = json.loads(archive.read(manifest_info).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("Invalid pet.json in ZIP") from exc
        if not isinstance(manifest, dict):
            raise TypeError("pet.json in ZIP must contain an object")

        sheet_name = manifest.get("spritesheetPath", "spritesheet.webp")
        if (
            not isinstance(sheet_name, str)
            or not sheet_name
            or Path(sheet_name).is_absolute()
            or ".." in Path(sheet_name).parts
            or len(Path(sheet_name).parts) != 1
        ):
            raise ValueError("Invalid spritesheetPath in ZIP")

        prefix = manifest_info.filename[: -len("pet.json")]
        expected_member = prefix + sheet_name
        members = {info.filename: info for info in archive.infolist()}
        sheet_info = members.get(expected_member)
        if sheet_info is None or sheet_info.is_dir():
            raise ValueError("ZIP is missing the sprite sheet")
        if sheet_info.file_size > MAX_FILE_SIZE:
            raise ValueError("Sprite sheet is too large")

        (staging / "pet.json").write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        (staging / sheet_name).write_bytes(archive.read(sheet_info))


def _copy_json_package(source: Path, staging: Path) -> None:
    if source.name.lower() != "pet.json":
        raise ValueError("Choose pet.json, a pet directory, or a ZIP archive")

    manifest = _load_manifest(source.parent)
    atlas = _resolve_atlas(source.parent.resolve(), manifest)

    shutil.copy2(source, staging / "pet.json")
    shutil.copy2(atlas, staging / atlas.name)


def install(source) -> Pet:
    """Import a package into ~/.moleditpy/pets without overwriting existing data."""
    source = Path(source)
    ROOT.mkdir(parents=True, exist_ok=True)

    # Stage on the destination filesystem so a rename publishes the complete package.
    with tempfile.TemporaryDirectory(prefix=".import-", dir=ROOT) as tmp:
        staging = Path(tmp).resolve()

        if source.is_dir():
            _copy_directory_package(source.resolve(), staging)
        elif source.suffix.lower() == ".zip":
            _extract_zip_package(source, staging)
        elif source.is_file():
            _copy_json_package(source.resolve(), staging)
        else:
            raise ValueError("Pet package does not exist")

        manifest = _load_manifest(staging)
        if not manifest.get("id"):
            manifest["id"] = (
                source.name
                if source.is_dir()
                else source.stem
                if source.suffix.lower() == ".zip"
                else source.parent.name
            )
            (staging / "pet.json").write_text(
                json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
            )
        pet = read_pet(staging)
        destination = ROOT / pet.identifier
        if destination.exists():
            raise FileExistsError(f"Pet already installed: {pet.identifier}")

        staging.rename(destination)
        return read_pet(destination)
