"""Full management dialog for configuring and calibrating QZFM sensors."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QLabel,
    QPushButton,
    QGroupBox,
    QFormLayout,
    QComboBox,
    QWidget,
    QSplitter,
    QInputDialog,
    QMessageBox,
    QLineEdit,
    QCheckBox
)

from src.hardware.sensor_manager import SensorManager, SensorInfo
from src.hardware.sensor_worker import SensorWorker, SensorCommand
from src.ui.calibration_wizard import CalibrationWizard
from src.ui.zeroing_window import ZeroingWindow
from src.ui.styles import (
    BG_DARKEST,
    BG_CARD,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    ACCENT_PRIMARY,
    FONT_MONO
)

class SensorDialog(QDialog):
    """Dialog for full sensor configuration and manual control."""
    
    def __init__(self, manager: SensorManager, worker: SensorWorker, parent=None):
        super().__init__(parent)
        self.manager = manager
        self.worker = worker
        self._zeroing_windows: dict[str, ZeroingWindow] = {}
        
        self.setWindowTitle("QZFM Sensor Management")
        self.setMinimumSize(700, 500)
        self._setup_ui()
        self._connect_signals()
        self._populate_list()
        
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left pane: List of sensors
        left_pane = QWidget()
        left_layout = QVBoxLayout(left_pane)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        self.list_sensors = QListWidget()
        self.list_sensors.currentRowChanged.connect(self._on_sensor_selected)
        left_layout.addWidget(self.list_sensors)
        
        btn_layout = QHBoxLayout()
        self.btn_add = QPushButton("+ Add")
        self.btn_add.clicked.connect(self._on_add_sensor)
        self.btn_remove = QPushButton("- Remove")
        self.btn_remove.clicked.connect(self._on_remove_sensor)
        btn_layout.addWidget(self.btn_add)
        btn_layout.addWidget(self.btn_remove)
        left_layout.addLayout(btn_layout)
        
        splitter.addWidget(left_pane)
        
        # Right pane: Details
        self.right_pane = QWidget()
        right_layout = QVBoxLayout(self.right_pane)
        right_layout.setContentsMargins(10, 0, 0, 0)
        
        # Wizard banner
        wizard_banner = QGroupBox("CALIBRAÇÃO GUIADA")
        wizard_banner.setStyleSheet(f"QGroupBox {{ border-left: 4px solid {ACCENT_PRIMARY}; }}")
        wl = QHBoxLayout(wizard_banner)
        
        lbl_wizard = QLabel("Para usuários iniciantes, utilize o assistente para inicializar e calibrar.")
        lbl_wizard.setWordWrap(True)
        wl.addWidget(lbl_wizard)
        
        self.btn_wizard = QPushButton("INICIAR WIZARD")
        self.btn_wizard.setMinimumHeight(40)
        self.btn_wizard.setStyleSheet("font-weight: bold;")
        self.btn_wizard.clicked.connect(self._on_run_wizard)
        wl.addWidget(self.btn_wizard)
        
        right_layout.addWidget(wizard_banner)
        
        # Details group
        details_group = QGroupBox("DETALHES DO SENSOR")
        form = QFormLayout(details_group)
        
        self.lbl_id = QLabel()
        self.lbl_port = QLabel()
        self.edit_name = QLineEdit()
        self.edit_name.editingFinished.connect(self._on_name_changed)
        
        self.chk_master = QCheckBox("Master")
        self.chk_master.toggled.connect(self._on_master_toggled)
        
        form.addRow("ID:", self.lbl_id)
        form.addRow("Porta:", self.lbl_port)
        form.addRow("Nome:", self.edit_name)
        form.addRow("Sincronização:", self.chk_master)
        
        right_layout.addWidget(details_group)
        
        # Status group
        status_group = QGroupBox("STATUS")
        sf = QFormLayout(status_group)
        
        self.lbl_leds = QLabel()
        self.lbl_b0 = QLabel()
        self.lbl_bz = QLabel()
        self.lbl_temp_err = QLabel()
        
        for lbl in (self.lbl_b0, self.lbl_bz, self.lbl_temp_err):
            lbl.setStyleSheet(f"font-family: {FONT_MONO};")
            
        sf.addRow("LEDs Lock:", self.lbl_leds)
        sf.addRow("B0 Field:", self.lbl_b0)
        sf.addRow("Bz Field:", self.lbl_bz)
        sf.addRow("Temp Error:", self.lbl_temp_err)
        
        right_layout.addWidget(status_group)
        
        # Manual Actions
        actions_group = QGroupBox("CONTROLE MANUAL")
        al = QHBoxLayout(actions_group)
        
        self.btn_connect = QPushButton("Conectar")
        self.btn_connect.clicked.connect(self._on_connect_toggle)
        al.addWidget(self.btn_connect)
        
        self.btn_zero = QPushButton("Field Zero")
        self.btn_zero.clicked.connect(self._on_zero_toggle)
        al.addWidget(self.btn_zero)
        
        self.btn_reset = QPushButton("Reset Field")
        self.btn_reset.clicked.connect(self._on_reset)
        al.addWidget(self.btn_reset)
        
        right_layout.addWidget(actions_group)
        right_layout.addStretch()
        
        splitter.addWidget(self.right_pane)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([200, 500])
        
        layout.addWidget(splitter)
        
        self.btn_close = QPushButton("Fechar")
        self.btn_close.clicked.connect(self.accept)
        layout.addWidget(self.btn_close, alignment=Qt.AlignmentFlag.AlignRight)
        
    def _connect_signals(self):
        self.worker.status_updated.connect(self._on_status_updated)
        self.worker.zeroing_data.connect(self._on_zeroing_data)
        
    def _populate_list(self):
        self.list_sensors.clear()
        configs = self.manager.get_configs()
        for s_id, cfg in configs.items():
            item = QListWidgetItem(f"{cfg['name']} ({cfg['port']})")
            item.setData(Qt.ItemDataRole.UserRole, s_id)
            self.list_sensors.addItem(item)
            
        if self.list_sensors.count() > 0:
            self.list_sensors.setCurrentRow(0)
        else:
            self.right_pane.setEnabled(False)
            
    def _current_sensor_id(self) -> str | None:
        item = self.list_sensors.currentItem()
        if item:
            return item.data(Qt.ItemDataRole.UserRole)
        return None
        
    def _on_sensor_selected(self, row: int):
        s_id = self._current_sensor_id()
        if not s_id:
            self.right_pane.setEnabled(False)
            return
            
        self.right_pane.setEnabled(True)
        info = self.manager.get_info(s_id)
        self._update_details_pane(info)
        
    @pyqtSlot(str, object)
    def _on_status_updated(self, s_id: str, info: SensorInfo):
        # Update list item text
        for i in range(self.list_sensors.count()):
            item = self.list_sensors.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == s_id:
                item.setText(f"{info.name} ({info.port})")
                break
                
        if s_id == self._current_sensor_id():
            self._update_details_pane(info)
            
    def _update_details_pane(self, info: SensorInfo):
        self.lbl_id.setText(info.sensor_id)
        self.lbl_port.setText(info.port)
        
        if self.edit_name.text() != info.name and not self.edit_name.hasFocus():
            self.edit_name.setText(info.name)
            
        self.chk_master.blockSignals(True)
        self.chk_master.setChecked(info.is_master)
        self.chk_master.blockSignals(False)
        
        # Status
        led_text = []
        if info.laser_on: led_text.append("LsrOn")
        if info.cell_temp_locked: led_text.append("TmpLck")
        if info.laser_locked: led_text.append("LsrLck")
        if info.field_zeroed: led_text.append("FldZro")
        
        self.lbl_leds.setText(" | ".join(led_text) if led_text else "None")
        self.lbl_b0.setText(f"{info.b0_field:.2f} pT")
        self.lbl_bz.setText(f"{info.bz_field:.2f} pT")
        self.lbl_temp_err.setText(f"{info.cell_temp_error:.4f}")
        
        # Buttons
        if info.connected:
            self.btn_connect.setText("Desconectar")
            self.btn_zero.setEnabled(True)
            self.btn_reset.setEnabled(True)
            self.btn_wizard.setEnabled(True)
        else:
            self.btn_connect.setText("Conectar")
            self.btn_zero.setEnabled(False)
            self.btn_reset.setEnabled(False)
            self.btn_wizard.setEnabled(False)
            
    # --- Actions ---
    
    def _on_add_sensor(self):
        ports = self.manager.list_available_ports()
        if not ports:
            QMessageBox.warning(self, "Aviso", "Nenhuma porta COM encontrada.")
            return
            
        port, ok = QInputDialog.getItem(self, "Adicionar Sensor", "Selecione a porta:", ports, 0, False)
        if ok and port:
            s_id = f"qzfm_{len(self.manager.get_configs())}"
            self.manager.add_sensor(s_id, port)
            self._populate_list()
            
    def _on_remove_sensor(self):
        s_id = self._current_sensor_id()
        if s_id:
            reply = QMessageBox.question(self, "Confirmar", f"Remover {s_id}?")
            if reply == QMessageBox.StandardButton.Yes:
                self.manager.remove_sensor(s_id)
                self._populate_list()
                
    def _on_name_changed(self):
        s_id = self._current_sensor_id()
        if s_id:
            cfg = self.manager.get_configs()[s_id]
            cfg["name"] = self.edit_name.text()
            self._populate_list()
            
    def _on_master_toggled(self, checked: bool):
        s_id = self._current_sensor_id()
        if s_id:
            if self.manager.get_info(s_id).connected:
                self.worker.queue_command(s_id, SensorCommand.SET_MASTER, is_master=checked)
            else:
                self.manager.get_configs()[s_id]["is_master"] = checked
            
    def _on_connect_toggle(self):
        s_id = self._current_sensor_id()
        if not s_id: return
        
        info = self.manager.get_info(s_id)
        if info.connected:
            self.worker.queue_command(s_id, SensorCommand.DISCONNECT)
        else:
            self.worker.queue_command(s_id, SensorCommand.CONNECT)
            
    def _on_zero_toggle(self):
        s_id = self._current_sensor_id()
        if not s_id: return
        
        # Check if already zeroing
        if s_id in self._zeroing_windows and self._zeroing_windows[s_id].isVisible():
            self.worker.queue_command(s_id, SensorCommand.FIELD_ZERO_STOP)
            self._zeroing_windows[s_id].close()
        else:
            self.worker.queue_command(s_id, SensorCommand.FIELD_ZERO_START, axes_xyz=True)
            info = self.manager.get_info(s_id)
            zw = ZeroingWindow(s_id, info.name, self)
            zw.btn_stop.clicked.connect(lambda: self._stop_zeroing(s_id))
            zw.show()
            self._zeroing_windows[s_id] = zw
            
    def _stop_zeroing(self, s_id: str):
        self.worker.queue_command(s_id, SensorCommand.FIELD_ZERO_STOP)
        if s_id in self._zeroing_windows:
            self._zeroing_windows[s_id].close()
            del self._zeroing_windows[s_id]
            
    def _on_reset(self):
        s_id = self._current_sensor_id()
        if s_id:
            self.worker.queue_command(s_id, SensorCommand.FIELD_RESET)
            
    def _on_run_wizard(self):
        s_id = self._current_sensor_id()
        if not s_id: return
        
        info = self.manager.get_info(s_id)
        wizard = CalibrationWizard(s_id, info.name, self.worker, self)
        wizard.exec()
        
    @pyqtSlot(str, float, float, float, float)
    def _on_zeroing_data(self, s_id: str, bz: float, by: float, b0: float, t_err: float):
        if s_id in self._zeroing_windows and self._zeroing_windows[s_id].isVisible():
            self._zeroing_windows[s_id].update_data(s_id, bz, by, b0, t_err)
