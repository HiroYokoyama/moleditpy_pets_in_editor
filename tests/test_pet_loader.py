import json
from pathlib import Path
from zipfile import ZipFile

import pytest
from PyQt6.QtGui import QImage

from pets_in_editor import pet_loader


def write_sheet(path: Path, width=1536, height=1872):
    image = QImage(width, height, QImage.Format.Format_ARGB32)
    image.fill(0)
    assert image.save(str(path))


def write_package(folder: Path, *, version=1, sheet_name="spritesheet.png"):
    folder.mkdir(parents=True, exist_ok=True)
    manifest = {
        "id": "sample",
        "displayName": "Sample",
        "description": "Test asset",
        "spritesheetPath": sheet_name,
    }
    if version == 2:
        manifest["spriteVersionNumber"] = 2
    (folder / "pet.json").write_text(json.dumps(manifest), encoding="utf-8")
    write_sheet(folder / sheet_name, 1536, 2288 if version == 2 else 1872)


def test_read_v1_package(tmp_path):
    write_package(tmp_path)
    pet = pet_loader.read_pet(tmp_path)
    assert pet.identifier == "sample"
    assert pet.frame_width == 192
    assert pet.frame_height == 208
    assert pet.columns == 8
    assert pet.rows == 9
    assert pet.frame_count == 72


def test_read_v2_package(tmp_path):
    write_package(tmp_path, version=2)
    pet = pet_loader.read_pet(tmp_path)
    assert pet.rows == 11
    assert pet.frame_count == 88


def test_reject_wrong_dimensions(tmp_path):
    write_package(tmp_path)
    write_sheet(tmp_path / "spritesheet.png", 100, 100)
    with pytest.raises(ValueError, match="Expected 1536x1872"):
        pet_loader.read_pet(tmp_path)


def test_reject_path_escape(tmp_path):
    write_package(tmp_path)
    manifest = json.loads((tmp_path / "pet.json").read_text())
    manifest["spritesheetPath"] = "../outside.png"
    (tmp_path / "pet.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="inside the pet directory"):
        pet_loader.read_pet(tmp_path)


def test_discover_uses_moleditpy_root(tmp_path, monkeypatch):
    root = tmp_path / ".moleditpy" / "pets"
    write_package(root / "one")
    monkeypatch.setattr(pet_loader, "ROOT", root)
    pets = pet_loader.discover()
    assert [pet.identifier for pet in pets] == ["sample"]


def test_install_directory(tmp_path, monkeypatch):
    source = tmp_path / "source"
    write_package(source, sheet_name="asset.png")
    destination_root = tmp_path / ".moleditpy" / "pets"
    monkeypatch.setattr(pet_loader, "ROOT", destination_root)

    pet = pet_loader.install(source)
    assert pet.folder == (destination_root / "sample").resolve()
    assert (pet.folder / "pet.json").is_file()
    assert (pet.folder / "asset.png").is_file()


def test_install_zip_with_custom_sheet_name(tmp_path, monkeypatch):
    source = tmp_path / "source"
    write_package(source, sheet_name="asset.png")
    archive = tmp_path / "package.zip"
    with ZipFile(archive, "w") as zf:
        zf.write(source / "pet.json", "bundle/pet.json")
        zf.write(source / "asset.png", "bundle/asset.png")

    destination_root = tmp_path / ".moleditpy" / "pets"
    monkeypatch.setattr(pet_loader, "ROOT", destination_root)

    pet = pet_loader.install(archive)
    assert pet.atlas.name == "asset.png"


def test_reject_invalid_animation_frame(tmp_path):
    write_package(tmp_path)
    manifest = json.loads((tmp_path / "pet.json").read_text())
    manifest["animations"] = {"idle": {"frames": [999], "fps": 8}}
    (tmp_path / "pet.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="references frame"):
        pet_loader.read_pet(tmp_path)


def test_duplicate_import_preserves_existing_pet(tmp_path, monkeypatch):
    source = tmp_path / "source"
    write_package(source)
    root = tmp_path / "pets"
    monkeypatch.setattr(pet_loader, "ROOT", root)
    pet = pet_loader.install(source)
    original = pet.atlas.read_bytes()
    with pytest.raises(FileExistsError, match="already installed"):
        pet_loader.install(source)
    assert pet.atlas.read_bytes() == original
    assert [folder.name for folder in root.iterdir()] == ["sample"]


def test_failed_import_leaves_no_partial_package(tmp_path, monkeypatch):
    source = tmp_path / "source"
    write_package(source)
    write_sheet(source / "spritesheet.png", 100, 100)
    root = tmp_path / "pets"
    monkeypatch.setattr(pet_loader, "ROOT", root)
    with pytest.raises(ValueError, match="Expected"):
        pet_loader.install(source)
    assert list(root.iterdir()) == []


def test_import_without_identifier_uses_source_folder(tmp_path, monkeypatch):
    source = tmp_path / "mochi"
    write_package(source)
    manifest = json.loads((source / "pet.json").read_text())
    del manifest["id"]
    (source / "pet.json").write_text(json.dumps(manifest))
    monkeypatch.setattr(pet_loader, "ROOT", tmp_path / "pets")
    pet = pet_loader.install(source / "pet.json")
    assert pet.identifier == "mochi"
    assert pet_loader.read_pet(pet.folder).identifier == "mochi"


def test_discovery_skips_staging_and_logs_invalid_packages(tmp_path, monkeypatch, caplog):
    root = tmp_path / "pets"
    write_package(root / "good")
    write_package(root / ".import-staged")
    broken = root / "broken"
    broken.mkdir()
    (broken / "pet.json").write_text("[]")
    monkeypatch.setattr(pet_loader, "ROOT", root)
    assert [pet.identifier for pet in pet_loader.discover()] == ["sample"]
    assert "Skipping invalid pet package" in caplog.text


@pytest.mark.parametrize("value", [True, 1.5, "8"])
def test_frame_grid_requires_integers(value):
    with pytest.raises(ValueError, match="must be integers"):
        pet_loader._frame_spec({"frame": {"columns": value}})
