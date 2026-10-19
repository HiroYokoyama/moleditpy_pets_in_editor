"""Pets in Editor — MoleditPy 4.x plugin entry point."""

import logging
from functools import wraps
from pathlib import Path

from PySide6.QtWidgets import QDialog, QFileDialog, QMessageBox

from .overlay import PetOverlay
from .pet_loader import discover, install
from .preferences import PreferencesDialog
from .settings import load, save

PLUGIN_NAME = "Pets in Editor"
PLUGIN_VERSION = "0.4.0"
PLUGIN_AUTHOR = "HiroYokoyama"
PLUGIN_DESCRIPTION = "Whole-application animated Codex-compatible pet overlay."
PLUGIN_CATEGORY = "Utility"
PLUGIN_SUPPORTED_MOLEDITPY_VERSION = ">=5.0.0, <6.0.0"
PLUGIN_TAGS = ["Utility"]
PLUGIN_DEPENDENCIES = []
PLUGIN_OPTIONAL_DEPENDENCIES = []

__version__ = PLUGIN_VERSION
__author__ = PLUGIN_AUTHOR

_controller = None
logger = logging.getLogger(__name__)


def ui_action(method):
    """Report failures at the Qt callback boundary so the editor stays usable."""

    @wraps(method)
    def guarded(self, *args, **kwargs):
        try:
            return method(self, *args, **kwargs)
        except Exception as exc:
            logger.exception("Pets in Editor action failed: %s", method.__name__)
            QMessageBox.warning(self.window, PLUGIN_NAME, str(exc))
            return None

    return guarded


class Controller:
    """Owns the overlay and menu actions for one MoleditPy session."""

    def __init__(self, context):
        self.context = context
        self.window = context.get_main_window()
        self.settings = load()
        self.overlay = None

        context.add_plugin_menu("Pets in Editor/Toggle Pet Visibility", self.toggle)
        context.add_plugin_menu("Pets in Editor/Import Pet", self.import_pet)
        context.add_plugin_menu("Pets in Editor/Settings", self.preferences)

        self._start_safely()

    @ui_action
    def _start_safely(self):
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
        # overlay after the replacement is ready.
        if not self.settings["enabled"]:
            self.stop()
            return

        pets = discover()
        chosen = next(
            (pet for pet in pets if pet.identifier == self.settings["selected"]),
            None,
        )
        if chosen is None and pets:
            chosen = pets[0]

        if chosen is None:
            self.stop()
            return

        values = {**self.settings, "selected": chosen.identifier}
        overlay = PetOverlay(self.window, chosen, self.settings, self.context)
        try:
            if values != self.settings:
                save(values)
        except OSError:
            overlay.close()
            overlay.deleteLater()
            raise
        self.stop()
        self.settings.update(values)
        self.overlay = overlay
        self.context.register_window("pet_overlay", self.overlay)

    def _apply_settings(self, values):
        # Save first: a failed write must leave the active preferences unchanged.
        previous = self.settings.copy()
        save(values)
        same_pet = values["selected"] == self.settings["selected"]
        self.settings.update(values)
        if same_pet and values["enabled"] and self.overlay is not None:
            self.overlay._sync_geometry()
            self.overlay.update()
        else:
            try:
                self.start()
            except (OSError, ValueError, RuntimeError):
                self.settings.update(previous)
                save(previous)
                raise

    def stop(self):
        overlays = []

        registered = self._registered_overlay()
        if registered is not None:
            overlays.append(registered)

        if self.overlay is not None and all(self.overlay is not item for item in overlays):
            overlays.append(self.overlay)

        for overlay in overlays:
            try:
                overlay.close()
                overlay.deleteLater()
            except RuntimeError:
                # Qt object may already have been deleted by the host.
                pass

        self.overlay = None

    @ui_action
    def toggle(self):
        self._apply_settings({**self.settings, "enabled": not self.settings["enabled"]})

    @ui_action
    def import_pet(self):
        path, _ = QFileDialog.getOpenFileName(
            self.window,
            "Import Codex pet package",
            str(Path.home()),
            "Pet packages (pet.json *.zip);;JSON files (*.json);;ZIP files (*.zip)",
        )
        if not path:
            return

        pet = install(path)
        self._apply_settings({**self.settings, "selected": pet.identifier, "enabled": True})

    @ui_action
    def preferences(self):
        pets = discover()
        if not pets:
            QMessageBox.information(
                self.window, PLUGIN_NAME, "Import a pet first to configure its appearance."
            )
            return
        dialog = PreferencesDialog(self.window, pets, self.settings)
        try:
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self._apply_settings(dialog.values())
        finally:
            dialog.deleteLater()


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
