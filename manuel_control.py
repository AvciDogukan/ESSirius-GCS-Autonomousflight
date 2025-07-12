from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, 
                            QSlider, QDial, QLabel, QGroupBox, QPushButton, 
                            QProgressBar, QSpinBox, QFrame)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QFont, QPalette, QColor, QIcon

class ControlWidget(QFrame):
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        self.setStyleSheet("""
            QFrame {
                border: 2px solid #2980b9;
                border-radius: 10px;
                background-color: #34495e;
                padding: 10px;
            }
        """)

class ManualControlPage(QWidget):
    def __init__(self, parent=None):
        super(ManualControlPage, self).__init__(parent)
        self.initUI()

    def initUI(self):
        main_layout = QVBoxLayout()
        
        # Stil tanımlamaları
        self.setStyleSheet("""
            QWidget {
                background-color: #2c3e50;
                color: white;
            }
            QGroupBox {
                font-size: 16px;
                font-weight: bold;
                border: 2px solid #e74c3c;
                border-radius: 10px;
                margin-top: 15px;
                padding: 10px;
            }
            QGroupBox::title {
                color: #e74c3c;
                subcontrol-position: top center;
                padding: 5px 20px;
                background-color: #2c3e50;
            }
            QLabel {
                color: #ecf0f1;
                font-size: 14px;
            }
            QSlider::handle:horizontal {
                background: #e74c3c;
                border: 2px solid #c0392b;
                width: 20px;
                margin: -5px 0;
                border-radius: 10px;
            }
            QSlider::groove:horizontal {
                border: 1px solid #bbb;
                background: #1a2733;
                height: 12px;
                border-radius: 6px;
            }
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                padding: 10px;
                border-radius: 5px;
                font-weight: bold;
                min-width: 100px;
                min-height: 30px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
            QPushButton:pressed {
                background-color: #a93226;
            }
            QProgressBar {
                border: 2px solid #c0392b;
                border-radius: 5px;
                text-align: center;
                background-color: #1a2733;
            }
            QProgressBar::chunk {
                background-color: #e74c3c;
            }
            QSpinBox {
                background-color: #34495e;
                color: white;
                border: 2px solid #c0392b;
                padding: 5px;
                border-radius: 5px;
                min-width: 80px;
                min-height: 30px;
            }
            QDial {
                background-color: #34495e;
            }
        """)

        # Üst Panel - Durum Göstergeleri
        status_panel = QHBoxLayout()
        
        # Hız Durumu
        speed_status = ControlWidget("Hız")
        speed_layout = QVBoxLayout()
        self.speed_display = QLabel("0 km/h")
        self.speed_display.setStyleSheet("font-size: 24px; color: #e74c3c;")
        self.speed_display.setAlignment(Qt.AlignCenter)
        speed_layout.addWidget(self.speed_display)
        speed_status.setLayout(speed_layout)
        
        # İrtifa Durumu
        altitude_status = ControlWidget("İrtifa")
        altitude_layout = QVBoxLayout()
        self.altitude_display = QLabel("0 m")
        self.altitude_display.setStyleSheet("font-size: 24px; color: #e74c3c;")
        self.altitude_display.setAlignment(Qt.AlignCenter)
        altitude_layout.addWidget(self.altitude_display)
        altitude_status.setLayout(altitude_layout)
        
        # Yön Durumu
        heading_status = ControlWidget("Yön")
        heading_layout = QVBoxLayout()
        self.heading_display = QLabel("0°")
        self.heading_display.setStyleSheet("font-size: 24px; color: #e74c3c;")
        self.heading_display.setAlignment(Qt.AlignCenter)
        heading_layout.addWidget(self.heading_display)
        heading_status.setLayout(heading_layout)
        
        status_panel.addWidget(speed_status)
        status_panel.addWidget(altitude_status)
        status_panel.addWidget(heading_status)
        
        main_layout.addLayout(status_panel)

        # Kontrol Paneli
        control_panel = QHBoxLayout()
        
        # Hız Kontrol Grubu
        speed_group = QGroupBox("Hız Kontrolü")
        speed_layout = QVBoxLayout()
        
        # Hız Slider
        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setRange(0, 180)
        self.speed_slider.setTickPosition(QSlider.TicksBelow)
        self.speed_slider.setTickInterval(20)
        
        # Hız Hassas Ayar
        speed_fine_control = QHBoxLayout()
        self.speed_decrease = QPushButton("-")
        self.speed_decrease.setFixedSize(40, 40)
        self.speed_spinbox = QSpinBox()
        self.speed_spinbox.setRange(0, 180)
        self.speed_spinbox.setSingleStep(5)
        self.speed_increase = QPushButton("+")
        self.speed_increase.setFixedSize(40, 40)
        
        speed_fine_control.addWidget(self.speed_decrease)
        speed_fine_control.addWidget(self.speed_spinbox)
        speed_fine_control.addWidget(self.speed_increase)
        
        speed_layout.addWidget(self.speed_slider)
        speed_layout.addLayout(speed_fine_control)
        speed_group.setLayout(speed_layout)
        
        # İrtifa Kontrol Grubu
        altitude_group = QGroupBox("İrtifa Kontrolü")
        altitude_layout = QVBoxLayout()
        
        # İrtifa Slider ve Progress Bar
        altitude_control = QHBoxLayout()
        self.altitude_slider = QSlider(Qt.Vertical)
        self.altitude_slider.setRange(0, 10000)
        self.altitude_slider.setTickPosition(QSlider.TicksLeft)
        self.altitude_slider.setTickInterval(1000)
        
        self.altitude_progress = QProgressBar()
        self.altitude_progress.setOrientation(Qt.Vertical)
        self.altitude_progress.setRange(0, 10000)
        self.altitude_progress.setTextVisible(True)
        self.altitude_progress.setFormat("%v m")
        
        altitude_control.addWidget(self.altitude_slider)
        altitude_control.addWidget(self.altitude_progress)
        
        # İrtifa Hassas Ayar
        altitude_fine_control = QHBoxLayout()
        self.altitude_decrease = QPushButton("-")
        self.altitude_decrease.setFixedSize(40, 40)
        self.altitude_spinbox = QSpinBox()
        self.altitude_spinbox.setRange(0, 10000)
        self.altitude_spinbox.setSingleStep(100)
        self.altitude_increase = QPushButton("+")
        self.altitude_increase.setFixedSize(40, 40)
        
        altitude_fine_control.addWidget(self.altitude_decrease)
        altitude_fine_control.addWidget(self.altitude_spinbox)
        altitude_fine_control.addWidget(self.altitude_increase)
        
        altitude_layout.addLayout(altitude_control)
        altitude_layout.addLayout(altitude_fine_control)
        altitude_group.setLayout(altitude_layout)
        
        # Yön Kontrol Grubu
        heading_group = QGroupBox("Yön Kontrolü")
        heading_layout = QVBoxLayout()
        
        self.heading_dial = QDial()
        self.heading_dial.setRange(0, 360)
        self.heading_dial.setNotchesVisible(True)
        self.heading_dial.setNotchTarget(45.0)
        self.heading_dial.setWrapping(True)
        
        # Yön Preset Butonları
        heading_presets = QHBoxLayout()
        directions = [("K", 0), ("KD", 45), ("D", 90), ("GD", 135),
                     ("G", 180), ("GB", 225), ("B", 270), ("KB", 315)]
        
        for name, angle in directions:
            btn = QPushButton(name)
            btn.setFixedSize(50, 50)
            btn.clicked.connect(lambda checked, a=angle: self.set_heading(a))
            heading_presets.addWidget(btn)
        
        heading_layout.addWidget(self.heading_dial)
        heading_layout.addLayout(heading_presets)
        heading_group.setLayout(heading_layout)
        
        # Kontrol gruplarını panele ekle
        control_panel.addWidget(speed_group)
        control_panel.addWidget(altitude_group)
        control_panel.addWidget(heading_group)
        
        main_layout.addLayout(control_panel)

        # Alt Panel - Acil Durum Kontrolleri
        emergency_panel = QHBoxLayout()
        
        self.emergency_stop = QPushButton("ACİL DURUŞ")
        self.emergency_stop.setStyleSheet("""
            QPushButton {
                background-color: #c0392b;
                font-size: 18px;
                min-height: 50px;
            }
            QPushButton:hover {
                background-color: #e74c3c;
            }
        """)
        
        self.return_home = QPushButton("EVE DÖNÜŞ")
        self.return_home.setStyleSheet("""
            QPushButton {
                background-color: #c0392b;
                font-size: 18px;
                min-height: 50px;
            }
            QPushButton:hover {
                background-color: #e74c3c;
            }
        """)
        
        emergency_panel.addWidget(self.emergency_stop)
        emergency_panel.addWidget(self.return_home)
        
        main_layout.addLayout(emergency_panel)
        
        self.setLayout(main_layout)
        
        # Bağlantıları kur
        self.setup_connections()

    def setup_connections(self):
        # Slider ve SpinBox bağlantıları
        self.speed_slider.valueChanged.connect(self.update_speed_display)
        self.speed_spinbox.valueChanged.connect(self.speed_slider.setValue)
        self.altitude_slider.valueChanged.connect(self.update_altitude_display)
        self.altitude_spinbox.valueChanged.connect(self.altitude_slider.setValue)
        self.heading_dial.valueChanged.connect(self.update_heading_display)
        
        # Buton bağlantıları
        self.speed_decrease.clicked.connect(lambda: self.adjust_speed(-5))
        self.speed_increase.clicked.connect(lambda: self.adjust_speed(5))
        self.altitude_decrease.clicked.connect(lambda: self.adjust_altitude(-100))
        self.altitude_increase.clicked.connect(lambda: self.adjust_altitude(100))

    def update_speed_display(self, value):
        self.speed_display.setText(f"{value} km/h")
        self.speed_spinbox.setValue(value)

    def update_altitude_display(self, value):
        self.altitude_display.setText(f"{value} m")
        self.altitude_spinbox.setValue(value)
        self.altitude_progress.setValue(value)

    def update_heading_display(self, value):
        self.heading_display.setText(f"{value}°")

    def adjust_speed(self, delta):
        new_value = self.speed_slider.value() + delta
        self.speed_slider.setValue(max(0, min(180, new_value)))

    def adjust_altitude(self, delta):
        new_value = self.altitude_slider.value() + delta
        self.altitude_slider.setValue(max(0, min(10000, new_value)))

    def set_heading(self, angle):
        self.heading_dial.setValue(angle)

    def connect_controls(self, set_speed, set_altitude, set_heading):
        self.speed_slider.valueChanged.connect(set_speed)
        self.altitude_slider.valueChanged.connect(set_altitude)
        self.heading_dial.valueChanged.connect(set_heading)