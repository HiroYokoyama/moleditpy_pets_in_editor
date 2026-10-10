"""Build the installable MoleditPy plugin ZIP from the repository."""

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "pets_in_editor"
VERSION = "0.1.0"
OUTPUT = ROOT / f"pets_in_editor-{VERSION}.zip"

with ZipFile(OUTPUT, "w", ZIP_DEFLATED) as archive:
    for path in sorted(PACKAGE.rglob("*")):
        if path.is_file() and "__pycache__" not in path.parts:
            archive.write(path, Path("pets_in_editor") / path.relative_to(PACKAGE))

print(OUTPUT)
