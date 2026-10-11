from types import SimpleNamespace

import pytest
from PyQt6.QtCore import QPoint, Qt
from PyQt6.QtGui import QCursor
from PyQt6.QtWidgets import QMainWindow, QWidget

from pets_in_editor.overlay import PetOverlay
from pets_in_editor.settings import DEFAULTS


def test_overlay_pauses_when_parent_hidden_and_restarts_when_shown(qapp, pet_asset):
    parent = QWidget()
    overlay = PetOverlay(parent, pet_asset, DEFAULTS.copy())
    try:
        assert not overlay.isVisible()
        assert not overlay.timer.isActive()
        parent.resize(400, 300)
        parent.show()
        qapp.processEvents()
        assert overlay.isVisible()
        assert overlay.timer.isActive()
        parent.hide()
        qapp.processEvents()
        assert not overlay.isVisible()
        assert not overlay.timer.isActive()
        parent.show()
        qapp.processEvents()
        assert overlay.timer.isActive()
        overlay.close()
        overlay._sync_geometry()
        assert not overlay.isVisible()
        assert not overlay.timer.isActive()
    finally:
        overlay.close()
        parent.close()


def test_overlay_fits_small_window_and_clamps_position(qapp, pet_asset):
    parent = QWidget()
    parent.resize(20, 20)
    parent.show()
    overlay = PetOverlay(parent, pet_asset, {**DEFAULTS, "scale": 2.0})
    try:
        overlay.xpos = 999
        overlay._sync_geometry()
        width, height = overlay._pet_size()
        assert width <= 20
        assert height <= 12
        assert 0 <= overlay.xpos <= overlay.width() - width
    finally:
        overlay.close()
        parent.close()


def test_zero_speed_uses_idle_animation(qapp, pet_asset):
    parent = QWidget()
    parent.resize(400, 300)
    parent.show()
    overlay = PetOverlay(parent, pet_asset, {**DEFAULTS, "speed": 0})
    try:
        position = overlay.xpos
        overlay.step()
        assert overlay.xpos == position
        assert overlay.animator.state == "idle"
    finally:
        overlay.close()
        parent.close()


def test_pet_reacts_to_calculation_and_dragging_without_moving(qapp, pet_asset):
    parent = QWidget()
    parent.resize(400, 300)
    parent.show()
    parent.compute_manager = SimpleNamespace(active_worker_ids={1, 2})
    context = SimpleNamespace(is_dragging_atom=True)
    overlay = PetOverlay(parent, pet_asset, DEFAULTS.copy(), context)
    try:
        position = overlay.xpos
        overlay.step()
        assert overlay.animator.state == "waiting"
        assert overlay.xpos == position
        parent.compute_manager.active_worker_ids.remove(1)
        overlay.step()
        assert overlay.animator.state == "waiting"
        parent.compute_manager.active_worker_ids.clear()
        overlay.step()
        assert overlay.animator.state == "review"
        assert overlay.xpos == position
        context.is_dragging_atom = False
        overlay.step()
        assert overlay.animator.state == "running-right"
    finally:
        overlay.close()
        parent.close()


@pytest.mark.parametrize(
    ("message", "state"),
    [
        ("Calculation Error: embedding failed", "failed"),
        ("Process completed (RDKit Conversion / MMFF).", "waving"),
        ("Halted", "idle"),
    ],
)
def test_status_reactions_expire_and_disconnect(qapp, pet_asset, message, state):
    parent = QMainWindow()
    parent.resize(400, 300)
    status_bar = parent.statusBar()
    parent.show()
    overlay = PetOverlay(parent, pet_asset, DEFAULTS.copy())
    try:
        status_bar.showMessage(message)
        overlay.step()
        assert overlay.animator.state == state
        status_bar.showMessage("Unrelated editor message")
        assert overlay.reaction == state
        overlay.reaction_remaining = 0
        overlay.step()
        assert overlay.animator.state == "running-right"
        overlay.close()
        status_bar.showMessage("Calculation Error: another error")
        assert overlay.reaction_remaining == 0
    finally:
        overlay.close()
        parent.close()


def test_stale_messages_do_not_change_activity_and_busy_has_priority(qapp, pet_asset):
    parent = QMainWindow()
    status_bar = parent.statusBar()
    parent.compute_manager = SimpleNamespace(active_worker_ids={1})
    overlay = PetOverlay(parent, pet_asset, DEFAULTS.copy())
    try:
        status_bar.showMessage("Ignored stale worker error: failed (ID = 7)")
        assert overlay.reaction is None
        status_bar.showMessage("Calculation Error: embedding failed")
        assert overlay._activity_state() == "waiting"
        parent.compute_manager.active_worker_ids.clear()
        assert overlay._activity_state() == "failed"
    finally:
        overlay.close()
        parent.close()


def test_pet_jumps_when_hovered_without_moving_and_resumes(qapp, pet_asset):
    parent = QWidget()
    parent.resize(400, 300)
    parent.show()
    overlay = PetOverlay(parent, pet_asset, DEFAULTS.copy())
    try:
        qapp.processEvents()
        pet_rect = overlay._pet_rect()
        global_center = overlay.mapToGlobal(pet_rect.center())
        QCursor.setPos(global_center)
        qapp.processEvents()

        position = overlay.xpos
        overlay.step()
        assert overlay.animator.state == "jumping"
        assert overlay.xpos == position

        # Move mouse away from pet
        QCursor.setPos(overlay.mapToGlobal(QPoint(0, 0)))
        qapp.processEvents()
        overlay.step()
        assert overlay.animator.state == "running-right"
    finally:
        overlay.close()
        parent.close()


def test_overlay_preserves_input_transparency(qapp, pet_asset):
    parent = QWidget()
    overlay = PetOverlay(parent, pet_asset, DEFAULTS.copy())
    try:
        assert overlay.testAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        assert bool(overlay.windowFlags() & Qt.WindowType.WindowTransparentForInput)
    finally:
        overlay.close()


def test_overlay_activity_level_roam_ranges(qapp, pet_asset):
    parent = QWidget()
    for level, min_ms, max_ms in [
        ("lazy", 5000, 10000),
        ("normal", 3500, 7000),
        ("energetic", 1500, 3000),
    ]:
        overlay = PetOverlay(parent, pet_asset, {**DEFAULTS, "activity_level": level})
        try:
            for _ in range(50):
                duration = overlay._next_roam_duration()
                assert min_ms <= duration <= max_ms
                direction = overlay._choose_direction()
                assert direction in (-1, 0, 1)
        finally:
            overlay.close()
    parent.close()


def test_overlay_roam_elapsed_triggers_new_roam(qapp, pet_asset, monkeypatch):
    parent = QWidget()
    overlay = PetOverlay(parent, pet_asset, {**DEFAULTS, "activity_level": "lazy"})
    try:
        overlay.roam_target_ms = 100
        overlay.roam_elapsed = 90
        monkeypatch.setattr(overlay, "_choose_direction", lambda: -1)
        monkeypatch.setattr(overlay, "_next_roam_duration", lambda: 3000)
        # Advance by 20ms so roam_elapsed (110) >= roam_target_ms (100)
        overlay.clock.restart()
        # Mock restart returning 20ms
        monkeypatch.setattr(overlay.clock, "restart", lambda: 20)
        overlay.step()
        assert overlay.direction == -1
        assert overlay.roam_target_ms == 3000
        assert overlay.roam_elapsed == 0
    finally:
        overlay.close()
        parent.close()

