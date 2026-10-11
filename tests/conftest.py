import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PyQt6.QtWidgets import QApplication


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance() or QApplication([])
    return app


@pytest.fixture
def pet_asset(tmp_path, qapp):
    import json

    from PyQt6.QtGui import QColor, QImage

    from pets_in_editor.pet_loader import read_pet

    folder = tmp_path / "pet"
    folder.mkdir()
    manifest = {
        "id": "sample",
        "displayName": "Sample",
        "description": "A sample pet",
        "spritesheetPath": "sheet.png",
        "frame": {"width": 32, "height": 32, "columns": 8, "rows": 9},
    }
    (folder / "pet.json").write_text(json.dumps(manifest), encoding="utf-8")
    image = QImage(256, 288, QImage.Format.Format_ARGB32)
    image.fill(QColor("orange"))
    assert image.save(str(folder / "sheet.png"))
    return read_pet(folder)
