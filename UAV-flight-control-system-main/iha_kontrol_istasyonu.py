import sys
import random
import requests  # Hava durumu verilerini çekmek için
import pyqtgraph as pg
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
                             QLabel, QPushButton, QPlainTextEdit, QGroupBox, QLineEdit, QListWidget, QSizePolicy, QStackedWidget, QGridLayout, QProgressBar, QSlider, QDial)
from PyQt5.QtCore import QTimer, Qt, QPointF, QObject, pyqtSlot
from PyQt5.QtGui import QPixmap, QPainter, QBrush, QColor, QFont, QPen, QPainterPath
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtWebChannel import QWebChannel
from manuel_control import ManualControlPage
from sensor_pages import LidarPage, GPSSpoofingPage, ElectronicWarfarePage

class SpeedometerWidget(QWidget):
    def __init__(self, parent=None):
        super(SpeedometerWidget, self).__init__(parent)
        self.speed = 0  # Initial speed

    def setSpeed(self, speed):
        self.speed = speed
        self.update()  # Trigger a repaint

    def paintEvent(self, event):
        painter = QPainter(self)
        rect = self.rect()
        center = rect.center()
        radius = min(rect.width(), rect.height()) // 2 - 30  # Increased size

        # Draw the outer circle
        painter.setPen(QPen(QColor(200, 200, 200), 6))
        painter.setBrush(QColor(50, 50, 50))
        painter.drawEllipse(center, radius, radius)

        # Draw the speed text
        painter.setFont(QFont('Arial', 28))
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(rect, Qt.AlignCenter, f"{self.speed} km/h")

        # Draw the needle
        angle = (self.speed / 180.0) * 270.0 - 45.0  # Map speed to angle
        painter.setPen(QPen(QColor(255, 0, 0), 4))
        needle_end = self.calculateNeedlePosition(center, radius, angle)
        painter.drawLine(center, needle_end)

        # Draw the ticks
        painter.setPen(QPen(QColor(255, 255, 255), 3))
        for i in range(0, 181, 20):
            tick_angle = (i / 180.0) * 270.0 - 45.0
            tick_start = self.calculateNeedlePosition(center, radius - 10, tick_angle)
            tick_end = self.calculateNeedlePosition(center, radius, tick_angle)
            painter.drawLine(tick_start, tick_end)

    def calculateNeedlePosition(self, center, radius, angle):
        from math import radians, cos, sin
        angle_rad = radians(angle)
        x = center.x() + radius * cos(angle_rad)
        y = center.y() - radius * sin(angle_rad)
        return QPointF(x, y)

class FuelGaugeWidget(QWidget):
    def __init__(self, parent=None):
        super(FuelGaugeWidget, self).__init__(parent)
        self.fuel_level = 100  # Initial fuel level

    def setFuelLevel(self, fuel_level):
        self.fuel_level = fuel_level
        self.update()  # Trigger a repaint

    def paintEvent(self, event):
        painter = QPainter(self)
        rect = self.rect()
        center = rect.center()
        radius = min(rect.width(), rect.height()) // 2 - 30  # Increased size

        # Determine color based on fuel level
        if self.fuel_level < 20:
            color = QColor(255, 0, 0)  # Red for dangerous
        elif self.fuel_level < 50:
            color = QColor(255, 165, 0)  # Orange for caution
        else:
            color = QColor(0, 255, 0)  # Green for safe

        # Draw the outer circle
        painter.setPen(QPen(QColor(200, 200, 200), 6))
        painter.setBrush(QColor(50, 50, 50))
        painter.drawEllipse(center, radius, radius)

        # Draw the fuel text
        painter.setFont(QFont('Arial', 28))
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(rect, Qt.AlignCenter, f"{self.fuel_level:.1f}%")  # One decimal place

        # Draw the needle
        angle = (self.fuel_level / 100.0) * 270.0 - 45.0  # Map fuel level to angle
        painter.setPen(QPen(color, 4))
        needle_end = self.calculateNeedlePosition(center, radius, angle)
        painter.drawLine(center, needle_end)

        # Draw the ticks
        painter.setPen(QPen(QColor(255, 255, 255), 3))
        for i in range(0, 101, 10):
            tick_angle = (i / 100.0) * 270.0 - 45.0
            tick_start = self.calculateNeedlePosition(center, radius - 10, tick_angle)
            tick_end = self.calculateNeedlePosition(center, radius, tick_angle)
            painter.drawLine(tick_start, tick_end)

    def calculateNeedlePosition(self, center, radius, angle):
        from math import radians, cos, sin
        angle_rad = radians(angle)
        x = center.x() + radius * cos(angle_rad)
        y = center.y() - radius * sin(angle_rad)
        return QPointF(x, y)

class CompassWidget(QWidget):
    def __init__(self, parent=None):
        super(CompassWidget, self).__init__(parent)
        self.heading = 0  # Initial heading

    def setHeading(self, heading):
        self.heading = heading
        self.update()  # Trigger a repaint

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)  # Kenar yumuşatma ekle
        rect = self.rect()
        center = rect.center()
        radius = min(rect.width(), rect.height()) // 2 - 30

        # Draw the outer circle
        painter.setPen(QPen(QColor(200, 200, 200), 6))
        painter.setBrush(QColor(50, 50, 50))
        painter.drawEllipse(center, radius, radius)

        # Draw the directions with adjusted positions and font size
        directions = ['N', 'E', 'S', 'W']
        painter.setFont(QFont('Arial', radius // 8))  # Font boyutunu radius'a göre ayarla
        painter.setPen(QColor(255, 255, 255))
        
        for i, direction in enumerate(directions):
            angle = i * 90
            # Harflerin pozisyonunu çembere daha yakın ayarla
            text_radius = radius - (radius // 4)  # Harfleri çembere daha yakın konumlandır
            pos = self.calculateNeedlePosition(center, text_radius, angle)
            
            # Metin boyutlarını hesapla ve merkeze hizala
            fm = painter.fontMetrics()
            text_width = fm.width(direction)
            text_height = fm.height()
            text_pos = QPointF(pos.x() - text_width/2, pos.y() + text_height/2)
            painter.drawText(text_pos, direction)

        # Draw the needle
        angle = self.heading
        painter.setPen(QPen(QColor(255, 0, 0), 4))
        needle_end = self.calculateNeedlePosition(center, radius - 10, angle)  # İbreyi biraz kısalt
        painter.drawLine(center, needle_end)

    def calculateNeedlePosition(self, center, radius, angle):
        from math import radians, cos, sin
        angle_rad = radians(angle)
        x = center.x() + radius * cos(angle_rad)
        y = center.y() - radius * sin(angle_rad)
        return QPointF(x, y)

class WebBridge(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent

    @pyqtSlot(float, float)
    def handleClick(self, lat, lon):
        self.parent.add_map_waypoint(lat, lon)

class FlightControlStation(QWidget):
    def __init__(self):
        super().__init__()
        # Uçuş durumuna ilişkin değişkenler
        self.in_flight = False
        self.altitude = 0      # İrtifa (metre)
        self.speed = 0         # Hız (km/h)
        self.heading = 0       # Yön (derece)
        self.battery = 100     # Batarya (%)
        self.gps = "41.012345, 29.005678"  # GPS koordinatları
        self.power_consumption = 0  # Güç tüketimi (W)
        self.battery_time_left = "N/A"  # Kalan batarya süresi
        self.waypoints = []  # Waypoint listesi
        self.current_waypoint_index = 0  # Mevcut waypoint indeksi
        self.weather_info = "Hava durumu bilgisi yok"  # Hava durumu bilgisi
        self.detected_frequencies = []  # Tespit edilen rakip frekanslar
        self.fuel_level = 100  # Yakıt seviyesi (%)
        self.connection_status = False  # Bağlantı durumu
        self.flight_time_seconds = 0  # Uçuş süresi (saniye)
        self.waypoint_counter = 0  # Waypoint sayacı ekle
        self.start_point = None    # Başlangıç noktası
        self.end_point = None      # Bitiş noktası
        self.home_point = None     # Ev konumu
        self.saved_missions = {}  # Kaydedilen görevleri tutacak sözlük
        
        self.api_key = "YOUR_API_KEY"  # OpenWeatherMap API anahtarınızı buraya ekleyin
        
        # Önce sayfaları oluştur
        self.manual_control_page = ManualControlPage(self)
        self.manual_control_page.connect_controls(self.setManualSpeed, self.setManualAltitude, self.setManualHeading)
        
        self.lidar_page = LidarPage(self)
        self.gps_spoof_page = GPSSpoofingPage(self)
        self.ew_page = ElectronicWarfarePage(self)

        # Grafik sayfası için gerekli değişkenler
        self.t = 0
        self.time_list = []
        self.altitude_list = []
        self.speed_list = []
        self.battery_list = []
        self.power_list = []

        # Web bridge'i oluştur
        self.web_bridge = WebBridge(self)
        self.channel = QWebChannel()
        self.channel.registerObject('handler', self.web_bridge)

        # UI'ı başlat
        self.initUI()
        self.initTimer()
    
    def initUI(self):
        self.setWindowTitle('Essirius ALACA İHA Kontrol İstasyonu')
        self.setGeometry(100, 100, 1200, 800)
        
        # CSS Stilleri: Arka plan, yazı tipi ve buton tasarımı
        self.setStyleSheet("""
        QWidget {
            background-color: #2e2e2e;
            color: #f0f0f0;
            font-family: Arial;
            font-size: 14px;
        }
        QPushButton {
            background-color: #FF5733;
            border: none;
            padding: 10px;
            border-radius: 10px;
            color: white;
            min-width: 60px;
            font-size: 20px;
        }
        QPushButton:hover {
            background-color: #C70039;
        }
        QPlainTextEdit {
            background-color: #1e1e1e;
            border: 1px solid #555;
            padding: 5px;
            color: #f0f0f0;
        }
        QLabel {
            font-size: 16px;
        }
        """)
        
        # Main layout
        main_layout = QVBoxLayout()
        
        # Navigation buttons
        nav_layout = QHBoxLayout()
        
        self.main_page_button = QPushButton("Ana Sayfa", self)
        self.main_page_button.setFixedSize(160, 40)
        self.main_page_button.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(0))
        nav_layout.addWidget(self.main_page_button)
        
        self.manual_control_button = QPushButton("Manuel Kontrol", self)
        self.manual_control_button.setFixedSize(160, 40)
        self.manual_control_button.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(1))
        nav_layout.addWidget(self.manual_control_button)
        
        self.lidar_button = QPushButton("LiDAR", self)
        self.lidar_button.setFixedSize(160, 40)
        self.lidar_button.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(2))
        nav_layout.addWidget(self.lidar_button)
        
        self.gps_spoof_button = QPushButton("GPS Spoofing", self)
        self.gps_spoof_button.setFixedSize(160, 40)
        self.gps_spoof_button.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(3))
        nav_layout.addWidget(self.gps_spoof_button)
        
        self.ew_button = QPushButton("Elektronik Harp", self)
        self.ew_button.setFixedSize(160, 40)
        self.ew_button.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(4))
        nav_layout.addWidget(self.ew_button)
        
        self.map_button = QPushButton("Harita", self)
        self.map_button.setFixedSize(160, 40)
        self.map_button.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(5))
        nav_layout.addWidget(self.map_button)
        
        self.graphs_button = QPushButton("Grafikler", self)
        self.graphs_button.setFixedSize(160, 40)
        self.graphs_button.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(6))
        nav_layout.addWidget(self.graphs_button)
        
        nav_layout.addStretch()  # Add stretch to push buttons to the left
        main_layout.addLayout(nav_layout)
        
        # Stacked widget to hold different pages
        self.stacked_widget = QStackedWidget(self)
        
        # Main page
        main_page = QWidget()
        main_page_layout = QGridLayout()  # Changed to QGridLayout for fixed positioning
        
        # Logo ve Başlık
        header_layout = QHBoxLayout()
        
        # Logo
        logo_label = QLabel(self)
        pixmap = QPixmap("C:/Users/doguk/OneDrive/Masaüstü/Iha/Adsız.png")
        
        # Logo boyutunu ayarla
        scaled_pixmap = pixmap.scaled(80, 80, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        
        # Final görüntü için pixmap
        result = QPixmap(100, 100)
        result.fill(Qt.transparent)
        
        # Final painter
        painter = QPainter(result)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Dairesel maske oluştur
        path = QPainterPath()
        path.addEllipse(2, 2, 76, 76)
        painter.setClipPath(path)
        
        # Logoyu ortala ve çiz
        x = (80 - scaled_pixmap.width()) // 2
        y = (80 - scaled_pixmap.height()) // 2
        painter.drawPixmap(x, y, scaled_pixmap)
        painter.end()
        
        logo_label.setPixmap(result)
        logo_label.setFixedSize(100, 110)
        logo_label.setStyleSheet("""
            QLabel {
                background: transparent;
                margin: 5px;
                padding: 0px;
            }
        """)
        header_layout.addWidget(logo_label)
        
        # Ust başlık
        self.header_label = QLabel("Essirius ALACA İHA Kontrol İstasyonu (Yerli Milli Arduplot)", self)
        self.header_label.setStyleSheet("font-size: 24px; font-weight: bold; margin: 10px;")
        header_layout.addWidget(self.header_label)
        
        header_layout.addStretch()  # Add stretch to push header to the left
        main_page_layout.addLayout(header_layout, 0, 0, 1, 2)  # Place header at the top
        
        # Kontrol Butonları Layout'u
        control_layout = QGridLayout()
        self.takeoff_button = QPushButton("Kalkış", self)
        self.takeoff_button.clicked.connect(self.on_takeoff)
        self.land_button = QPushButton("İniş", self)
        self.land_button.clicked.connect(self.on_land)
        self.emergency_button = QPushButton("Acil Durum", self)
        self.emergency_button.clicked.connect(self.on_emergency)
        self.start_mission_button = QPushButton("Görevi Başlat", self)
        self.start_mission_button.clicked.connect(self.on_start_mission)
        self.return_home_button = QPushButton("Geri Dön", self)
        self.return_home_button.clicked.connect(self.on_return_home)

        control_layout.addWidget(self.takeoff_button, 0, 0)
        control_layout.addWidget(self.land_button, 0, 1)
        control_layout.addWidget(self.emergency_button, 0, 2)
        control_layout.addWidget(self.start_mission_button, 1, 0)
        control_layout.addWidget(self.return_home_button, 1, 1)
        
        main_page_layout.addLayout(control_layout, 1, 0)  # Place control buttons on the left
        
        # İHA Bilgileri Paneli
        telemetry_group = QGroupBox("İHA Bilgileri")
        telemetry_layout = QFormLayout()
        telemetry_layout.setLabelAlignment(Qt.AlignRight)
        
        self.altitude_value = QLabel("0 m", self)
        telemetry_layout.addRow("İrtifa:", self.altitude_value)
        
        self.speed_value = QLabel("0 km/h", self)
        telemetry_layout.addRow("Hız:", self.speed_value)
        
        self.heading_value = QLabel("0°", self)
        telemetry_layout.addRow("Yön:", self.heading_value)
        
        self.battery_value = QLabel("100%", self)
        telemetry_layout.addRow("Batarya:", self.battery_value)
        
        self.gps_value = QLabel("N/A", self)
        telemetry_layout.addRow("GPS:", self.gps_value)
        
        # Güç Tüketimi ve Batarya Süresi
        self.power_value = QLabel("0 W", self)
        telemetry_layout.addRow("Güç Tüketimi:", self.power_value)
        
        self.battery_time_value = QLabel("N/A", self)
        telemetry_layout.addRow("Kalan Batarya Süresi:", self.battery_time_value)
        
        telemetry_group.setLayout(telemetry_layout)
        main_page_layout.addWidget(telemetry_group, 2, 0)  # Place telemetry panel below control buttons
        
        # Durum Paneli
        status_group = QGroupBox("Durum Paneli")
        status_layout = QVBoxLayout()
        self.status_label = QLabel("Durum: Beklemede")
        self.flight_time_label = QLabel("Uçuş Süresi: 0 dk 0 sn", self)
        status_layout.addWidget(self.status_label)
        status_layout.addWidget(self.flight_time_label)
        status_group.setLayout(status_layout)
        main_page_layout.addWidget(status_group, 3, 0)  # Place status panel below telemetry
        
        # Görev Paneli
        mission_group = QGroupBox("Görev Paneli")
        mission_layout = QVBoxLayout()
        self.mission_label = QLabel("Görev: Yok")
        mission_layout.addWidget(self.mission_label)
        mission_group.setLayout(mission_layout)
        main_page_layout.addWidget(mission_group, 4, 0)  # Place mission panel below status
        
        # Uçuş Planı Paneli
        flight_plan_group = QGroupBox("Uçuş Planı")
        flight_plan_layout = QVBoxLayout()
        
        self.waypoint_input = QLineEdit(self)
        self.waypoint_input.setPlaceholderText("Yeni Waypoint (lat, lon)")
        flight_plan_layout.addWidget(self.waypoint_input)
        
        self.add_waypoint_button = QPushButton("Waypoint Ekle", self)
        self.add_waypoint_button.setFixedSize(140, 40)  # Slightly increased width
        self.add_waypoint_button.clicked.connect(self.add_waypoint)
        flight_plan_layout.addWidget(self.add_waypoint_button)
        
        self.waypoint_list = QListWidget(self)
        flight_plan_layout.addWidget(self.waypoint_list)
        
        flight_plan_group.setLayout(flight_plan_layout)
        main_page_layout.addWidget(flight_plan_group, 5, 0)  # Place flight plan panel below mission
        
        # Hava Durumu Paneli
        weather_group = QGroupBox("Hava Durumu")
        weather_layout = QVBoxLayout()
        self.weather_label = QLabel(self.weather_info)
        weather_layout.addWidget(self.weather_label)
        weather_group.setLayout(weather_layout)
        main_page_layout.addWidget(weather_group, 6, 0)  # Place weather panel below flight plan
        
        # Elektronik Harp Paneli
        ew_group = QGroupBox("Elektronik Harp")
        ew_layout = QVBoxLayout()
        
        # Frekans başlığı
        self.ew_label = QLabel("Tespit Edilen Frekanslar:")
        self.ew_label.setStyleSheet("""
            QLabel {
                color: #e74c3c;
                font-size: 12px;
                font-weight: bold;
                padding: 5px;
            }
        """)
        
        # Frekans listesi
        self.frequency_list = QListWidget(self)
        self.frequency_list.setStyleSheet("""
            QListWidget {
                background-color: #2c2c2c;
                border: 2px solid #c0392b;
                border-radius: 5px;
                padding: 5px;
                color: white;
                min-height: 100px;
            }
            QListWidget::item {
                padding: 5px;
                border-bottom: 1px solid #1a1a1a;
            }
            QListWidget::item:selected {
                background-color: #c0392b;
            }
        """)
        
        ew_layout.addWidget(self.ew_label)
        ew_layout.addWidget(self.frequency_list)
        ew_group.setLayout(ew_layout)
        
        # Elektronik Harp panel stili
        ew_group.setStyleSheet("""
            QGroupBox {
                font-size: 14px;
                font-weight: bold;
                border: 2px solid #e74c3c;
                border-radius: 8px;
                margin-top: 12px;
                padding: 15px;
                background-color: #1a1a1a;
            }
            QGroupBox::title {
                color: #e74c3c;
                subcontrol-position: top center;
                padding: 5px;
            }
        """)
        
        # Konsol Paneli
        log_group = QGroupBox("Konsol")
        log_layout = QVBoxLayout()
        
        self.log_area = QPlainTextEdit(self)
        self.log_area.setReadOnly(True)
        self.log_area.setMinimumHeight(150)
        self.log_area.setStyleSheet("""
            QPlainTextEdit {
                background-color: #2c2c2c;
                color: #ecf0f1;
                border: 2px solid #c0392b;
                border-radius: 5px;
                padding: 8px;
                font-family: 'Consolas', monospace;
                font-size: 12px;
            }
            QPlainTextEdit:focus {
                border: 2px solid #e74c3c;
            }
        """)
        
        log_layout.addWidget(self.log_area)
        log_group.setLayout(log_layout)
        
        # Konsol panel stili
        log_group.setStyleSheet("""
            QGroupBox {
                font-size: 14px;
                font-weight: bold;
                border: 2px solid #e74c3c;
                border-radius: 8px;
                margin-top: 12px;
                padding: 15px;
                background-color: #1a1a1a;
            }
            QGroupBox::title {
                color: #e74c3c;
                subcontrol-position: top center;
                padding: 5px;
            }
        """)
        
        # Indicators Group
        indicators_group = QGroupBox("Göstergeler")
        indicators_layout = QVBoxLayout()
        indicators_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)  # Genişleme politikası
        
        # Göstergeler için yatay layout
        gauges_layout = QHBoxLayout()
        gauges_layout.setSpacing(20)  # Göstergeler arası boşluk
        
        # Her gösterge için sabit genişlikli container widget
        speed_widget = QWidget()
        speed_widget.setFixedWidth(250)  # Sadece genişlik sabit
        speed_container = QVBoxLayout(speed_widget)
        self.speedometer = SpeedometerWidget(self)
        self.speedometer.setMinimumSize(200, 200)
        speed_label = QLabel("HIZ GÖSTERGESİ\nAnlık hız değerini km/h cinsinden gösterir")
        speed_label.setAlignment(Qt.AlignCenter)
        speed_label.setStyleSheet("""
            QLabel {
                color: #e74c3c;
                font-size: 11px;
                font-weight: bold;
                margin-top: 5px;
            }
        """)
        speed_container.addWidget(self.speedometer)
        speed_container.addWidget(speed_label)
        speed_container.setAlignment(Qt.AlignCenter)
        
        # Yakıt göstergesi container
        fuel_widget = QWidget()
        fuel_widget.setFixedWidth(250)  # Sadece genişlik sabit
        fuel_container = QVBoxLayout(fuel_widget)
        self.fuel_gauge = FuelGaugeWidget(self)
        self.fuel_gauge.setMinimumSize(200, 200)
        fuel_label = QLabel("BATARYA GÖSTERGESİ\nKalan batarya yüzdesini gösterir")
        fuel_label.setAlignment(Qt.AlignCenter)
        fuel_label.setStyleSheet("""
            QLabel {
                color: #2ecc71;
                font-size: 11px;
                font-weight: bold;
                margin-top: 5px;
            }
        """)
        fuel_container.addWidget(self.fuel_gauge)
        fuel_container.addWidget(fuel_label)
        fuel_container.setAlignment(Qt.AlignCenter)
        
        # Pusula göstergesi container
        compass_widget = QWidget()
        compass_widget.setFixedWidth(250)  # Sadece genişlik sabit
        compass_container = QVBoxLayout(compass_widget)
        self.compass = CompassWidget(self)
        self.compass.setMinimumSize(200, 200)
        compass_label = QLabel("PUSULA GÖSTERGESİ\nAracın yönünü derece cinsinden gösterir")
        compass_label.setAlignment(Qt.AlignCenter)
        compass_label.setStyleSheet("""
            QLabel {
                color: #e74c3c;
                font-size: 11px;
                font-weight: bold;
                margin-top: 5px;
            }
        """)
        compass_container.addWidget(self.compass)
        compass_container.addWidget(compass_label)
        compass_container.setAlignment(Qt.AlignCenter)
        
        # Göstergeleri ana layout'a ekle
        gauges_layout.addWidget(speed_widget, 1, Qt.AlignTop)
        gauges_layout.addWidget(fuel_widget, 1, Qt.AlignTop)
        gauges_layout.addWidget(compass_widget, 1, Qt.AlignTop)
        
        indicators_layout.addLayout(gauges_layout)
        indicators_group.setLayout(indicators_layout)
        
        # Bağlantı Paneli
        connection_group = QGroupBox("Bağlantı Paneli")
        connection_layout = QVBoxLayout()
        connection_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)  # Yatayda genişle, dikeyde sabit
        
        # Port ve Baudrate ayarları için container
        settings_container = QHBoxLayout()
        
        # Port ayarları
        port_layout = QVBoxLayout()
        port_label = QLabel("Port:")
        port_label.setStyleSheet("color: #e74c3c; font-weight: bold;")
        self.port_input = QLineEdit()
        self.port_input.setPlaceholderText("COM1")
        self.port_input.setStyleSheet("""
            QLineEdit {
                background-color: #2c2c2c;
                color: white;
                border: 2px solid #c0392b;
                border-radius: 5px;
                padding: 8px;
                min-height: 30px;
            }
            QLineEdit:focus {
                border: 2px solid #e74c3c;
            }
        """)
        port_layout.addWidget(port_label)
        port_layout.addWidget(self.port_input)
        
        # Baudrate ayarları
        baud_layout = QVBoxLayout()
        baud_label = QLabel("Baudrate:")
        baud_label.setStyleSheet("color: #e74c3c; font-weight: bold;")
        self.baudrate_input = QLineEdit()
        self.baudrate_input.setPlaceholderText("115200")
        self.baudrate_input.setStyleSheet("""
            QLineEdit {
                background-color: #2c2c2c;
                color: white;
                border: 2px solid #c0392b;
                border-radius: 5px;
                padding: 8px;
                min-height: 30px;
            }
            QLineEdit:focus {
                border: 2px solid #e74c3c;
            }
        """)
        baud_layout.addWidget(baud_label)
        baud_layout.addWidget(self.baudrate_input)
        
        settings_container.addLayout(port_layout)
        settings_container.addLayout(baud_layout)
        
        # Bağlantı butonları
        button_container = QHBoxLayout()
        self.connect_button = QPushButton("Bağlan", self)
        self.connect_button.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                padding: 10px;
                border-radius: 5px;
                font-weight: bold;
                min-width: 120px;
                min-height: 40px;
            }
            QPushButton:hover {
                background-color: #2ecc71;
            }
        """)
        
        self.disconnect_button = QPushButton("Bağlantıyı Kes", self)
        self.disconnect_button.setStyleSheet("""
            QPushButton {
                background-color: #c0392b;
                color: white;
                border: none;
                padding: 10px;
                border-radius: 5px;
                font-weight: bold;
                min-width: 120px;
                min-height: 40px;
            }
            QPushButton:hover {
                background-color: #e74c3c;
            }
        """)
        
        button_container.addWidget(self.connect_button)
        button_container.addWidget(self.disconnect_button)
        
        # Bağlantı durumu
        self.connection_status_label = QLabel("Bağlantı Durumu: Kesik", self)
        self.connection_status_label.setStyleSheet("color: red;")  # Başlangıçta kırmızı
        self.connection_status_label.setAlignment(Qt.AlignCenter)
        
        connection_layout.addLayout(settings_container)
        connection_layout.addLayout(button_container)
        connection_layout.addWidget(self.connection_status_label)
        
        connection_group.setLayout(connection_layout)
        connection_group.setStyleSheet("""
            QGroupBox {
                font-size: 14px;
                font-weight: bold;
                border: 2px solid #e74c3c;
                border-radius: 8px;
                margin-top: 12px;
                padding: 15px;
                background-color: #1a1a1a;
            }
            QGroupBox::title {
                color: #e74c3c;
                subcontrol-position: top center;
                padding: 5px;
            }
        """)
        
        # Sağ taraf için container widget güncelleme
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setSpacing(10)  # Paneller arası boşluk
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        # Göstergeler ve Bağlantı panellerini ekle
        right_layout.addWidget(indicators_group)
        right_layout.addWidget(connection_group)
        
        # Elektronik Harp Paneli
        ew_group = QGroupBox("Elektronik Harp")
        ew_layout = QVBoxLayout()
        
        # Frekans başlığı
        self.ew_label = QLabel("Tespit Edilen Frekanslar:")
        self.ew_label.setStyleSheet("""
            QLabel {
                color: #e74c3c;
                font-size: 12px;
                font-weight: bold;
                padding: 5px;
            }
        """)
        
        # Frekans listesi
        self.frequency_list = QListWidget(self)
        self.frequency_list.setStyleSheet("""
            QListWidget {
                background-color: #2c2c2c;
                border: 2px solid #c0392b;
                border-radius: 5px;
                padding: 5px;
                color: white;
                min-height: 100px;
            }
            QListWidget::item {
                padding: 5px;
                border-bottom: 1px solid #1a1a1a;
            }
            QListWidget::item:selected {
                background-color: #c0392b;
            }
        """)
        
        ew_layout.addWidget(self.ew_label)
        ew_layout.addWidget(self.frequency_list)
        ew_group.setLayout(ew_layout)
        
        # Elektronik Harp panel stili
        ew_group.setStyleSheet("""
            QGroupBox {
                font-size: 14px;
                font-weight: bold;
                border: 2px solid #e74c3c;
                border-radius: 8px;
                margin-top: 12px;
                padding: 15px;
                background-color: #1a1a1a;
            }
            QGroupBox::title {
                color: #e74c3c;
                subcontrol-position: top center;
                padding: 5px;
            }
        """)
        
        # Konsol Paneli
        log_group = QGroupBox("Konsol")
        log_layout = QVBoxLayout()
        
        self.log_area = QPlainTextEdit(self)
        self.log_area.setReadOnly(True)
        self.log_area.setMinimumHeight(150)
        self.log_area.setStyleSheet("""
            QPlainTextEdit {
                background-color: #2c2c2c;
                color: #ecf0f1;
                border: 2px solid #c0392b;
                border-radius: 5px;
                padding: 8px;
                font-family: 'Consolas', monospace;
                font-size: 12px;
            }
            QPlainTextEdit:focus {
                border: 2px solid #e74c3c;
            }
        """)
        
        log_layout.addWidget(self.log_area)
        log_group.setLayout(log_layout)
        
        # Konsol panel stili
        log_group.setStyleSheet("""
            QGroupBox {
                font-size: 14px;
                font-weight: bold;
                border: 2px solid #e74c3c;
                border-radius: 8px;
                margin-top: 12px;
                padding: 15px;
                background-color: #1a1a1a;
            }
            QGroupBox::title {
                color: #e74c3c;
                subcontrol-position: top center;
                padding: 5px;
            }
        """)
        
        # Yeni panelleri sağ layout'a ekle
        right_layout.addWidget(ew_group)
        right_layout.addWidget(log_group)
        right_layout.addStretch(0)  # Alt boşluğu kaldır
        
        main_page_layout.addWidget(right_container, 0, 2, -1, 1)  # Sağ tarafı tamamen kapla
        
        main_page.setLayout(main_page_layout)
        
        # Map Page
        map_page = QWidget()
        map_layout = QVBoxLayout()

        # Üst panel - Kontrol paneli
        top_panel = QHBoxLayout()

        # Sol panel - Koordinat ve waypoint listesi
        left_panel = QVBoxLayout()
        
        # Koordinat girişi
        coord_group = QGroupBox("Koordinat Girişi")
        coord_layout = QHBoxLayout()
        
        lat_layout = QVBoxLayout()
        lat_label = QLabel("Enlem:")
        lat_label.setStyleSheet("color: #e74c3c; font-weight: bold;")
        self.lat_input = QLineEdit()
        self.lat_input.setPlaceholderText("41.0082")
        self.lat_input.setStyleSheet("""
            QLineEdit {
                background-color: #2c2c2c;
                color: white;
                border: 2px solid #c0392b;
                border-radius: 5px;
                padding: 8px;
            }
        """)
        lat_layout.addWidget(lat_label)
        lat_layout.addWidget(self.lat_input)
        
        lon_layout = QVBoxLayout()
        lon_label = QLabel("Boylam:")
        lon_label.setStyleSheet("color: #e74c3c; font-weight: bold;")
        self.lon_input = QLineEdit()
        self.lon_input.setPlaceholderText("28.9784")
        self.lon_input.setStyleSheet("""
            QLineEdit {
                background-color: #2c2c2c;
                color: white;
                border: 2px solid #c0392b;
                border-radius: 5px;
                padding: 8px;
            }
        """)
        lon_layout.addWidget(lon_label)
        lon_layout.addWidget(self.lon_input)
        
        coord_layout.addLayout(lat_layout)
        coord_layout.addLayout(lon_layout)
        coord_group.setLayout(coord_layout)
        
        # Waypoint Listesi
        waypoint_list_group = QGroupBox("Waypoint Listesi")
        waypoint_list_layout = QVBoxLayout()
        self.map_waypoint_list = QListWidget()
        self.map_waypoint_list.setStyleSheet("""
            QListWidget {
                background-color: #2c2c2c;
                color: white;
                border: 2px solid #c0392b;
                border-radius: 5px;
                padding: 5px;
            }
            QListWidget::item {
                padding: 5px;
                border-bottom: 1px solid #1a1a1a;
            }
        """)
        waypoint_list_layout.addWidget(self.map_waypoint_list)
        waypoint_list_group.setLayout(waypoint_list_layout)
        
        # Kayıtlı Görevler
        saved_missions_group = QGroupBox("Kayıtlı Görevler")
        saved_missions_layout = QVBoxLayout()
        self.saved_missions_list = QListWidget()
        self.saved_missions_list.setStyleSheet("""
            QListWidget {
                background-color: #2c2c2c;
                color: white;
                border: 2px solid #c0392b;
                border-radius: 5px;
                padding: 5px;
            }
        """)
        saved_missions_layout.addWidget(self.saved_missions_list)
        saved_missions_group.setLayout(saved_missions_layout)
        
        # Sol panele grupları ekle
        left_panel.addWidget(coord_group)
        left_panel.addWidget(waypoint_list_group)
        left_panel.addWidget(saved_missions_group)
        
        # Waypoint kontrolleri
        waypoint_group = QGroupBox("Waypoint Kontrolleri")
        waypoint_layout = QVBoxLayout()
        
        # Üst sıra butonları
        top_buttons = QHBoxLayout()
        self.add_start_point_button = QPushButton("Başlangıç Noktası Ekle")
        self.add_end_point_button = QPushButton("Bitiş Noktası Ekle")
        self.add_home_point_button = QPushButton("Ev Konumu Ayarla")
        
        # Alt sıra butonları
        bottom_buttons = QHBoxLayout()
        self.add_waypoint_map_button = QPushButton("Waypoint Ekle")
        self.clear_waypoints_button = QPushButton("Noktaları Temizle")
        self.save_mission_button = QPushButton("Görevi Kaydet")
        self.load_mission_button = QPushButton("Görevi Yükle")
        self.start_mission_map_button = QPushButton("Görevi Başlat")
        
        for button in [self.add_start_point_button, self.add_end_point_button, 
                      self.add_home_point_button, self.add_waypoint_map_button,
                      self.clear_waypoints_button, self.save_mission_button,
                      self.load_mission_button, self.start_mission_map_button]:
            button.setStyleSheet("""
                QPushButton {
                    background-color: #e74c3c;
                    color: white;
                    border: none;
                    padding: 10px;
                    border-radius: 5px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #c0392b;
                }
            """)
        
        top_buttons.addWidget(self.add_start_point_button)
        top_buttons.addWidget(self.add_end_point_button)
        top_buttons.addWidget(self.add_home_point_button)
        
        bottom_buttons.addWidget(self.add_waypoint_map_button)
        bottom_buttons.addWidget(self.clear_waypoints_button)
        bottom_buttons.addWidget(self.save_mission_button)
        bottom_buttons.addWidget(self.load_mission_button)
        bottom_buttons.addWidget(self.start_mission_map_button)
        
        waypoint_layout.addLayout(top_buttons)
        waypoint_layout.addLayout(bottom_buttons)
        waypoint_group.setLayout(waypoint_layout)
        
        # Buton bağlantıları
        self.add_start_point_button.clicked.connect(self.add_start_point)
        self.add_end_point_button.clicked.connect(self.add_end_point)
        self.add_home_point_button.clicked.connect(self.add_home_point)
        self.add_waypoint_map_button.clicked.connect(lambda: self.add_map_waypoint(
            float(self.lat_input.text()), float(self.lon_input.text())
        ))
        self.clear_waypoints_button.clicked.connect(self.clear_map_waypoints)
        self.save_mission_button.clicked.connect(self.save_current_mission)
        self.load_mission_button.clicked.connect(self.load_selected_mission)
        self.start_mission_map_button.clicked.connect(self.start_map_mission)
        
        # Ana layout'a panelleri ekle
        top_panel.addWidget(waypoint_group)
        
        # Harita ve sol panel için container
        map_container = QHBoxLayout()
        left_panel_widget = QWidget()
        left_panel_widget.setLayout(left_panel)
        left_panel_widget.setFixedWidth(300)  # Sol panel genişliği
        
        # Harita widget'ı
        self.map_view = QWebEngineView()
        self.map_view.page().setWebChannel(self.channel)
        self.map_view.setHtml(self.generate_map_html())
        
        map_container.addWidget(left_panel_widget)
        map_container.addWidget(self.map_view)
        
        # Ana layout'a elementleri ekle
        map_layout.addLayout(top_panel)
        map_layout.addLayout(map_container)
        
        map_page.setLayout(map_layout)
        
        # Graphs page
        graphs_page = QWidget()
        graphs_layout = QVBoxLayout()
        
        # İrtifa Grafiği
        altitude_group = QGroupBox("İrtifa Grafiği")
        altitude_layout = QVBoxLayout()
        self.altitude_plot = pg.PlotWidget()
        self.altitude_plot.setBackground('#2c2c2c')
        self.altitude_plot.setLabel('left', 'İrtifa (m)', color='#ffffff')
        self.altitude_plot.setLabel('bottom', 'Zaman (s)', color='#ffffff')
        self.altitude_plot.showGrid(x=True, y=True, alpha=0.3)
        self.altitude_curve = self.altitude_plot.plot(pen=pg.mkPen(color='#e74c3c', width=2))
        altitude_layout.addWidget(self.altitude_plot)
        altitude_group.setLayout(altitude_layout)
        
        # Hız Grafiği
        speed_group = QGroupBox("Hız Grafiği")
        speed_layout = QVBoxLayout()
        self.speed_plot = pg.PlotWidget()
        self.speed_plot.setBackground('#2c2c2c')
        self.speed_plot.setLabel('left', 'Hız (km/h)', color='#ffffff')
        self.speed_plot.setLabel('bottom', 'Zaman (s)', color='#ffffff')
        self.speed_plot.showGrid(x=True, y=True, alpha=0.3)
        self.speed_curve = self.speed_plot.plot(pen=pg.mkPen(color='#e74c3c', width=2))
        speed_layout.addWidget(self.speed_plot)
        speed_group.setLayout(speed_layout)
        
        # Batarya Grafiği
        battery_group = QGroupBox("Batarya Grafiği")
        battery_layout = QVBoxLayout()
        self.battery_plot = pg.PlotWidget()
        self.battery_plot.setBackground('#2c2c2c')
        self.battery_plot.setLabel('left', 'Batarya (%)', color='#ffffff')
        self.battery_plot.setLabel('bottom', 'Zaman (s)', color='#ffffff')
        self.battery_plot.showGrid(x=True, y=True, alpha=0.3)
        self.battery_curve = self.battery_plot.plot(pen=pg.mkPen(color='#2ecc71', width=2))
        battery_layout.addWidget(self.battery_plot)
        battery_group.setLayout(battery_layout)
        
        # Güç Tüketimi Grafiği
        power_group = QGroupBox("Güç Tüketimi Grafiği")
        power_layout = QVBoxLayout()
        self.power_plot = pg.PlotWidget()
        self.power_plot.setBackground('#2c2c2c')
        self.power_plot.setLabel('left', 'Güç (W)', color='#ffffff')
        self.power_plot.setLabel('bottom', 'Zaman (s)', color='#ffffff')
        self.power_plot.showGrid(x=True, y=True, alpha=0.3)
        self.power_curve = self.power_plot.plot(pen=pg.mkPen(color='#f1c40f', width=2))
        power_layout.addWidget(self.power_plot)
        power_group.setLayout(power_layout)
        
        # Grafik gruplarını ana layout'a ekle
        graphs_layout.addWidget(altitude_group)
        graphs_layout.addWidget(speed_group)
        graphs_layout.addWidget(battery_group)
        graphs_layout.addWidget(power_group)
        
        # Stil ayarları
        for group in [altitude_group, speed_group, battery_group, power_group]:
            group.setStyleSheet("""
                QGroupBox {
                    font-size: 14px;
                    font-weight: bold;
                    border: 2px solid #e74c3c;
                    border-radius: 8px;
                    margin-top: 12px;
                    padding: 15px;
                    background-color: #1a1a1a;
                }
                QGroupBox::title {
                    color: #e74c3c;
                    subcontrol-position: top center;
                    padding: 5px;
                }
            """)
        
        graphs_page.setLayout(graphs_layout)
        
        # Stacked widget'a sayfaları ekle
        self.stacked_widget.addWidget(main_page)                # index 0
        self.stacked_widget.addWidget(self.manual_control_page) # index 1
        self.stacked_widget.addWidget(self.lidar_page)         # index 2
        self.stacked_widget.addWidget(self.gps_spoof_page)     # index 3
        self.stacked_widget.addWidget(self.ew_page)            # index 4
        self.stacked_widget.addWidget(map_page)                # index 5
        self.stacked_widget.addWidget(graphs_page)             # index 6
        
        main_layout.addWidget(self.stacked_widget)
        self.setLayout(main_layout)
    
    def initTimer(self):
        # Telemetri bilgilerini her saniye güncelleyen timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_telemetry)
        self.timer.start(1000)  # Her 1000 milisaniyede bir
    
    def update_telemetry(self):
        # Eğer uçuşta ise telemetri değerlerini simüle et
        if self.in_flight:
            self.flight_time_seconds += 1
            self.altitude += random.randint(5, 15)  # İrtifayı artır
            self.speed = random.randint(30, 60)
            self.heading = (self.heading + random.randint(-5, 5)) % 360
            self.power_consumption = random.uniform(50, 150)  # Güç tüketimi simülasyonu
            self.battery = max(0, self.battery - self.power_consumption / 1000)  # Batarya tüketimi
            # GPS koordinatlarında küçük değişiklikler simüle et
            lat_change = random.uniform(-0.0001, 0.0001)
            lon_change = random.uniform(-0.0001, 0.0001)
            try:
                lat, lon = map(float, self.gps.split(','))
            except:
                lat, lon = 41.012345, 29.005678
            lat += lat_change
            lon += lon_change
            self.gps = f"{lat:.6f}, {lon:.6f}"
            
            # Kalan batarya süresi hesapla
            if self.power_consumption > 0:
                self.battery_time_left = f"{self.battery / (self.power_consumption / 1000):.1f} s"
            else:
                self.battery_time_left = "N/A"
            
            # Waypoint'ler arasında geçiş yap
            if self.waypoints:
                current_waypoint = self.waypoints[self.current_waypoint_index]
                self.gps = current_waypoint
                self.current_waypoint_index = (self.current_waypoint_index + 1) % len(self.waypoints)
            
            # Tespit edilen frekansları simüle et
            self.detect_frequencies()
        else:
            # Uçuşta değilken irtifa ve hız sıfırlansın
            self.altitude = 0
            self.speed = 0
            self.power_consumption = 0
            self.battery_time_left = "N/A"
            self.flight_time_seconds = 0
        
        # Telemetri etiketlerini güncelle
        self.altitude_value.setText(f"{self.altitude} m")
        self.speed_value.setText(f"{self.speed} km/h")
        self.heading_value.setText(f"{self.heading}°")
        self.battery_value.setText(f"{self.battery:.1f}%")
        self.gps_value.setText(self.gps)
        self.power_value.setText(f"{self.power_consumption:.1f} W")
        self.battery_time_value.setText(self.battery_time_left)
        
        # Grafik verilerini güncelle
        self.t += 1
        self.time_list.append(self.t)
        self.altitude_list.append(self.altitude)
        self.speed_list.append(self.speed)
        self.battery_list.append(self.battery)
        self.power_list.append(self.power_consumption)
        
        # Grafikleri 100 noktaya kadar tut
        if len(self.time_list) > 100:
            self.time_list = self.time_list[-100:]
            self.altitude_list = self.altitude_list[-100:]
            self.speed_list = self.speed_list[-100:]
            self.battery_list = self.battery_list[-100:]
            self.power_list = self.power_list[-100:]
        
        # Grafikleri güncelle
        self.altitude_curve.setData(self.time_list, self.altitude_list)
        self.speed_curve.setData(self.time_list, self.speed_list)
        self.battery_curve.setData(self.time_list, self.battery_list)
        self.power_curve.setData(self.time_list, self.power_list)
        
        self.speedometer.setSpeed(self.speed)
        self.fuel_gauge.setFuelLevel(self.battery)
        self.compass.setHeading(self.heading)
        
        # Flight Time Display
        minutes, seconds = divmod(self.flight_time_seconds, 60)
        self.flight_time_label.setText(f"Uçuş Süresi: {minutes} dk {seconds} sn")
   
    def detect_frequencies(self):
        # Tespit edilen frekansları simüle et
        new_frequency = random.uniform(1.0, 10.0)  # 1.0 - 10.0 GHz arası rastgele frekans
        self.detected_frequencies.append(f"{new_frequency:.2f} GHz")
        self.frequency_list.addItem(f"{new_frequency:.2f} GHz")
    
    def update_weather(self):
        # Hava durumu verilerini OpenWeatherMap API'sinden çek
        try:
            lat, lon = map(float, self.gps.split(','))
            url = f"http://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={self.api_key}&units=metric"
            response = requests.get(url)
            data = response.json()
            if data.get("weather"):
                weather_description = data["weather"][0]["description"]
                temperature = data["main"]["temp"]
                self.weather_info = f"{weather_description}, {temperature}°C"
            else:
                self.weather_info = "Hava durumu bilgisi alınamadı"
        except Exception as e:
            self.weather_info = f"Hata: {e}"
        
        self.weather_label.setText(self.weather_info)
    
    def generate_map_html(self):
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Map</title>
            <meta charset="utf-8" />
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <link rel="stylesheet" href="https://unpkg.com/leaflet/dist/leaflet.css" />
            <script src="https://unpkg.com/leaflet/dist/leaflet.js"></script>
            <script src="qrc:///qtwebchannel/qwebchannel.js"></script>
            <style>
                #map { height: 100vh; }
            </style>
        </head>
        <body style="margin:0;">
            <div id="map"></div>
            <script>
                var map = L.map('map').setView([41.0082, 28.9784], 13);
                var markers = [];
                var path;
                var startMarker = null;
                var endMarker = null;
                
                L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                    maxZoom: 19,
                    attribution: '© OpenStreetMap contributors'
                }).addTo(map);
                
                // Özel marker ikonları
                var startIcon = L.icon({
                    iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-green.png',
                    iconSize: [25, 41],
                    iconAnchor: [12, 41],
                    popupAnchor: [1, -34]
                });
                
                var endIcon = L.icon({
                    iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-red.png',
                    iconSize: [25, 41],
                    iconAnchor: [12, 41],
                    popupAnchor: [1, -34]
                });
                
                new QWebChannel(qt.webChannelTransport, function(channel) {
                    window.handler = channel.objects.handler;
                    
                    map.on('click', function(e) {
                        var marker = L.marker(e.latlng).addTo(map);
                        markers.push(marker);
                        
                        // Waypoint'ler arası çizgi çiz
                        var points = markers.map(m => m.getLatLng());
                        if (startMarker) points.unshift(startMarker.getLatLng());
                        if (endMarker) points.push(endMarker.getLatLng());
                        
                        if (path) {
                            map.removeLayer(path);
                        }
                        path = L.polyline(points, {color: '#e74c3c', weight: 3}).addTo(map);
                        
                        // Python'a koordinatları gönder
                        handler.handleClick(e.latlng.lat, e.latlng.lng);
                    });
                });
                
                function addStartPoint(lat, lon) {
                    if (startMarker) {
                        map.removeLayer(startMarker);
                    }
                    startMarker = L.marker([lat, lon], {icon: startIcon}).addTo(map);
                    startMarker.bindPopup('Başlangıç Noktası').openPopup();
                    updatePath();
                }
                
                function addEndPoint(lat, lon) {
                    if (endMarker) {
                        map.removeLayer(endMarker);
                    }
                    endMarker = L.marker([lat, lon], {icon: endIcon}).addTo(map);
                    endMarker.bindPopup('Bitiş Noktası').openPopup();
                    updatePath();
                }
                
                function updatePath() {
                    var points = markers.map(m => m.getLatLng());
                    if (startMarker) points.unshift(startMarker.getLatLng());
                    if (endMarker) points.push(endMarker.getLatLng());
                    
                    if (path) {
                        map.removeLayer(path);
                    }
                    if (points.length > 1) {
                        path = L.polyline(points, {color: '#e74c3c', weight: 3}).addTo(map);
                    }
                }
                
                function clearWaypoints() {
                    markers.forEach(m => map.removeLayer(m));
                    markers = [];
                    if (startMarker) {
                        map.removeLayer(startMarker);
                        startMarker = null;
                    }
                    if (endMarker) {
                        map.removeLayer(endMarker);
                        endMarker = null;
                    }
                    if (path) {
                        map.removeLayer(path);
                        path = null;
                    }
                }
            </script>
        </body>
        </html>
        """
    
    def log_message(self, message):
        # Zaman damgalı log mesajı ekler
        time_str = datetime.now().strftime('%H:%M:%S')
        self.log_area.appendPlainText(f"[{time_str}] {message}")
    
    def on_takeoff(self):
        if not self.in_flight:
            self.in_flight = True
            self.altitude = 0
            self.speed = 0
            self.heading = 0
            self.battery = 100
            self.gps = "41.012345, 29.005678"
            self.log_message("Kalkış gerçekleştiriliyor.")
            self.header_label.setText("Kalkış Başarılı!")
            self.status_label.setText("Durum: Uçuşta")
        else:
            self.log_message("Uçuş zaten devam ediyor.")
    
    def on_land(self):
        if self.in_flight:
            self.in_flight = False
            self.altitude = 0
            self.speed = 0
            self.log_message("İniş gerçekleştiriliyor.")
            self.header_label.setText("İniş Yapıldı!")
            self.status_label.setText("Durum: İniş Yapıldı")
        else:
            self.log_message("Uçuş yapılmıyor.")
    
    def on_emergency(self):
        self.in_flight = False
        self.altitude = 0
        self.speed = 0
        self.log_message("ACİL DURUM! Uçuş derhal durduruldu!")
        self.header_label.setText("ACİL DURUM!")
        self.status_label.setText("Durum: Acil Durum")
    
    def on_start_mission(self):
        if self.in_flight:
            self.log_message("Görev başlatıldı.")
            self.header_label.setText("Görev Devam Ediyor!")
            self.mission_label.setText("Görev: Aktif")
        else:
            self.log_message("Uçuşa başlanmadan görev başlatılamaz!")
    
    def on_return_home(self):
        if self.in_flight:
            self.log_message("Geri dönüş başlatıldı.")
            self.header_label.setText("Geri Dönüş Devam Ediyor!")
            self.mission_label.setText("Görev: Geri Dönüş")
        else:
            self.log_message("Uçuş yapılmıyor.")
    
    def add_waypoint(self):
        waypoint = self.waypoint_input.text()
        if waypoint:
            self.waypoints.append(waypoint)
            self.waypoint_list.addItem(waypoint)
            self.waypoint_input.clear()
            self.log_message(f"Waypoint eklendi: {waypoint}")

    def setManualSpeed(self, value):
        self.speed = value
        self.speedometer.setSpeed(self.speed)

    def setManualAltitude(self, value):
        self.altitude = value
        # Update altitude display or any related functionality

    def setManualHeading(self, value):
        self.heading = value
        self.compass.setHeading(self.heading)

    def connect(self):
        # Simulate connection
        self.connection_status = True
        self.connection_status_label.setText("Bağlantı Durumu: Aktif")
        self.connection_status_label.setStyleSheet("color: green;")

    def disconnect(self):
        # Simulate disconnection
        self.connection_status = False
        self.connection_status_label.setText("Bağlantı Durumu: Kesik")
        self.connection_status_label.setStyleSheet("color: red;")

    def add_map_waypoint(self, lat, lon):
        self.waypoint_counter += 1
        waypoint = f"Waypoint {self.waypoint_counter}: {lat:.6f}, {lon:.6f}"
        self.waypoints.append(waypoint)
        self.map_waypoint_list.addItem(waypoint)
        self.log_message(f"Haritadan waypoint eklendi: {waypoint}")

    def add_start_point(self):
        try:
            lat = float(self.lat_input.text())
            lon = float(self.lon_input.text())
            self.start_point = f"Başlangıç: {lat:.6f}, {lon:.6f}"
            self.map_waypoint_list.insertItem(0, self.start_point)
            self.map_view.page().runJavaScript(
                f"addStartPoint({lat}, {lon});"
            )
            self.log_message(f"Başlangıç noktası eklendi: {lat}, {lon}")
        except ValueError:
            self.log_message("Geçersiz koordinat formatı!")

    def add_end_point(self):
        try:
            lat = float(self.lat_input.text())
            lon = float(self.lon_input.text())
            self.end_point = f"Bitiş: {lat:.6f}, {lon:.6f}"
            self.map_waypoint_list.addItem(self.end_point)
            self.map_view.page().runJavaScript(
                f"addEndPoint({lat}, {lon});"
            )
            self.log_message(f"Bitiş noktası eklendi: {lat}, {lon}")
        except ValueError:
            self.log_message("Geçersiz koordinat formatı!")

    def clear_map_waypoints(self):
        self.waypoints.clear()
        self.map_waypoint_list.clear()
        self.waypoint_counter = 0
        self.start_point = None
        self.end_point = None
        self.map_view.page().runJavaScript("clearWaypoints();")
        self.log_message("Tüm noktalar temizlendi")

    def start_map_mission(self):
        if not self.waypoints:
            self.log_message("Waypoint olmadan görev başlatılamaz!")
            return
        
        if not self.in_flight:
            self.log_message("Önce kalkış yapılmalı!")
            return
        
        self.log_message("Görev başlatıldı!")
        self.mission_label.setText(f"Görev: {len(self.waypoints)} waypoint'li görev aktif")
        # Görev başlatma kodları buraya eklenecek

    def add_home_point(self):
        try:
            lat = float(self.lat_input.text())
            lon = float(self.lon_input.text())
            self.home_point = f"Ev Konumu: {lat:.6f}, {lon:.6f}"
            # Listede ev konumu varsa güncelle, yoksa başa ekle
            found = False
            for i in range(self.map_waypoint_list.count()):
                if self.map_waypoint_list.item(i).text().startswith("Ev Konumu:"):
                    self.map_waypoint_list.item(i).setText(self.home_point)
                    found = True
                    break
            if not found:
                self.map_waypoint_list.insertItem(0, self.home_point)
            
            self.map_view.page().runJavaScript(
                f"addHomePoint({lat}, {lon});"
            )
            self.log_message(f"Ev konumu ayarlandı: {lat}, {lon}")
        except ValueError:
            self.log_message("Geçersiz koordinat formatı!")

    def save_current_mission(self):
        mission_name = f"Görev_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        mission = []
        for i in range(self.map_waypoint_list.count()):
            mission.append(self.map_waypoint_list.item(i).text())
        
        self.saved_missions_list.addItem(mission_name)
        self.saved_missions[mission_name] = mission
        self.log_message(f"Görev kaydedildi: {mission_name}")

    def load_selected_mission(self):
        current_item = self.saved_missions_list.currentItem()
        if current_item is None:
            self.log_message("Yüklenecek görev seçilmedi!")
            return
            
        mission_name = current_item.text()
        if mission_name in self.saved_missions:
            self.clear_map_waypoints()
            for waypoint in self.saved_missions[mission_name]:
                self.map_waypoint_list.addItem(waypoint)
                # Koordinatları haritada göster
                if ":" in waypoint:
                    type_str, coords = waypoint.split(":", 1)
                    lat, lon = map(float, coords.strip().split(","))
                    if "Başlangıç" in type_str:
                        self.map_view.page().runJavaScript(f"addStartPoint({lat}, {lon});")
                    elif "Bitiş" in type_str:
                        self.map_view.page().runJavaScript(f"addEndPoint({lat}, {lon});")
                    elif "Ev Konumu" in type_str:
                        self.map_view.page().runJavaScript(f"addHomePoint({lat}, {lon});")
                    else:
                        self.add_map_waypoint(lat, lon)
            
            self.log_message(f"Görev yüklendi: {mission_name}")
        else:
            self.log_message("Görev bulunamadı!")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = FlightControlStation()
    ex.show()
    sys.exit(app.exec_())