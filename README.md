# Pets in Editor for MoleditPy

**Author:** HiroYokoyama  
**Supported MoleditPy:** 4.x

A MoleditPy 4.x plugin that displays a Codex-compatible animated pet across the
whole application window. The overlay is transparent to mouse input and does
not modify molecular data.

## Features

- Whole-application Qt overlay.
- All commands live under `Plugins → Pets in Editor → …`.
- Pet visibility is controlled by `Toggle Pet Visibility`; no toolbar button is added.
- The overlay is registered with MoleditPy's window registry, so `Reload All Plugins` does not duplicate pets.
- Codex `pet.json` packages.
- PNG and WebP sprite sheets.
- Standard 1536x1872 (8x9, 192x208 cells) layout.
- `spriteVersionNumber: 2` 1536x2288 (8x11) layout.
- Optional manifest `frame` and `animations` data.
- Directional movement uses the standard right/left movement rows.
- Pet packages are imported to `~/.moleditpy/pets/`.
- No Codex installation or pre-existing pet directory is required.
- Settings are stored in `pets_in_editor/settings.json` inside the plugin directory.

## Repository layout

```text
moleditpy_pets_in_editor/
├── .github/workflows/
├── pets_in_editor/
│   ├── __init__.py
│   ├── animation.py
│   ├── overlay.py
│   ├── pet_loader.py
│   └── settings.py
├── scripts/
├── tests/
├── LICENSE
├── README.md
├── SECURITY.md
├── CONTRIBUTING.md
├── .gitignore
└── ruff.toml
```

## Install in MoleditPy

Build an installable ZIP:

```bash
python scripts/build_plugin_zip.py
```

Then install `pets_in_editor-0.1.0.zip` with MoleditPy's Plugin Manager, or copy
the `pets_in_editor` folder to:

- Windows: `%USERPROFILE%\.moleditpy\plugins\pets_in_editor\`
- Linux/macOS: `~/.moleditpy/plugins/pets_in_editor/`

Restart MoleditPy, or use the application's plugin reload function.

## Import a Codex pet package

Use **Plugins → Pets in Editor → Import Pet** and select either:

- `pet.json` with its sprite sheet beside it, or
- a ZIP containing one `pet.json` and the referenced sprite sheet.

Imported assets are copied to:

```text
~/.moleditpy/pets/<id>/
```

The plugin does not search another application's pet directory.

## Codex default state rows

For standard sheets the plugin follows the current Codex row mapping:

| Row | State |
|---:|---|
| 0 | idle |
| 1 | running / move right |
| 2 | running / move left |
| 3 | waving |
| 4 | jumping |
| 5 | failed |
| 6 | waiting |
| 7 | running/activity |
| 8 | review |

For v2 sheets, rows 9-10 are retained and accepted but this plugin does not yet
drive look-direction poses.

## Tests

```bash
python -m pip install pytest PyQt6
QT_QPA_PLATFORM=offscreen python -m pytest tests -v
```

On Windows PowerShell:

```powershell
$env:QT_QPA_PLATFORM="offscreen"
python -m pytest tests -v
```

The repository includes loader, validation, animation-row, settings, and
MoleditPy entry-point tests.

## Compatibility note

The overlay is implemented as a transparent Qt tool window associated with the
MoleditPy main window. This is intended to remain visible above native
OpenGL/VTK child surfaces. Window-manager behavior can differ on Linux/Wayland,
so runtime testing in the target desktop environment is recommended.

## License

GPL-3.0.
