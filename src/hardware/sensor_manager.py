"""Manager for multiple QZFM sensors."""

from __future__ import annotations
import logging
from dataclasses import dataclass, field
from PyQt6.QtCore import QSettings
from serial.tools import list_ports
import serial

try:
    from QZFM import QZFM
except ImportError:
    QZFM = None  # Will be handled gracefully

logger = logging.getLogger(__name__)

@dataclass
class SensorInfo:
    """Immutable snapshot of sensor state."""
    sensor_id: str
    port: str
    name: str
    is_master: bool = False
    gain: float = 2.7  # V/nT
    
    # State fields
    connected: bool = False
    laser_on: bool = False
    cell_temp_locked: bool = False
    laser_locked: bool = False
    field_zeroed: bool = False
    is_calibrated: bool = False
    
    # Measurements
    cell_temp_error: float = 0.0
    bz_field: float = 0.0
    by_field: float = 0.0
    b0_field: float = 0.0
    
    # Message log
    messages: list[tuple[str, float]] = field(default_factory=list)

class SensorManager:
    """Manages multiple QZFM instances."""
    
    def __init__(self):
        self._sensors: dict[str, QZFM] = {}
        self._configs: dict[str, dict] = {}  # id -> {port, name, master, gain}
        
    def add_sensor(self, sensor_id: str, port: str, name: str = "", is_master: bool = False, gain: float = 2.7) -> None:
        if not name:
            name = f"Sensor {len(self._configs) + 1}"
            
        self._configs[sensor_id] = {
            "port": port,
            "name": name,
            "is_master": is_master,
            "gain": gain,
        }
        logger.info(f"Added sensor config: {sensor_id} ({name}) on port {port}")
        
    def remove_sensor(self, sensor_id: str) -> None:
        if sensor_id in self._sensors:
            self.disconnect_sensor(sensor_id)
        if sensor_id in self._configs:
            del self._configs[sensor_id]
            logger.info(f"Removed sensor config: {sensor_id}")
            
    def get_configs(self) -> dict[str, dict]:
        return self._configs
        
    def get_sensor(self, sensor_id: str) -> QZFM | None:
        return self._sensors.get(sensor_id)
        
    def connect_sensor(self, sensor_id: str) -> None:
        if QZFM is None:
            raise ImportError("QZFM library is not installed.")
            
        if sensor_id not in self._configs:
            raise ValueError(f"Unknown sensor: {sensor_id}")
            
        if sensor_id in self._sensors:
            return  # Already connected
            
        config = self._configs[sensor_id]
        port = config["port"]
        
        logger.info(f"Connecting to sensor {sensor_id} on port {port}...")
        try:
            # Create without device_name to avoid auto-connect
            sensor = QZFM(device_name=None)
            sensor.ser = serial.Serial(port, **sensor.serial_settings)
            sensor.set_master(config["is_master"])
            
            self._sensors[sensor_id] = sensor
            logger.info(f"Connected to {sensor_id}")
        except Exception as e:
            logger.error(f"Failed to connect {sensor_id}: {e}")
            raise
            
    def disconnect_sensor(self, sensor_id: str) -> None:
        if sensor_id in self._sensors:
            try:
                self._sensors[sensor_id].disconnect()
            except Exception as e:
                logger.error(f"Error disconnecting {sensor_id}: {e}")
            finally:
                del self._sensors[sensor_id]
                logger.info(f"Disconnected {sensor_id}")
                
    def disconnect_all(self) -> None:
        for sensor_id in list(self._sensors.keys()):
            self.disconnect_sensor(sensor_id)
            
    def get_info(self, sensor_id: str) -> SensorInfo:
        if sensor_id not in self._configs:
            raise ValueError(f"Unknown sensor: {sensor_id}")
            
        config = self._configs[sensor_id]
        sensor = self._sensors.get(sensor_id)
        
        info = SensorInfo(
            sensor_id=sensor_id,
            port=config["port"],
            name=config["name"],
            is_master=config["is_master"],
            gain=config["gain"]
        )
        
        if sensor is not None:
            info.connected = True
            try:
                info.laser_on = sensor.led.get('laser on (LED1)', False)
                info.cell_temp_locked = sensor.led.get('cell temp lock (LED2)', False)
                info.laser_locked = sensor.led.get('laser lock (LED3)', False)
                info.field_zeroed = sensor.led.get('field zeroed (LED4)', False)
                info.is_calibrated = sensor.is_calibrated
                
                info.cell_temp_error = sensor.sensor_par.get('cell temp error', 0.0)
                info.bz_field = sensor.sensor_par.get('Bz field (pT)', 0.0)
                info.by_field = sensor.sensor_par.get('By field (pT)', 0.0)
                info.b0_field = sensor.sensor_par.get('B0 field (pT)', 0.0)
                
                info.messages = list(sensor.messages)
            except Exception as e:
                logger.debug(f"Error reading sensor info for {sensor_id}: {e}")
                
        return info

    def get_all_info(self) -> dict[str, SensorInfo]:
        return {s_id: self.get_info(s_id) for s_id in self._configs}
        
    @staticmethod
    def list_available_ports() -> list[str]:
        return [port.device for port in list_ports.comports()]
        
    def save_config(self, settings: QSettings) -> None:
        settings.beginGroup("sensors")
        settings.setValue("count", len(self._configs))
        for i, (s_id, config) in enumerate(self._configs.items()):
            settings.beginGroup(f"sensor_{i}")
            settings.setValue("id", s_id)
            settings.setValue("port", config["port"])
            settings.setValue("name", config["name"])
            settings.setValue("is_master", config["is_master"])
            settings.setValue("gain", config["gain"])
            settings.endGroup()
        settings.endGroup()
        
    def load_config(self, settings: QSettings) -> None:
        self.disconnect_all()
        self._configs.clear()
        
        settings.beginGroup("sensors")
        count = int(settings.value("count", 0))
        for i in range(count):
            settings.beginGroup(f"sensor_{i}")
            s_id = str(settings.value("id", f"s{i}"))
            port = str(settings.value("port", ""))
            name = str(settings.value("name", f"Sensor {i+1}"))
            
            is_master = settings.value("is_master", False, type=bool)
            
            gain_val = settings.value("gain", 2.7)
            gain = float(gain_val) if gain_val else 2.7
                
            if port:
                self.add_sensor(s_id, port, name, is_master, gain)
            settings.endGroup()
        settings.endGroup()
