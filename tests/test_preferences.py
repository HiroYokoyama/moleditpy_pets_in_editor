from dataclasses import replace

from PyQt6.QtWidgets import QDialogButtonBox

from pets_in_editor.preferences import PreferencesDialog
from pets_in_editor.settings import DEFAULTS


def test_preferences_restore_selection_and_do_not_mutate_settings(qapp, pet_asset):
    other = replace(pet_asset, identifier="other", name="Other")
    values = {**DEFAULTS, "selected": "other", "enabled": False}
    dialog = PreferencesDialog(None, [pet_asset, other], values)
    try:
        assert dialog.pet_choice.currentData() == "other"
        assert dialog.values() == values
        assert not dialog.preview.pixmap().isNull()
        dialog.show()
        assert dialog.timer.isActive()
        dialog.pet_choice.setCurrentIndex(0)
        dialog.scale.setValue(1.25)
        dialog.speed.setValue(0)
        dialog.enabled.setChecked(True)
        assert dialog.values() == {
            "selected": "sample",
            "enabled": True,
            "scale": 1.25,
            "speed": 0,
        }
        dialog.reject()
        assert values == {**DEFAULTS, "selected": "other", "enabled": False}
        assert not dialog.timer.isActive()
    finally:
        dialog.close()


def test_preferences_disable_save_for_unreadable_sprite(qapp, pet_asset, tmp_path):
    pet = replace(pet_asset, atlas=tmp_path / "missing.png")
    dialog = PreferencesDialog(None, [pet], DEFAULTS.copy())
    try:
        assert not dialog.buttons.button(QDialogButtonBox.StandardButton.Save).isEnabled()
        assert "Unable to decode" in dialog.preview.text()
    finally:
        dialog.close()
