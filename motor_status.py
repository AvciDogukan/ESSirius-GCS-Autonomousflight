import sys
import math
import random
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from pymavlink import mavutil

class MavlinkListener(QThread):
    pwm_update = pyqtSignal(dict)  # {'motor_1': {'pwm':...}, ...}

    def __init__(self, connection_str='udpin:localhost:14541', parent=None):
        super().__init__(parent)
        self.connection_str = connection_str
        self.running = True

    def run(self):
        try:
            # 14541'de dinle
            master = mavutil.mavlink_connection(self.connection_str)
            master.wait_heartbeat()
            print("MAVLink bağlantısı kuruldu")
            while self.running:
                msg = master.recv_match(type='SERVO_OUTPUT_RAW', blocking=True, timeout=1)
                if msg:
                    motor_data = {}
                    # Servo1-4 -> motor_1-4
                    for i in range(1, 5):
                        pwm = getattr(msg, f'servo{i}_raw', 0)
                        motor_data[f'motor_{i}'] = {'pwm': pwm}
                    self.pwm_update.emit(motor_data)
        except Exception as e:
            print(f"MavlinkListener Hatası: {e}")

    def stop(self):
        self.running = False

class MotorStatusWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.motor_data = {
            f'motor_{i}': {'tilt': 0, 'pwm': 1500, 'rpm': 0, 'temp': 25} for i in range(1, 5)
        }
        # 14541 portunda dinle
        self.mavlink_thread = MavlinkListener('udpin:localhost:14541')
        self.mavlink_thread.pwm_update.connect(self.on_pwm_update)
        self.mavlink_thread.start()
        # random RPM/Tilt/Temp için timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_random_params)
        self.timer.start(300)

    def initUI(self):
        main_layout = QVBoxLayout()
        title = QLabel("MOTOR DURUMU")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("""
            QLabel {
                font-size: 24px;
                font-weight: bold;
                color: #2c3e50;
                padding: 10px;
                background-color: #ecf0f1;
                border-radius: 5px;
                margin-bottom: 10px;
            }
        """)
        main_layout.addWidget(title)
        self.drone_widget = DroneVisualization()
        main_layout.addWidget(self.drone_widget)
        details_layout = QHBoxLayout()
        for i in range(1, 5):
            motor_frame = self.create_motor_detail_frame(i)
            details_layout.addWidget(motor_frame)
        main_layout.addLayout(details_layout)
        status_layout = QHBoxLayout()
        self.overall_status = QLabel("Genel Durum: ✅ Normal")
        self.overall_status.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #27ae60;
                padding: 10px;
                background-color: #d5f4e6;
                border-radius: 5px;
                border: 2px solid #27ae60;
            }
        """)
        status_layout.addWidget(self.overall_status)
        main_layout.addLayout(status_layout)
        self.setLayout(main_layout)

    def create_motor_detail_frame(self, motor_num):
        frame = QFrame()
        frame.setFrameStyle(QFrame.Box)
        frame.setStyleSheet("""
            QFrame {
                border: 2px solid #3498db;
                border-radius: 10px;
                background-color: #f8f9fa;
                margin: 5px;
            }
        """)
        layout = QVBoxLayout()
        motor_title = QLabel(f"Motor {motor_num}")
        motor_title.setAlignment(Qt.AlignCenter)
        motor_title.setStyleSheet("""
            QLabel {
                font-size: 14px;
                font-weight: bold;
                padding: 5px;
                background-color: #3498db;
                color: white;
                border-radius: 3px;
            }
        """)
        layout.addWidget(motor_title)
        tilt_label = QLabel("Tilt Açısı:")
        tilt_label.setStyleSheet("font-weight: bold; color: #34495e;")
        layout.addWidget(tilt_label)
        tilt_value = QLabel("0°")
        tilt_value.setObjectName(f"tilt_{motor_num}")
        tilt_value.setStyleSheet("font-size: 16px; color: #e74c3c; font-weight: bold;")
        layout.addWidget(tilt_value)
        pwm_label = QLabel("PWM Değeri:")
        pwm_label.setStyleSheet("font-weight: bold; color: #34495e;")
        layout.addWidget(pwm_label)
        pwm_value = QLabel("1500")
        pwm_value.setObjectName(f"pwm_{motor_num}")
        pwm_value.setStyleSheet("font-size: 16px; color: #3498db; font-weight: bold;")
        layout.addWidget(pwm_value)
        rpm_label = QLabel("RPM:")
        rpm_label.setStyleSheet("font-weight: bold; color: #34495e;")
        layout.addWidget(rpm_label)
        rpm_value = QLabel("0")
        rpm_value.setObjectName(f"rpm_{motor_num}")
        rpm_value.setStyleSheet("font-size: 16px; color: #f39c12; font-weight: bold;")
        layout.addWidget(rpm_value)
        temp_label = QLabel("Sıcaklık:")
        temp_label.setStyleSheet("font-weight: bold; color: #34495e;")
        layout.addWidget(temp_label)
        temp_value = QLabel("25°C")
        temp_value.setObjectName(f"temp_{motor_num}")
        temp_value.setStyleSheet("font-size: 16px; color: #27ae60; font-weight: bold;")
        layout.addWidget(temp_value)
        frame.setLayout(layout)
        return frame

    def on_pwm_update(self, data):
        for key in data:
            self.motor_data[key]['pwm'] = data[key]['pwm']
        self.update_motor_display()
        self.drone_widget.update_motors(self.motor_data)

    def update_random_params(self):
        for i in range(1, 5):
            key = f'motor_{i}'
            self.motor_data[key]['tilt'] = random.randint(-30, 30)
            self.motor_data[key]['rpm'] = random.randint(0, 8000)
            self.motor_data[key]['temp'] = random.randint(20, 60)
        self.update_motor_display()
        self.drone_widget.update_motors(self.motor_data)

    def update_motor_display(self):
        for i in range(1, 5):
            data = self.motor_data[f'motor_{i}']
            tilt_widget = self.findChild(QLabel, f"tilt_{i}")
            if tilt_widget:
                tilt_widget.setText(f"{data['tilt']}°")
            pwm_widget = self.findChild(QLabel, f"pwm_{i}")
            if pwm_widget:
                pwm_widget.setText(str(data['pwm']))
            rpm_widget = self.findChild(QLabel, f"rpm_{i}")
            if rpm_widget:
                rpm_widget.setText(str(data['rpm']))
            temp_widget = self.findChild(QLabel, f"temp_{i}")
            if temp_widget:
                temp_widget.setText(f"{data['temp']}°C")
                if data['temp'] > 50:
                    temp_widget.setStyleSheet("font-size: 16px; color: #e74c3c; font-weight: bold;")
                elif data['temp'] > 40:
                    temp_widget.setStyleSheet("font-size: 16px; color: #f39c12; font-weight: bold;")
                else:
                    temp_widget.setStyleSheet("font-size: 16px; color: #27ae60; font-weight: bold;")

    def closeEvent(self, event):
        self.mavlink_thread.stop()
        self.mavlink_thread.wait()
        event.accept()

class DroneVisualization(QWidget):
    def __init__(self):
        super().__init__()
        self.setMinimumSize(400, 300)
        self.motor_data = {}
    def update_motors(self, motor_data):
        self.motor_data = motor_data
        self.update()
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        center_x = self.width() // 2
        center_y = self.height() // 2
        painter.setBrush(QBrush(QColor(52, 73, 94)))
        painter.setPen(QPen(QColor(44, 62, 80), 2))
        painter.drawEllipse(center_x - 30, center_y - 30, 60, 60)
        motor_positions = [
            (center_x - 80, center_y - 80),  # Motor 1 (sol üst)
            (center_x + 80, center_y - 80),  # Motor 2 (sağ üst)
            (center_x + 80, center_y + 80),  # Motor 3 (sağ alt)
            (center_x - 80, center_y + 80)   # Motor 4 (sol alt)
        ]
        painter.setPen(QPen(QColor(149, 165, 166), 4))
        for mx, my in motor_positions:
            painter.drawLine(center_x, center_y, mx, my)
        for i, (mx, my) in enumerate(motor_positions):
            motor_key = f'motor_{i+1}'
            if motor_key in self.motor_data:
                data = self.motor_data[motor_key]
                if data['temp'] > 50:
                    color = QColor(231, 76, 60)
                elif data['temp'] > 40:
                    color = QColor(243, 156, 18)
                else:
                    color = QColor(39, 174, 96)
                size = 15 + (data['pwm'] - 1000) * 0.01
                painter.setBrush(QBrush(color))
                painter.setPen(QPen(QColor(0, 0, 0), 2))
                painter.drawEllipse(mx - size//2, my - size//2, size, size)
                painter.setPen(QPen(QColor(255, 255, 255), 2))
                painter.drawText(mx - 5, my + 5, str(i+1))
                if abs(data['tilt']) > 5:
                    painter.setPen(QPen(QColor(231, 76, 60), 3))
                    tilt_length = 20
                    angle_rad = math.radians(data['tilt'])
                    end_x = mx + tilt_length * math.cos(angle_rad)
                    end_y = my + tilt_length * math.sin(angle_rad)
                    painter.drawLine(mx, my, end_x, end_y)
            else:
                painter.setBrush(QBrush(QColor(189, 195, 199)))
                painter.setPen(QPen(QColor(0, 0, 0), 2))
                painter.drawEllipse(mx - 10, my - 10, 20, 20)
                painter.setPen(QPen(QColor(255, 255, 255), 2))
                painter.drawText(mx - 5, my + 5, str(i+1))

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MotorStatusWidget()
    window.show()
    sys.exit(app.exec_())

