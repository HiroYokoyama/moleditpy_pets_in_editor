# Pets in Editor for MoleditPy

[![Tests](https://github.com/HiroYokoyama/moleditpy_pets_in_editor/actions/workflows/tests.yml/badge.svg)](https://github.com/HiroYokoyama/moleditpy_pets_in_editor/actions/workflows/tests.yml)
[![MoleditPy](https://img.shields.io/badge/MoleditPy->=4.0.0-3577F7)](https://github.com/HiroYokoyama/python_molecular_editor)
[![GitHub tag](https://img.shields.io/github/v/tag/HiroYokoyama/moleditpy_pets_in_editor?label=version)](https://github.com/HiroYokoyama/moleditpy_pets_in_editor/tags)
[![GitHub Downloads](https://img.shields.io/github/downloads/HiroYokoyama/moleditpy_pets_in_editor/total)](https://github.com/HiroYokoyama/moleditpy_pets_in_editor/releases)

Repo: [https://github.com/HiroYokoyama/moleditpy_pets_in_editor](https://github.com/HiroYokoyama/moleditpy_pets_in_editor)

A MoleditPy 4.x plugin that displays a Codex-compatible animated pet across the
whole application window. The overlay is transparent to mouse input and does
not modify molecular data.

## Features

- Whole-application Qt overlay.
- All commands live under `Plugins → Pets in Editor → …`.
- **Settings** combines pet selection, visibility, size, movement speed, and activity level with an animated preview and a Reset button. Save applies changes; Cancel keeps your current settings.
- Pet visibility is controlled by `Toggle Pet Visibility`; no toolbar button is added.
- The overlay is registered with MoleditPy's window registry, so `Reload All Plugins` does not duplicate pets.
- Codex `pet.json` packages.
- PNG and WebP sprite sheets.
- Standard 1536x1872 (8x9, 192x208 cells) layout.
- `spriteVersionNumber: 2` 1536x2288 (8x11) layout.
- Optional manifest `frame` and `animations` data.
- Directional movement uses the standard right/left movement rows with randomized roaming intervals and activity levels (Lazy, Normal, Energetic).
- Set movement speed to zero for a stationary pet with an idle animation.
- Pets fit inside the editor window and pause while the window is hidden or minimized.
- Size, speed, and activity changes preserve the current pet's position.
- Pets pause their movement and use the waiting animation during built-in 2D-to-3D conversion or optimization, and the review animation while dragging 3D atoms or groups.
- Hovering the mouse over the pet plays its jumping animation on the spot without intercepting mouse clicks or editor interactions.
- Explicit calculation errors show the failed animation, completion messages show a wave, and cancellation shows idle briefly before normal movement resumes.
- Pet packages are imported to `~/.moleditpy/pets/`.
- No Codex installation or pre-existing pet directory is required.
- Settings are stored in `pets_in_editor/settings.json` inside the plugin directory.
- Personal settings are excluded from Git and release ZIPs.

## Version 0.3.0

Adds configurable wandering activity levels (Lazy / Quiet, Normal, Energetic / Active) with randomized roaming intervals and movement vs idle probabilities. Adds a **Reset** button to the Settings dialog to restore default preferences.

## Version 0.2.2

Plays the jumping animation when hovering the mouse over the pet without moving or capturing mouse clicks, preserving full pass-through click interactions with the editor beneath.

## Version 0.2.1

Removes duplicate individual menu actions and input dialogs (`Select Pet`, `Size`, `Speed`) in favor of the unified `Settings` dialog, leaving `Toggle Pet Visibility`, `Import Pet`, and `Settings` in the plugin menu.

## Version 0.2.0

Adds a settings dialog with an animated pet preview, improves movement and small-window behavior,
and reports menu action failures without interrupting the editor. Imports are staged before
publishing a complete pet package; invalid installed packages are logged and skipped. Custom
sheets with fewer animation rows fall back to idle instead of displaying blank frames.

Activity uses the plugin API's `is_dragging_atom` flag and the host compute manager's
`active_worker_ids` collection, read by the existing animation timer. The latter is a host
implementation detail because MoleditPy currently has no public calculation-state API.
Failure, completion, and cancellation reactions listen to Qt's `QStatusBar.messageChanged`
signal and recognize only MoleditPy's explicit `Calculation Error:`, `Process completed (`
and `Halted` messages. These reactions last 3.5 seconds of visible animation time. Unrelated
messages and stale-worker notices are ignored. Active workers take priority over reactions.
This compatibility adapter depends on the host's English message format; independent
calculation plugins and constrained-optimization dialogs are not monitored unless they
emit those same messages. No host methods or worker callbacks are modified.

## Repository layout

```text
moleditpy_pets_in_editor/
├── .github/
├── pets_in_editor/
│   ├── __init__.py
│   ├── animation.py
│   ├── overlay.py
│   ├── pet_loader.py
│   └── settings.py
├── tests/
├── LICENSE
├── README.md
├── SECURITY.md
├── CONTRIBUTING.md
├── CODE_OF_CONDUCT.md
├── .gitignore
└── ruff.toml
```

## Install in MoleditPy

Download `pets_in_editor_<version>.zip` from the
[Releases](https://github.com/HiroYokoyama/moleditpy_pets_in_editor/releases) page and install it with MoleditPy's Plugin Manager, or copy
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
