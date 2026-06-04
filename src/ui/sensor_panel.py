"""Sensor panel sidebar widget for displaying QZFM status."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QScrollArea,
    QGroupBox
)

from src.hardware.sensor_manager import SensorInfo
from src.ui.styles import (
    SENSOR_ONLINE,
    SENSOR_WARMING,
    SENSOR_OFFLINE,
    SENSOR_ERROR,
    LED_OFF,
    BG_CARD,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    FONT_MONO
)

class SensorCard(QFrame):
    """A small card displaying the status of a single sensor."""
    
    def __init__(self, sensor_id: str, parent=None):
        super().__init__(parent)
        self.sensor_id = sensor_id
        self.setProperty("class", "sensor-card")
        self._setup_ui()
        
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(4)
        
        # Header: Name and Status LED
        header = QHBoxLayout()
        header.setSpacing(6)
        
        self.lbl_name = QLabel(self.sensor_id)
        self.lbl_name.setStyleSheet("font-weight: bold;")
        header.addWidget(self.lbl_name)
        
        header.addStretch()
        
        self.lbl_led = QLabel()
        self.lbl_led.setProperty("class", "sensor-led")
        self.lbl_led.setFixedSize(10, 10)
        header.addWidget(self.lbl_led)
        
        layout.addLayout(header)
        
        # Readouts: Field / Temp
        readouts = QHBoxLayout()
        self.lbl_field = QLabel("B0: --- pT")
        self.lbl_field.setStyleSheet(f"font-family: {FONT_MONO}; font-size: 10px; color: {TEXT_SECONDARY};")
        readouts.addWidget(self.lbl_field)
        
        readouts.addStretch()
        
        self.lbl_temp = QLabel("Err: ---")
        self.lbl_temp.setStyleSheet(f"font-family: {FONT_MONO}; font-size: 10px; color: {TEXT_SECONDARY};")
        readouts.addWidget(self.lbl_temp)
        
        layout.addLayout(readouts)
        
    def update_info(self, info: SensorInfo):
        self.lbl_name.setText(info.name)
        
        if not info.connected:
            self._set_led(SENSOR_OFFLINE)
            self.lbl_field.setText("B0: --- pT")
            self.lbl_temp.setText("Err: ---")
            return
            
        if info.cell_temp_locked and info.laser_locked:
            self._set_led(SENSOR_ONLINE)
        elif info.laser_on:
            self._set_led(SENSOR_WARMING)
        else:
            self._set_led(SENSOR_ERROR)
            
        self.lbl_field.setText(f"B0: {info.b0_field:.1f}pT")
        self.lbl_temp.setText(f"Err: {info.cell_temp_error:.3f}")
        
    def _set_led(self, color: str):
        self.lbl_led.setStyleSheet(f"background-color: {color}; border-radius: 5px;")


class SensorPanel(QGroupBox):
    """Sidebar panel to summarize sensor statuses.
    
    Signals
    -------
    manage_clicked
        User requested to open the full sensor management dialog.
    """
    
    manage_clicked = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__("QZFM SENSORS", parent)
        self._cards: dict[str, SensorCard] = {}
        self._setup_ui()
        
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)
        
        # Header button
        header_layout = QHBoxLayout()
        header_layout.addStretch()
        
        self.btn_manage = QPushButton("MANAGE SENSORS")
        self.btn_manage.setToolTip("Open Sensor Manager and Calibration Wizard")
        self.btn_manage.setFixedHeight(22)
        self.btn_manage.setStyleSheet("font-size: 10px; padding: 2px 8px; font-weight: bold;")
        self.btn_manage.clicked.connect(self.manage_clicked.emit)
        header_layout.addWidget(self.btn_manage)
        
        layout.addLayout(header_layout)
        
        # Scroll area for cards
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setStyleSheet("background: transparent;")
        
        self.cards_container = QWidget()
        self.cards_container.setStyleSheet("background: transparent;")
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.cards_layout.setSpacing(4)
        self.cards_layout.addStretch()
        
        self.scroll_area.setWidget(self.cards_container)
        
        # Make the scroll area adapt to its content, without a fixed large gap
        self.scroll_area.setMinimumHeight(0)
        self.scroll_area.setMaximumHeight(200)
        
        layout.addWidget(self.scroll_area)
        
    def update_sensor(self, info: SensorInfo):
        """Update or create a card for the sensor."""
        if info.sensor_id not in self._cards:
            card = SensorCard(info.sensor_id)
            # Insert before the stretch
            self.cards_layout.insertWidget(self.cards_layout.count() - 1, card)
            self._cards[info.sensor_id] = card
            
        self._cards[info.sensor_id].update_info(info)
        
    def remove_sensor(self, sensor_id: str):
        if sensor_id in self._cards:
            card = self._cards.pop(sensor_id)
            self.cards_layout.removeWidget(card)
            card.deleteLater()
            
    def clear(self):
        for card in self._cards.values():
            self.cards_layout.removeWidget(card)
            card.deleteLater()
        self._cards.clear()
