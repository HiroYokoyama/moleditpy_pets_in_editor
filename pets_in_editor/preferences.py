"""Pet preferences with an animated preview and explicit save/cancel actions."""

import logging

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QLabel,
    QSpinBox,
    QVBoxLayout,
)

from .animation import Animator


class PreferencesDialog(QDialog):
    def __init__(self, parent, pets, settings):
        super().__init__(parent)
        self.setWindowTitle("Pets in Editor Settings")
        self.setMinimumWidth(360)
        self.pets = pets
        self.animator = None
        self.preview_error = None

        self.pet_choice = QComboBox()
        for pet in pets:
            self.pet_choice.addItem(f"{pet.name} ({pet.identifier})", pet.identifier)
        current = self.pet_choice.findData(settings["selected"])
        self.pet_choice.setCurrentIndex(max(0, current))
        self.enabled = QCheckBox("Show pet in the editor")
        self.enabled.setChecked(settings["enabled"])
        self.scale = QDoubleSpinBox()
        self.scale.setRange(0.2, 2.0)
        self.scale.setSingleStep(0.05)
        self.scale.setDecimals(2)
        self.scale.setSuffix(" ×")
        self.scale.setValue(settings["scale"])
        self.speed = QSpinBox()
        self.speed.setRange(0, 400)
        self.speed.setSuffix(" px/s")
        self.speed.setValue(settings["speed"])
        self.speed.setToolTip("Set to 0 for a stationary pet with an idle animation.")

        self.preview = QLabel()
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview.setFixedHeight(180)
        self.description = QLabel()
        self.description.setTextFormat(Qt.TextFormat.PlainText)
        self.description.setWordWrap(True)
        self.description.setMaximumWidth(440)
        form = QFormLayout()
        form.addRow("Pet:", self.pet_choice)
        form.addRow("Visibility:", self.enabled)
        form.addRow("Size:", self.scale)
        form.addRow("Movement speed:", self.speed)
        layout = QVBoxLayout(self)
        layout.addWidget(self.preview)
        layout.addWidget(self.description)
        layout.addLayout(form)
        hint = QLabel("Changes take effect when you save. Pets fit inside the editor window.")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

        self.timer = QTimer(self)
        self.timer.setInterval(50)
        self.timer.timeout.connect(self._advance)
        self.pet_choice.currentIndexChanged.connect(self._select_pet)
        self.scale.valueChanged.connect(self._render)
        self._select_pet()

    def _select_pet(self):
        pet = self.pets[self.pet_choice.currentIndex()]
        self.animator = None
        self.preview_error = None
        try:
            self.animator = Animator(pet)
        except ValueError as exc:
            logging.getLogger(__name__).exception("Unable to preview pet %s", pet.identifier)
            self.preview_error = str(exc)
        self.buttons.button(QDialogButtonBox.StandardButton.Save).setEnabled(
            self.animator is not None
        )
        self.description.setText(pet.description or "No description provided.")
        self._render()

    def _render(self):
        if self.animator is None:
            self.preview.setText(self.preview_error or "No preview available.")
            return
        frame = self.animator.pixmap()
        self.preview.setPixmap(
            frame.scaled(
                min(400, max(1, int(self.animator.pet.frame_width * self.scale.value()))),
                min(180, max(1, int(self.animator.pet.frame_height * self.scale.value()))),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

    def _advance(self):
        if self.animator is not None:
            self.animator.advance(self.timer.interval())
            self._render()

    def values(self):
        return {
            "selected": self.pet_choice.currentData(),
            "enabled": self.enabled.isChecked(),
            "scale": self.scale.value(),
            "speed": self.speed.value(),
        }

    def showEvent(self, event):
        self.timer.start()
        super().showEvent(event)

    def hideEvent(self, event):
        self.timer.stop()
        super().hideEvent(event)
