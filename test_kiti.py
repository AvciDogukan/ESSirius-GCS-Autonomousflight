from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QPushButton, QLabel, QTextEdit, QApplication, QGroupBox, QGridLayout)
from PyQt5.QtCore import pyqtSignal, Qt

class FailSafeTestPanel(QWidget):
    # Fail-safe senaryoları için özel sinyaller
    telemetry_lost = pyqtSignal()
    gps_loss = pyqtSignal()
    battery_low = pyqtSignal()
    rc_loss = pyqtSignal()
    imu_fail = pyqtSignal()
    motor_fail = pyqtSignal()
    emergency_shutdown = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Fail-Safe Test Paneli")
        self.setFixedSize(400, 500)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        group = QGroupBox("Fail-Safe Senaryoları")
        grid = QGridLayout()

        self.buttons = {
            "Telemetriyi Kes": (self.telemetry_lost, 0, 0),
            "GPS Sinyalini Kes": (self.gps_loss, 0, 1),
            "Batarya %10": (self.battery_low, 1, 0),
            "RC Sinyalini Kes": (self.rc_loss, 1, 1),
            "IMU Sapması": (self.imu_fail, 2, 0),
            "Motor Arızası": (self.motor_fail, 2, 1),
            "Acil Durdur": (self.emergency_shutdown, 3, 0),
        }

        for label, (signal, row, col) in self.buttons.items():
            btn = QPushButton(label)
            btn.setStyleSheet("padding: 8px; font-weight: bold;")
            btn.clicked.connect(lambda _, s=signal, l=label: self.emit_signal(s, l))
            grid.addWidget(btn, row, col)

        group.setLayout(grid)
        layout.addWidget(group)

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setStyleSheet("background-color: #f0f0f0; font-family: monospace;")
        layout.addWidget(QLabel("Log Çıktısı:"))
        layout.addWidget(self.log_output)

        self.setLayout(layout)

    def emit_signal(self, signal, label):
        signal.emit()
        self.log_output.append(f"✅ Test Tetiklendi: {label}")


if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)
    test_panel = FailSafeTestPanel()
    test_panel.show()
    sys.exit(app.exec_())
