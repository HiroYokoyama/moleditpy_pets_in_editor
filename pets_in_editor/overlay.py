"""Whole-application transparent overlay window for the animated pet."""

from __future__ import annotations

import random

from PyQt6.QtCore import QEvent, QPoint, QRect, Qt, QTimer
from PyQt6.QtGui import QPainter
from PyQt6.QtWidgets import QWidget

from .animation import Animator


class PetOverlay(QWidget):
    """Transparent tool window that follows the MoleditPy main window."""

    def __init__(self, parent_window, pet, settings):
        flags = (
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowDoesNotAcceptFocus
            | Qt.WindowType.WindowTransparentForInput
        )
        super().__init__(parent_window, flags)

        self.parent_window = parent_window
        self.animator = Animator(pet)
        self.settings = settings
        self.xpos = 30.0
        self.direction = 1
        self.tick_count = 0

        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        parent_window.installEventFilter(self)
        self._sync_geometry()

        self.timer = QTimer(self)
        self.timer.setInterval(50)
        self.timer.timeout.connect(self.step)
        self.timer.start()

        self.show()
        self.raise_()

    def _sync_geometry(self):
        if self.parent_window.isMinimized():
            self.hide()
            return

        top_left = self.parent_window.mapToGlobal(QPoint(0, 0))
        self.setGeometry(
            top_left.x(),
            top_left.y(),
            self.parent_window.width(),
            self.parent_window.height(),
        )
        if self.parent_window.isVisible():
            self.show()
            self.raise_()

    def eventFilter(self, obj, event):
        if obj is self.parent_window and event.type() in {
            QEvent.Type.Move,
            QEvent.Type.Resize,
            QEvent.Type.Show,
            QEvent.Type.WindowStateChange,
        }:
            QTimer.singleShot(0, self._sync_geometry)
        elif obj is self.parent_window and event.type() in {
            QEvent.Type.Hide,
            QEvent.Type.Close,
        }:
            self.hide()
        return False

    def step(self):
        self.tick_count += 1

        scale = float(self.settings["scale"])
        pet_width = max(1, int(self.animator.pet.frame_width * scale))
        usable_width = max(0, self.width() - pet_width)

        if self.tick_count % 100 == 0:
            self.direction = random.choice((-1, 0, 1))

        if self.direction > 0:
            state = "running-right"
        elif self.direction < 0:
            state = "running-left"
        else:
            state = "idle"

        self.animator.set_state(state)
        self.xpos += self.direction * float(self.settings["speed"]) * 0.05

        if self.xpos <= 0:
            self.xpos = 0
            self.direction = 1
        elif self.xpos >= usable_width:
            self.xpos = usable_width
            self.direction = -1

        self.animator.advance(50)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        frame = self.animator.pixmap()
        scale = float(self.settings["scale"])
        width = max(1, int(self.animator.pet.frame_width * scale))
        height = max(1, int(self.animator.pet.frame_height * scale))

        target = QRect(
            int(self.xpos),
            max(0, self.height() - height - 8),
            width,
            height,
        )
        painter.drawPixmap(target, frame)
        painter.end()

    def closeEvent(self, event):
        self.timer.stop()
        try:
            self.parent_window.removeEventFilter(self)
        except RuntimeError:
            pass
        super().closeEvent(event)
