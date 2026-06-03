"""Unit tests for QZFM integration, including MockQZFM and QzfmWorker."""

from __future__ import annotations

import numpy as np
import pytest
from PyQt6.QtCore import QEventLoop

from src.processing.qzfm_worker import MockQZFM, QzfmWorker


def test_mock_qzfm_basic_operations() -> None:
    """Test that MockQZFM connects, starts up, and reads data correctly."""
    mock = MockQZFM("SIMULATOR")
    
    assert mock.device_name == "SIMULATOR"
    assert mock.led["laser on (LED1)"] is True
    assert mock.led["is master"] is True
    
    # Run auto start
    mock.auto_start(zero_calibrate=True)
    assert mock.led["laser lock (LED3)"] is True
    assert mock.led["cell temp lock (LED2)"] is True
    assert mock.led["field zeroed (LED4)"] is True
    assert mock.is_field_zeroed is True
    assert mock.is_calibrated is True
    
    # Read data
    times, fields = mock.read_data(seconds=0.5, axis="z")
    assert len(times) == 100  # 0.5s * 200Hz
    assert len(fields) == 100
    assert not np.isnan(fields).any()
    
    # Field reset
    mock.field_reset()
    assert mock.is_field_zeroed is False
    assert mock.is_calibrated is False
    assert mock.sensor_par["Bz field (pT)"] == 0.0


def test_qzfm_worker_signals(qtbot) -> None:
    """Test QzfmWorker connection and signal emissions using pytest-qt's qtbot."""
    worker = QzfmWorker()
    
    # Track signal emission
    connected_signals = []
    status_signals = []
    
    worker.connected_status.connect(connected_signals.append)
    worker.status_updated.connect(lambda leds, params: status_signals.append((leds, params)))
    
    # Trigger connection
    worker.connect_sensor("SIMULATOR_TEST")
    
    assert worker.is_simulated is True
    assert len(connected_signals) == 1
    assert connected_signals[0] is True
    
    # Run status poll explicitly to verify status emission
    worker._poll_status()
    assert len(status_signals) == 1
    leds, params = status_signals[0]
    assert leds["laser on (LED1)"] is True
    
    # Disconnect
    worker.disconnect_sensor()
    assert len(connected_signals) == 2
    assert connected_signals[1] is False
