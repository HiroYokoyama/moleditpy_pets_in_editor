"""Pets in Editor — MoleditPy 4.x plugin entry point."""

from pathlib import Path

from PyQt6.QtWidgets import QFileDialog, QInputDialog, QMessageBox

from .overlay import PetOverlay
from .pet_loader import discover, install
from .settings import load, save

PLUGIN_NAME = "Pets in Editor"
PLUGIN_VERSION = "0.1.0"
PLUGIN_AUTHOR = "HiroYokoyama"
PLUGIN_DESCRIPTION = "Whole-application animated Codex-compatible pet overlay."
PLUGIN_CATEGORY = "Utility"
PLUGIN_SUPPORTED_MOLEDITPY_VERSION = "4.*"
PLUGIN_TAGS = ["Utility"]
PLUGIN_DEPENDENCIES = []
PLUGIN_OPTIONAL_DEPENDENCIES = []

__version__ = PLUGIN_VERSION
__author__ = PLUGIN_AUTHOR

_controller = None


class Controller:
    """Owns the overlay and menu actions for one MoleditPy session."""

    def __init__(self, context):
        self.context = context
        self.window = context.get_main_window()
        self.settings = load()
        self.overlay = None

        context.add_plugin_menu("Pets in Editor/Select Pet", self.select_pet)
        context.add_plugin_menu("Pets in Editor/Import Pet", self.import_pet)
        context.add_plugin_menu("Pets in Editor/Toggle Pet Visibility", self.toggle)
        context.add_plugin_menu("Pets in Editor/Size", self.change_size)
        context.add_plugin_menu("Pets in Editor/Speed", self.change_speed)

        self.start()

    def _registered_overlay(self):
        """Return the session-wide overlay registered by MoleditPy, if any."""
        try:
            return self.context.get_window("pet_overlay")
        except (AttributeError, RuntimeError):
            return None

    def start(self):
        # Important for hot reload:
        # module globals are recreated on reload, but PluginContext's namespaced
        # window registry survives. Always retire the previously registered
        # overlay before creating another one.
        self.stop()

        if not self.settings["enabled"]:
            return

        pets = discover()
        chosen = next(
            (pet for pet in pets if pet.identifier == self.settings["selected"]),
            None,
        )
        if chosen is None and pets:
            chosen = pets[0]

        if chosen is None:
            return

        self.settings["selected"] = chosen.identifier
        save(self.settings)

        self.overlay = PetOverlay(self.window, chosen, self.settings)
        self.context.register_window("pet_overlay", self.overlay)

    def stop(self):
        overlays = []

        registered = self._registered_overlay()
        if registered is not None:
            overlays.append(registered)

        if self.overlay is not None and all(
            self.overlay is not item for item in overlays
        ):
            overlays.append(self.overlay)

        for overlay in overlays:
            try:
                overlay.close()
                overlay.deleteLater()
            except RuntimeError:
                # Qt object may already have been deleted by the host.
                pass

        self.overlay = None

    def select_pet(self):
        pets = discover()
        if not pets:
            QMessageBox.information(
                self.window,
                PLUGIN_NAME,
                "No pets are installed. Import a Codex pet package first.",
            )
            return

        labels = [f"{pet.name} ({pet.identifier})" for pet in pets]
        item, ok = QInputDialog.getItem(
            self.window, PLUGIN_NAME, "Select pet:", labels, 0, False
        )
        if not ok:
            return

        self.settings["selected"] = pets[labels.index(item)].identifier
        self.settings["enabled"] = True
        save(self.settings)
        self.start()

    def import_pet(self):
        path, _ = QFileDialog.getOpenFileName(
            self.window,
            "Import Codex pet package",
            str(Path.home()),
            "Pet packages (pet.json *.zip);;JSON files (*.json);;ZIP files (*.zip)",
        )
        if not path:
            return

        try:
            pet = install(path)
        except Exception as exc:
            QMessageBox.warning(self.window, PLUGIN_NAME, str(exc))
            return

        self.settings["selected"] = pet.identifier
        self.settings["enabled"] = True
        save(self.settings)
        self.start()

    def toggle(self):
        self.settings["enabled"] = not self.settings["enabled"]
        save(self.settings)
        self.start()

    def change_size(self):
        value, ok = QInputDialog.getDouble(
            self.window,
            PLUGIN_NAME,
            "Pet scale:",
            float(self.settings["scale"]),
            0.20,
            2.00,
            2,
        )
        if ok:
            self.settings["scale"] = value
            save(self.settings)
            self.start()

    def change_speed(self):
        value, ok = QInputDialog.getInt(
            self.window,
            PLUGIN_NAME,
            "Movement speed (pixels/second):",
            int(self.settings["speed"]),
            0,
            400,
        )
        if ok:
            self.settings["speed"] = value
            save(self.settings)


def initialize(context):
    """MoleditPy V4 plugin entry point."""
    global _controller
    if _controller is not None:
        _controller.stop()
    _controller = Controller(context)
    return _controller


def shutdown(context=None):
    """Release timers/windows when the plugin is reloaded or disabled."""
    global _controller

    if _controller is not None:
        _controller.stop()
        _controller = None
        return

    # A module reload resets globals. The PluginContext registry is the durable
    # source of truth for persistent windows, so clean it up from there too.
    if context is not None:
        try:
            overlay = context.get_window("pet_overlay")
            if overlay is not None:
                overlay.close()
                overlay.deleteLater()
        except (AttributeError, RuntimeError):
            pass
