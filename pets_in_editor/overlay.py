"""Whole-application transparent overlay window for the animated pet."""

from __future__ import annotations

import logging
import random

from PyQt6.QtCore import QElapsedTimer, QEvent, QPoint, QRect, Qt, QTimer, pyqtSlot
from PyQt6.QtGui import QCursor, QPainter
from PyQt6.QtWidgets import QStatusBar, QWidget

from .animation import Animator


class PetOverlay(QWidget):
    """Transparent tool window that follows the MoleditPy main window."""

    def __init__(self, parent_window, pet, settings, context=None):
        animator = Animator(pet)
        flags = (
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowDoesNotAcceptFocus
            | Qt.WindowType.WindowTransparentForInput
        )
        super().__init__(parent_window, flags)

        self.parent_window = parent_window
        self.context = context
        self.animator = animator
        self.settings = settings
        self.xpos = 30.0
        self.direction = 1
        self.roam_elapsed = 0
        self._closed = False
        self.clock = QElapsedTimer()
        self.reaction = None
        self.reaction_remaining = 0
        self.status_bar = parent_window.findChild(QStatusBar)
        if self.status_bar is not None:
            self.status_bar.messageChanged.connect(self._on_status_message)

        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self.timer = QTimer(self)
        self.timer.setInterval(50)
        self.timer.timeout.connect(self.step)
        parent_window.installEventFilter(self)
        self._sync_geometry()

    def _sync_geometry(self):
        if self._closed:
            return
        if self.parent_window.isMinimized() or not self.parent_window.isVisible():
            self.hide()
            return

        top_left = self.parent_window.mapToGlobal(QPoint(0, 0))
        self.setGeometry(
            top_left.x(),
            top_left.y(),
            self.parent_window.width(),
            self.parent_window.height(),
        )
        self.xpos = min(max(0.0, self.xpos), max(0, self.width() - self._pet_size()[0]))
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
        milliseconds = min(250, max(0, self.clock.restart()))
        self.reaction_remaining = max(0, self.reaction_remaining - milliseconds)
        self.roam_elapsed += milliseconds
        pet_width, _ = self._pet_size()
        usable_width = max(0, self.width() - pet_width)

        if self.roam_elapsed >= 5000:
            self.roam_elapsed %= 5000
            self.direction = random.choice((-1, 0, 1))

        speed = float(self.settings["speed"])
        activity = self._activity_state()
        if activity is None:
            self.xpos += self.direction * speed * milliseconds / 1000
        if self.xpos <= 0:
            self.xpos = 0
            self.direction = 1
        elif self.xpos >= usable_width:
            self.xpos = usable_width
            self.direction = -1

        if activity is not None:
            state = activity
        elif speed == 0 or usable_width == 0:
            state = "idle"
        elif self.direction > 0:
            state = "running-right"
        elif self.direction < 0:
            state = "running-left"
        else:
            state = "idle"

        self.animator.set_state(state)
        self.animator.advance(milliseconds)
        self.update()

    def _is_mouse_over_pet(self):
        if self._closed or not self.isVisible() or not self.parent_window.isVisible():
            return False
        try:
            cursor_pos = self.mapFromGlobal(QCursor.pos())
            return self._pet_rect().contains(cursor_pos)
        except (RuntimeError, AttributeError):
            return False

    def _activity_state(self):
        # Keep the host implementation dependency at this one read-only boundary.
        compute = getattr(self.parent_window, "compute_manager", None)
        if getattr(compute, "active_worker_ids", ()):
            return "waiting"
        if self.context is not None and getattr(self.context, "is_dragging_atom", False):
            return "review"
        if self._is_mouse_over_pet():
            return "jumping"
        if self.reaction_remaining:
            return self.reaction
        return None

    @pyqtSlot(str)
    def _on_status_message(self, message):
        # Exact messages emitted by ComputeManager/CalculationWorker. Ignore
        # unrelated status updates and stale worker messages.
        if message.startswith("Calculation Error:"):
            self.reaction = "failed"
        elif message.startswith("Process completed ("):
            self.reaction = "waving"
        elif message == "Halted":
            self.reaction = "idle"
        else:
            return
        self.reaction_remaining = 3500

    def _pet_size(self):
        pet = self.animator.pet
        scale = min(
            float(self.settings["scale"]),
            max(1, self.width()) / pet.frame_width,
            max(1, self.height() - 8) / pet.frame_height,
        )
        return max(1, int(pet.frame_width * scale)), max(1, int(pet.frame_height * scale))

    def _pet_rect(self):
        width, height = self._pet_size()
        return QRect(
            int(min(max(0, self.xpos), max(0, self.width() - width))),
            max(0, self.height() - height - 8),
            width,
            height,
        )

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        frame = self.animator.pixmap()
        target = self._pet_rect()
        painter.drawPixmap(target, frame)
        painter.end()

    def showEvent(self, event):
        self.clock.start()
        self.timer.start()
        super().showEvent(event)

    def hideEvent(self, event):
        self.timer.stop()
        super().hideEvent(event)

    def closeEvent(self, event):
        if self._closed:
            super().closeEvent(event)
            return
        self._closed = True
        self.timer.stop()
        try:
            self.parent_window.removeEventFilter(self)
            if self.status_bar is not None:
                self.status_bar.messageChanged.disconnect(self._on_status_message)
        except RuntimeError:
            logging.getLogger(__name__).debug("Overlay parent was already deleted", exc_info=True)
        super().closeEvent(event)
