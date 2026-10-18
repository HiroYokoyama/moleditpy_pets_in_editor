from dataclasses import replace

from PySide6.QtWidgets import QDialogButtonBox

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
        dialog.activity_level.setCurrentIndex(dialog.activity_level.findData("energetic"))
        assert dialog.values() == {
            "selected": "sample",
            "enabled": True,
            "scale": 1.25,
            "speed": 0,
            "activity_level": "energetic",
        }
        dialog.reject()
        assert values == {**DEFAULTS, "selected": "other", "enabled": False}
        assert not dialog.timer.isActive()
    finally:
        dialog.close()


def test_preferences_reset_to_defaults(qapp, pet_asset):
    values = {
        "selected": "sample",
        "enabled": False,
        "scale": 1.75,
        "speed": 200,
        "activity_level": "energetic",
    }
    dialog = PreferencesDialog(None, [pet_asset], values)
    try:
        assert dialog.enabled.isChecked() is False
        assert dialog.scale.value() == 1.75
        assert dialog.speed.value() == 200
        assert dialog.activity_level.currentData() == "energetic"

        reset_btn = dialog.buttons.button(QDialogButtonBox.StandardButton.RestoreDefaults)
        assert reset_btn is not None
        assert reset_btn.text() == "Reset"
        reset_btn.click()

        assert dialog.enabled.isChecked() == DEFAULTS["enabled"]
        assert dialog.scale.value() == DEFAULTS["scale"]
        assert dialog.speed.value() == DEFAULTS["speed"]
        assert dialog.activity_level.currentData() == DEFAULTS["activity_level"]
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
