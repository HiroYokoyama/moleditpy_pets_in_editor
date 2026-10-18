from types import SimpleNamespace

import pytest
from PySide6.QtWidgets import QWidget

import pets_in_editor


class FakeContext:
    def __init__(self, window):
        self.window = window
        self.actions = []
        self.windows = {}

    def get_main_window(self):
        return self.window

    def add_plugin_menu(self, path, callback):
        self.actions.append((path, callback))

    def register_window(self, window_id, window):
        self.windows[window_id] = window

    def get_window(self, window_id):
        window = self.windows.get(window_id)
        if window is None:
            return None
        try:
            # Touch a QObject method so deleted Qt wrappers behave like the host.
            window.objectName()
        except RuntimeError:
            self.windows.pop(window_id, None)
            return None
        return window


def test_initialize_registers_nested_plugin_menu_without_installed_pets(
    qapp, tmp_path, monkeypatch
):
    from pets_in_editor import pet_loader, settings

    monkeypatch.setattr(pet_loader, "ROOT", tmp_path / "pets")
    monkeypatch.setattr(settings, "PATH", tmp_path / "settings.json")

    window = QWidget()
    context = FakeContext(window)

    controller = pets_in_editor.initialize(context)
    try:
        assert controller.window is window
        assert [path for path, _ in context.actions] == [
            "Pets in Editor/Toggle Pet Visibility",
            "Pets in Editor/Import Pet",
            "Pets in Editor/Settings",
        ]
        assert controller.overlay is None
    finally:
        pets_in_editor.shutdown(context)
        window.close()


def test_registered_overlay_is_retired_even_after_global_controller_is_lost(
    qapp, tmp_path, monkeypatch
):
    from pets_in_editor import pet_loader, settings

    monkeypatch.setattr(pet_loader, "ROOT", tmp_path / "pets")
    monkeypatch.setattr(settings, "PATH", tmp_path / "settings.json")

    window = QWidget()
    context = FakeContext(window)

    stale = QWidget(window)
    stale.show()
    context.register_window("pet_overlay", stale)

    # Simulate what happens to module globals after a hot reload.
    pets_in_editor._controller = None
    pets_in_editor.shutdown(context)

    assert not stale.isVisible()
    stale.deleteLater()
    window.close()


def test_failed_settings_write_preserves_active_values(qapp, monkeypatch, caplog):
    from pets_in_editor.settings import DEFAULTS

    monkeypatch.setattr(pets_in_editor, "load", lambda: DEFAULTS.copy())
    monkeypatch.setattr(pets_in_editor.Controller, "start", lambda self: None)
    window = QWidget()
    controller = pets_in_editor.Controller(FakeContext(window))
    messages = []
    monkeypatch.setattr(
        pets_in_editor.QMessageBox, "warning", lambda *args: messages.append(args[-1])
    )

    def fail_save(values):
        raise PermissionError("Settings file is read-only")

    monkeypatch.setattr(pets_in_editor, "save", fail_save)
    try:
        controller.toggle()
        assert controller.settings == DEFAULTS
        assert messages == ["Settings file is read-only"]
        assert "action failed: toggle" in caplog.text
    finally:
        window.close()


def test_size_and_speed_updates_preserve_overlay(qapp, monkeypatch):
    from pets_in_editor.settings import DEFAULTS

    monkeypatch.setattr(pets_in_editor, "load", lambda: DEFAULTS.copy())
    monkeypatch.setattr(pets_in_editor.Controller, "start", lambda self: None)
    monkeypatch.setattr(pets_in_editor, "save", lambda values: None)
    window = QWidget()
    controller = pets_in_editor.Controller(FakeContext(window))
    updated = []
    overlay = SimpleNamespace(
        _sync_geometry=lambda: updated.append("geometry"),
        update=lambda: updated.append("paint"),
    )
    controller.overlay = overlay
    try:
        controller._apply_settings({**controller.settings, "speed": 0, "scale": 1.25})
        assert controller.overlay is overlay
        assert controller.settings["speed"] == 0
        assert controller.settings["scale"] == 1.25
        assert updated == ["geometry", "paint"]
    finally:
        window.close()


def test_failed_pet_restart_restores_previous_settings(qapp, monkeypatch):
    from pets_in_editor.settings import DEFAULTS

    monkeypatch.setattr(pets_in_editor, "load", lambda: DEFAULTS.copy())
    monkeypatch.setattr(pets_in_editor.Controller, "start", lambda self: None)
    window = QWidget()
    controller = pets_in_editor.Controller(FakeContext(window))
    saved = []
    monkeypatch.setattr(pets_in_editor, "save", lambda values: saved.append(values.copy()))

    def fail_start():
        raise ValueError("Unable to decode sprite")

    monkeypatch.setattr(controller, "start", fail_start)
    try:
        with pytest.raises(ValueError, match="Unable to decode"):
            controller._apply_settings({**DEFAULTS, "selected": "broken"})
        assert controller.settings == DEFAULTS
        assert saved[-1] == DEFAULTS
    finally:
        window.close()
