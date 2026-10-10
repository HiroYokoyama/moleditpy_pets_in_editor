from PyQt6.QtWidgets import QWidget

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
            "Pets in Editor/Select Pet",
            "Pets in Editor/Import Pet",
            "Pets in Editor/Toggle Pet Visibility",
            "Pets in Editor/Size",
            "Pets in Editor/Speed",
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
