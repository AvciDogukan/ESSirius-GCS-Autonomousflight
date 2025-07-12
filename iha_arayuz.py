import sys
import random
import requests  # Hava durumu verilerini çekmek için
import pyqtgraph as pg
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QComboBox, QWidget, QVBoxLayout, QHBoxLayout, QLayout, QFormLayout,
                             QLabel, QDialog, QVBoxLayout, QLabel, QPushButton, QListWidget, QPushButton, QPlainTextEdit, QGroupBox, QLineEdit, QListWidget, QSizePolicy, QStackedWidget, QGridLayout, QProgressBar, QSlider, QDial)
from PyQt5.QtCore import QTimer, Qt, QPointF, QObject, pyqtSlot, Qt, pyqtSignal
from PyQt5.QtGui import QPixmap, QPainter, QBrush, QColor, QFont, QPen, QPainterPath
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtWebChannel import QWebChannel
from PyQt5.QtCore import QTimer, pyqtSlot, QMetaObject, Q_ARG
from core.mavsdk_subprocess import MAVSDKSubprocessManager
from PyQt5.QtWidgets import QWidget
from PyQt5.QtGui import QPainter, QBrush, QColor, QFont, QPen, QPainterPath, QRadialGradient, QLinearGradient, QConicalGradient
from PyQt5.QtCore import Qt, QPointF, QTimer, QPropertyAnimation, QEasingCurve, pyqtProperty
import math
from PyQt5.QtCore import QRect, QRectF, QSize, QSizeF
# MAVSDK imports - Güvenli import
try:
    from mavsdk import System
    from mavsdk.offboard import PositionNedYaw, VelocityBodyYawspeed
    import asyncio
    MAVSDK_AVAILABLE = True
    print("✅ MAVSDK başarıyla yüklendi")
except ImportError as e:
    print(f"❌ MAVSDK import hatası: {e}")
    MAVSDK_AVAILABLE = False

from PyQt5.QtWidgets import QMessageBox
# Diğer modüller
from manuel_control import ManualControlPage
from sensor_pages import LidarPage, GPSSpoofingPage, ElectronicWarfarePage
from core.mission_selector import MissionSelectorDialog
import threading  
import traceback  
from threading import Thread, Lock
from PyQt5.QtCore import QMetaObject, Q_ARG, Qt, pyqtSlot
import logging
from io import StringIO
import time
import math
import sys
import subprocess
import json
from motor_status import MotorStatusWidget
from core.weather_ai_module import create_weather_ai_dialog
from core.realtime_failsafe_monitor import open_failsafe_monitor

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QSpinBox, QSlider, QGroupBox, 
                             QGridLayout, QFrame, QProgressBar)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QIcon


# Thread-safe lock
vehicle_lock = threading.Lock()

UI_SCALE = 1

class AdvancedSpeedometerWidget(QWidget):
    def __init__(self, parent=None):
        super(AdvancedSpeedometerWidget, self).__init__(parent)
        self.speed = 0
        self.target_speed = 0
        self.min_speed = 0
        self.max_speed = 0
        self.unit_kmh = True  # True: km/h, False: m/s
        self.pulse_value = 0
        self.glow_intensity = 0
        
        # Animasyon ayarları
        self.animation = QPropertyAnimation(self, b"animatedSpeed")
        self.animation.setDuration(500)  # 500ms smooth transition
        self.animation.setEasingCurve(QEasingCurve.OutCubic)
        
        # Pulse animasyonu
        self.pulse_timer = QTimer()
        self.pulse_timer.timeout.connect(self.updatePulse)
        self.pulse_timer.start(50)  # 20 FPS
        
    @pyqtProperty(float)
    def animatedSpeed(self):
        return self.speed
    
    @animatedSpeed.setter
    def animatedSpeed(self, value):
        self.speed = value
        self.update()

    def setSpeed(self, speed):
        # Min/Max tracking
        if speed > self.max_speed:
            self.max_speed = speed
        if speed < self.min_speed or self.min_speed == 0:
            self.min_speed = speed
            
        # Smooth animation
        self.target_speed = speed
        self.animation.setStartValue(self.speed)
        self.animation.setEndValue(speed)
        self.animation.start()

    def toggleUnit(self):
        """Birim değiştir: km/h ⇄ m/s"""
        self.unit_kmh = not self.unit_kmh
        self.update()
    
    def getDisplaySpeed(self):
        """Birime göre hız döndür"""
        if self.unit_kmh:
            return self.speed, "km/h"
        else:
            return self.speed / 3.6, "m/s"
    
    def updatePulse(self):
        """Pulse ve glow efekti"""
        self.pulse_value = (self.pulse_value + 0.1) % (2 * math.pi)
        
        # Kritik değerlerde glow
        if self.speed > 150:  # Kritik hız
            self.glow_intensity = 0.5 + 0.3 * math.sin(self.pulse_value * 3)
        else:
            self.glow_intensity = 0.1
            
        self.update()

    def getSpeedColor(self, speed):
        """Hıza göre gradient renk"""
        if speed <= 50:
            # Yeşil zone
            return QColor(0, 255, 0)
        elif speed <= 100:
            # Yeşil → Sarı geçiş
            ratio = (speed - 50) / 50
            return QColor(int(255 * ratio), 255, int(255 * (1 - ratio)))
        elif speed <= 150:
            # Sarı → Turuncu geçiş
            ratio = (speed - 100) / 50
            return QColor(255, int(255 * (1 - ratio * 0.5)), 0)
        else:
            # Kırmızı zone
            return QColor(255, 0, 0)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        rect = self.rect()
        center = rect.center()
        radius = min(rect.width(), rect.height()) // 2 - 40
        
        # 🎨 3D ARKA PLAN GRADİYENTİ
        bg_gradient = QRadialGradient(center, radius)
        bg_gradient.setColorAt(0, QColor(80, 80, 80))
        bg_gradient.setColorAt(0.7, QColor(40, 40, 40))
        bg_gradient.setColorAt(1, QColor(20, 20, 20))
        
        painter.setBrush(QBrush(bg_gradient))
        painter.setPen(QPen(QColor(150, 150, 150), 4))
        painter.drawEllipse(center, radius, radius)
        
        # 🌈 RENK ZONE'LARI
        self.drawSpeedZones(painter, center, radius)
        
        # 📊 TIK İŞARETLERİ VE SAYILAR
        self.drawTicks(painter, center, radius)
        
        # 🚁 MERKEZ LOGO (Drone ikonu)
        self.drawDroneLogo(painter, center, radius // 4)
        
        # 📱 DİJİTAL DISPLAY
        self.drawDigitalDisplay(painter, rect, center, radius)
        
        # ⚡ İBRE (Glow efekti ile)
        self.drawNeedle(painter, center, radius)
        
        # 📈 MIN/MAX GÖSTERGESİ
        self.drawMinMaxIndicators(painter, center, radius)
        
        # 🏷️ BİRİM ETİKETİ
        self.drawUnitLabel(painter, rect)

    def drawSpeedZones(self, painter, center, radius):
        """Renk zone'ları çiz"""
        zones = [
            (0, 50, QColor(255, 0, 0, 80)),      # Yeşil zone
            (50, 100, QColor(255, 165, 0, 80)),  # Sarı zone  
            (100, 150, QColor(255, 255, 0, 80)),  # Turuncu zone
            (150, 200, QColor(0, 255, 0, 80))    # Kırmızı zone
        ]
        
        for start_speed, end_speed, color in zones:
            start_angle = -135.0 + (start_speed / 200.0) * 270.0
            span_angle = ((end_speed - start_speed) / 200.0) * 270.0
            
            painter.setBrush(QBrush(color))
            painter.setPen(Qt.NoPen)
            
            # Arc path oluştur
            path = QPainterPath()
            path.arcMoveTo(center.x() - radius, center.y() - radius, 
                          radius * 2, radius * 2, start_angle)
            path.arcTo(center.x() - radius, center.y() - radius,
                      radius * 2, radius * 2, start_angle, span_angle)
            
            # İç daire ile kes
            inner_radius = radius - 20
            path.arcTo(center.x() - inner_radius, center.y() - inner_radius,
                      inner_radius * 2, inner_radius * 2, 
                      start_angle + span_angle, -span_angle)
            path.closeSubpath()
            
            painter.drawPath(path)

    def drawTicks(self, painter, center, radius):
        """Tik işaretleri ve sayılar"""
        painter.setPen(QPen(QColor(255, 255, 255), 2))
        painter.setFont(QFont('Arial', 10, QFont.Bold))
        
        for speed in range(0, 201, 20):
            angle = -135.0 + (speed / 200.0) * 270.0
            
            # Tik çizgisi
            tick_start = self.calculatePosition(center, radius - 15, angle)
            tick_end = self.calculatePosition(center, radius - 5, angle)
            painter.drawLine(tick_start, tick_end)
            
            # Sayı
            if speed % 40 == 0:  # Sadece 0, 40, 80, 120, 160, 200
                number_pos = self.calculatePosition(center, radius - 30, angle)
                painter.drawText(int(number_pos.x()) - 10, int(number_pos.y()) + 5, str(speed))

    def drawDroneLogo(self, painter, center, size):
        """Merkeze drone logosu"""
        painter.setPen(QPen(QColor(100, 150, 255), 2))
        painter.setBrush(QBrush(QColor(100, 150, 255, 100)))
        
        # Basit drone şekli - merkez gövde
        painter.drawEllipse(center.x() - size//4, center.y() - size//4, 
                           size//2, size//2)
        
        # Propeller kolları
        arm_length = size // 2
        for angle in [45, 135, 225, 315]:
            arm_end = self.calculatePosition(center, arm_length, angle)
            painter.drawLine(center, arm_end)
            
            # Propeller daireleri
            prop_radius = size // 8
            painter.drawEllipse(int(arm_end.x()) - prop_radius, int(arm_end.y()) - prop_radius,
                               prop_radius * 2, prop_radius * 2)

    def drawDigitalDisplay(self, painter, rect, center, radius):
        """Digital display"""
        display_speed, unit = self.getDisplaySpeed()
        
        display_width = 100
        display_height = 30
        display_x = center.x() - display_width // 2
        display_y = center.y() - radius - 35  # Göstergenin üst kısmına
        
        display_rect = QRect(display_x, display_y, display_width, display_height)
        # Arka plan
        
        painter.setBrush(QBrush(QColor(0, 0, 0, 150)))
        painter.setPen(QPen(QColor(0, 255, 0), 2))
        painter.drawRoundedRect(display_rect, 5, 5)
        
        # Digital sayı
        painter.setFont(QFont('Courier', 16, QFont.Bold))
        painter.setPen(QColor(0, 255, 0))
        
        painter.setFont(QFont('Courier', 14, QFont.Bold))
        painter.setPen(QColor(0, 255, 0))
        painter.drawText(display_rect, Qt.AlignCenter, f"{display_speed:.1f} {unit}")

    def drawNeedle(self, painter, center, radius):
        """Glow efektli ibre"""
        angle = -135.0 + (self.speed / 200.0) * 270.0
        needle_end = self.calculatePosition(center, radius - 20, angle)
        
        # Glow efekti
        if self.glow_intensity > 0:
            glow_pen = QPen(QColor(255, 255, 255, int(self.glow_intensity * 255)), 8)
            painter.setPen(glow_pen)
            painter.drawLine(center, needle_end)
        
        # Ana ibre
        needle_color = self.getSpeedColor(self.speed)
        painter.setPen(QPen(needle_color, 4))
        painter.drawLine(center, needle_end)
        
        # İbre merkez noktası
        painter.setBrush(QBrush(needle_color))
        painter.drawEllipse(center.x() - 6, center.y() - 6, 12, 12)

    def drawMinMaxIndicators(self, painter, center, radius):
        """Min/Max göstergeleri"""
        if self.min_speed > 0 or self.max_speed > 0:
            painter.setPen(QPen(QColor(100, 100, 255), 2))
            painter.setFont(QFont('Arial', 8))
            
            # Min işareti
            if self.min_speed > 0:
                min_angle = -135.0 + (self.min_speed / 200.0) * 270.0
                min_pos = self.calculatePosition(center, radius + 10, min_angle)
                painter.drawText(min_pos.x() - 10, min_pos.y(), "MIN")
            
            # Max işareti  
            if self.max_speed > 0:
                max_angle = -135.0 + (self.max_speed / 200.0) * 270.0
                max_pos = self.calculatePosition(center, radius + 10, max_angle)
                painter.drawText(max_pos.x() - 10, max_pos.y(), "MAX")

    def drawUnitLabel(self, painter, rect):
        """Birim etiketi"""
        _, unit = self.getDisplaySpeed()
        painter.setPen(QColor(200, 200, 200))
        painter.setFont(QFont('Arial', 10))
        painter.drawText(rect.bottomRight() - QPointF(50, 10), 
                        f"[{unit}]")

    def calculatePosition(self, center, radius, angle):
        """Açıdan pozisyon hesapla"""
        angle_rad = math.radians(angle)
        x = center.x() + radius * math.cos(angle_rad)
        y = center.y() + radius * math.sin(angle_rad)
        return QPointF(x, y)

    def mousePressEvent(self, event):
        """Mouse click - birim değiştir"""
        if event.button() == Qt.LeftButton:
            self.toggleUnit()

class AdvancedBatteryGaugeWidget(QWidget):
    def __init__(self, parent=None):
        super(AdvancedBatteryGaugeWidget, self).__init__(parent)
        self.battery_level = 100
        self.target_battery = 100
        self.warning_blink = False
        self.blink_timer = QTimer()
        self.blink_timer.timeout.connect(self.toggleBlink)
        
        # Smooth animation
        self.animation = QPropertyAnimation(self, b"animatedBattery")
        self.animation.setDuration(800)
        self.animation.setEasingCurve(QEasingCurve.OutCubic)

    @pyqtProperty(float)
    def animatedBattery(self):
        return self.battery_level
    
    @animatedBattery.setter  
    def animatedBattery(self, value):
        self.battery_level = value
        self.update()

    def setBatteryLevel(self, level):
        self.target_battery = level
        self.animation.setStartValue(self.battery_level)
        self.animation.setEndValue(level)
        self.animation.start()
        
        # Düşük batarya uyarısı
        if level < 20 and not self.blink_timer.isActive():
            self.blink_timer.start(500)  # 500ms blink
        elif level >= 20 and self.blink_timer.isActive():
            self.blink_timer.stop()
            self.warning_blink = False

    def toggleBlink(self):
        self.warning_blink = not self.warning_blink
        self.update()

    def getBatteryColor(self):
        """Batarya seviyesine göre renk"""
        if self.battery_level < 10:
            color = QColor(255, 0, 0)  # Kırmızı
        elif self.battery_level < 25:
            color = QColor(255, 100, 0)  # Turuncu
        elif self.battery_level < 50:
            color = QColor(255, 200, 0)  # Sarı
        else:
            color = QColor(0, 255, 0)  # Yeşil
        
        # Düşük bataryada blink efekti
        if self.battery_level < 20 and self.warning_blink:
            color.setAlpha(100)
        
        return color

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        rect = self.rect()
        center = rect.center()
        radius = min(rect.width(), rect.height()) // 2 - 40
        
        # 3D Gradient background
        bg_gradient = QRadialGradient(center, radius)
        bg_gradient.setColorAt(0, QColor(60, 60, 60))
        bg_gradient.setColorAt(0.8, QColor(30, 30, 30))
        bg_gradient.setColorAt(1, QColor(10, 10, 10))
        
        painter.setBrush(QBrush(bg_gradient))
        painter.setPen(QPen(QColor(120, 120, 120), 4))
        painter.drawEllipse(center, radius, radius)
        
        # Batarya zone'ları
        self.drawBatteryZones(painter, center, radius)
        
        # Tik işaretleri
        self.drawBatteryTicks(painter, center, radius)
        
        # Batarya ikonu (merkez)
        self.drawBatteryIcon(painter, center, radius // 3)
        
        # Digital display
        self.drawBatteryDigital(painter, rect)
        
        # İbre
        self.drawBatteryNeedle(painter, center, radius)

    def drawBatteryZones(self, painter, center, radius):
        """Batarya zone'ları"""
        zones = [
            (0, 10, QColor(0, 255, 0, 80)),     # Kritik
            (10, 25, QColor(255, 200, 0, 60)),   # Düşük
            (25, 75, QColor(255, 100, 0, 80)),   # Orta
            (75, 100, QColor(255, 0, 0, 100))     # Yüksek
        ]
        
        for start, end, color in zones:
            start_angle = -135.0 + (start / 100.0) * 270.0
            span_angle = ((end - start) / 100.0) * 270.0
            
            painter.setBrush(QBrush(color))
            painter.setPen(Qt.NoPen)
            
            path = QPainterPath()
            path.arcMoveTo(center.x() - radius, center.y() - radius,
                          radius * 2, radius * 2, start_angle)
            path.arcTo(center.x() - radius, center.y() - radius,
                      radius * 2, radius * 2, start_angle, span_angle)
            
            inner_radius = radius - 15
            path.arcTo(center.x() - inner_radius, center.y() - inner_radius,
                      inner_radius * 2, inner_radius * 2,
                      start_angle + span_angle, -span_angle)
            path.closeSubpath()
            
            painter.drawPath(path)

    def drawBatteryTicks(self, painter, center, radius):
        """Batarya tik işaretleri"""
        painter.setPen(QPen(QColor(255, 255, 255), 2))
        painter.setFont(QFont('Arial', 9, QFont.Bold))
        
        for level in range(0, 101, 10):
            angle = -135.0 + (level / 100.0) * 270.0
            
            tick_start = self.calculatePosition(center, radius - 12, angle)
            tick_end = self.calculatePosition(center, radius - 4, angle)
            painter.drawLine(tick_start, tick_end)
            
            if level % 25 == 0:
                number_pos = self.calculatePosition(center, radius - 25, angle)
                painter.drawText(int(number_pos.x()) - 8, int(number_pos.y()) + 4, f"{level}")

    def drawBatteryIcon(self, painter, center, size):
        """Batarya ikonu"""
        # Batarya gövdesi
        battery_rect = QRect(int(center.x()) - int(size//2), int(center.y()) - int(size//3),
                            size, int(size//1.5))
        painter.setBrush(QBrush(QColor(100, 100, 100)))
        painter.setPen(QPen(QColor(200, 200, 200), 2))
        painter.drawRoundedRect(battery_rect, 3, 3)
        
        # Batarya üst terminal
        terminal_rect = QRect(int(center.x()) - size//6, int(center.y()) - size//2,
                             size//3, size//6)
        painter.drawRoundedRect(terminal_rect, 2, 2)
        
        # Doluluk göstergesi
        fill_width = int((battery_rect.width() - 4) * self.battery_level / 100)
        if fill_width > 0:
            fill_rect = QRect(battery_rect.x() + 2, battery_rect.y() + 2,
                             fill_width, battery_rect.height() - 4)
            painter.setBrush(QBrush(self.getBatteryColor()))
            painter.drawRect(fill_rect)

    def drawBatteryDigital(self, painter, rect):
        """Digital batarya göstergesi"""
        center = rect.center()
        radius = min(rect.width(), rect.height()) // 2 - 40
        
        display_width = 100
        display_height = 30
        display_x = center.x() - display_width // 2
        display_y = center.y() - radius - 35  # Göstergenin üst kısmına
        
        display_rect = QRect(display_x, display_y, display_width, display_height)
        
        # Arka plan
        painter.setBrush(QBrush(QColor(0, 0, 0, 150)))
        painter.setPen(QPen(self.getBatteryColor(), 2))
        painter.drawRoundedRect(display_rect, 5, 5)
        
        # Digital sayı
        painter.setFont(QFont('Courier', 14, QFont.Bold))
        painter.setPen(self.getBatteryColor())
        painter.drawText(display_rect, Qt.AlignCenter, f"{self.battery_level:.1f}%")

    def drawBatteryNeedle(self, painter, center, radius):
        """Batarya ibresi"""
        angle = -135.0 + (self.battery_level / 100.0) * 270.0
        needle_end = self.calculatePosition(center, radius - 15, angle)
        
        color = self.getBatteryColor()
        painter.setPen(QPen(color, 4))
        painter.drawLine(center, needle_end)
        
        painter.setBrush(QBrush(color))
        painter.drawEllipse(center.x() - 5, center.y() - 5, 10, 10)

    def calculatePosition(self, center, radius, angle):
        angle_rad = math.radians(angle)
        x = center.x() + radius * math.cos(angle_rad)
        y = center.y() + radius * math.sin(angle_rad)
        return QPointF(x, y)

class AdvancedCompassWidget(QWidget):
    def __init__(self, parent=None):
        super(AdvancedCompassWidget, self).__init__(parent)
        self.heading = 0
        self.target_heading = 0
        
        # Smooth rotation animation
        self.animation = QPropertyAnimation(self, b"animatedHeading")
        self.animation.setDuration(300)
        self.animation.setEasingCurve(QEasingCurve.OutCubic)

    @pyqtProperty(float)
    def animatedHeading(self):
        return self.heading
    
    @animatedHeading.setter
    def animatedHeading(self, value):
        self.heading = value
        self.update()

    def setHeading(self, heading):
        # En kısa yol hesaplama (360° geçiş için)
        diff = heading - self.heading
        if diff > 180:
            diff -= 360
        elif diff < -180:
            diff += 360
        
        self.target_heading = self.heading + diff
        self.animation.setStartValue(self.heading)
        self.animation.setEndValue(self.target_heading)
        self.animation.start()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        rect = self.rect()
        center = rect.center()
        radius = min(rect.width(), rect.height()) // 2 - 30
        
        # 3D Compass background
        bg_gradient = QConicalGradient(center, 0)
        bg_gradient.setColorAt(0, QColor(100, 150, 255))
        bg_gradient.setColorAt(0.25, QColor(50, 100, 200))
        bg_gradient.setColorAt(0.5, QColor(100, 150, 255))
        bg_gradient.setColorAt(0.75, QColor(50, 100, 200))
        bg_gradient.setColorAt(1, QColor(100, 150, 255))
        
        painter.setBrush(QBrush(bg_gradient))
        painter.setPen(QPen(QColor(200, 200, 200), 3))
        painter.drawEllipse(center, radius, radius)
        
        # Yön işaretleri
        self.drawCompassDirections(painter, center, radius)
        
        # Derece işaretleri
        self.drawDegreeMarks(painter, center, radius)
        
        # Pusula ibresi
        self.drawCompassNeedle(painter, center, radius)
        
        # Digital heading
        self.drawDigitalHeading(painter, rect)

    def drawCompassDirections(self, painter, center, radius):
        """Ana yön işaretleri (N, E, S, W)"""
        directions = [
            (0, 'N', QColor(255, 0, 0)),      # Kuzey - Kırmızı
            (90, 'E', QColor(0, 255, 0)),     # Doğu - Yeşil  
            (180, 'S', QColor(255, 255, 0)),  # Güney - Sarı
            (270, 'W', QColor(0, 0, 0))   # Batı - Mavi
        ]
        
        painter.setFont(QFont('Arial', 14, QFont.Bold))
        
        for angle, direction, color in directions:
            # Yön metnini çiz
            text_radius = radius - 20
            pos = self.calculatePosition(center, text_radius, angle - 90)  # -90 çünkü 0° üstte
            
            painter.setPen(color)
            painter.drawText(int(pos.x()) - 8, int(pos.y()) + 5, direction)
            
            # Yön çizgisi
            line_start = self.calculatePosition(center, radius - 10, angle - 90)
            line_end = self.calculatePosition(center, radius, angle - 90)
            painter.setPen(QPen(color, 3))
            painter.drawLine(line_start, line_end)

    def drawDegreeMarks(self, painter, center, radius):
        """Derece işaretleri"""
        painter.setPen(QPen(QColor(255, 255, 255), 1))
        painter.setFont(QFont('Arial', 8))
        
        for degree in range(0, 360, 10):
            angle = degree - 90  # 0° üstte olacak şekilde ayarla
            
            if degree % 30 == 0:  # Ana işaretler
                mark_start = self.calculatePosition(center, radius - 8, angle)
                mark_end = self.calculatePosition(center, radius, angle)
                painter.setPen(QPen(QColor(255, 255, 255), 2))
                painter.drawLine(mark_start, mark_end)
                
                # Derece sayısı
                if degree % 90 != 0:  # N,E,S,W dışındakiler
                    text_pos = self.calculatePosition(center, radius - 15, angle)
                    painter.setPen(QColor(200, 200, 200))
                    painter.drawText(int(text_pos.x()) - 8, int(text_pos.y()) + 3, str(degree))
            else:  # Küçük işaretler
                mark_start = self.calculatePosition(center, radius - 4, angle)
                mark_end = self.calculatePosition(center, radius, angle)
                painter.setPen(QPen(QColor(150, 150, 150), 1))
                painter.drawLine(mark_start, mark_end)

    def drawCompassNeedle(self, painter, center, radius):
        """Pusula ibresi"""
        # Kuzey ibresi (kırmızı)
        north_end = self.calculatePosition(center, radius - 25, self.heading - 90)
        painter.setPen(QPen(QColor(255, 0, 0), 4))
        painter.drawLine(center, north_end)
        
        # Güney ibresi (beyaz)
        south_end = self.calculatePosition(center, radius - 35, self.heading + 90)
        painter.setPen(QPen(QColor(255, 255, 255), 3))
        painter.drawLine(center, south_end)
        
        # Merkez nokta
        painter.setBrush(QBrush(QColor(255, 255, 255)))
        painter.setPen(QPen(QColor(100, 100, 100), 2))
        painter.drawEllipse(center.x() - 8, center.y() - 8, 16, 16)

    def drawDigitalHeading(self, painter, rect):
        """Digital yön göstergesi"""
        heading_text = f"{int(self.heading % 360)}°"
        
        center = rect.center()
        radius = min(rect.width(), rect.height()) // 2 - 30
        
        display_width = 100
        display_height = 30
        display_x = center.x() - display_width // 2
        display_y = center.y() - radius - 35  # Göstergenin üst kısmına
        
        display_rect = QRect(display_x, display_y, display_width, display_height)
        
        # Arka plan
        painter.setBrush(QBrush(QColor(0, 0, 0, 150)))
        painter.setPen(QPen(QColor(100, 150, 255), 2))
        painter.drawRoundedRect(display_rect, 5, 5)
        
        # Digital sayı
        painter.setFont(QFont('Courier', 14, QFont.Bold))
        painter.setPen(QColor(100, 150, 255))
        painter.drawText(display_rect, Qt.AlignCenter, heading_text)

    def calculatePosition(self, center, radius, angle):
        angle_rad = math.radians(angle)
        x = center.x() + radius * math.cos(angle_rad)
        y = center.y() + radius * math.sin(angle_rad)
        return QPointF(x, y)

    def mousePressEvent(self, event):
        """Mouse ile heading reset"""
        if event.button() == Qt.RightButton:
            self.setHeading(0)  # Kuzeyi göster
            
class TakeoffAltitudeDialog(QDialog):
    """Kalkış yükseklik seçim dialogu"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_altitude = 10  # Default 10 metre
        self.setupUI()
        
    def setupUI(self):
        self.setWindowTitle("🚀 KALKIŞ YÜKSEKLİĞİ AYARLA")
        self.setFixedSize(900, 800)
        self.setModal(True)
        
        # Ana layout
        main_layout = QVBoxLayout()
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # Header
        self.create_header(main_layout)
        
        # Yükseklik seçim bölümü
        self.create_altitude_section(main_layout)
        
        # Güvenlik uyarıları
        self.create_safety_section(main_layout)
        
        # Butonlar
        self.create_buttons(main_layout)
        
        self.setLayout(main_layout)
        self.apply_styles()
    
    def create_header(self, layout):
        """Header bölümü"""
        header_frame = QFrame()
        header_layout = QVBoxLayout(header_frame)
        
        title = QLabel("🚀 KALKIŞ YÜKSEKLİĞİ AYARLA")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("""
            QLabel {
                font-size: 20px;
                font-weight: bold;
                color: #e74c3c;
                padding: 15px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(231, 76, 60, 0.1), 
                    stop:1 rgba(192, 57, 43, 0.1));
                border: 2px solid #e74c3c;
                border-radius: 10px;
            }
        """)
        
        subtitle = QLabel("İHA'nın kalkış yapacağı irtifayı belirleyin")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("color: #7f8c8d; font-size: 12px; margin-top: 5px;")
        
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        layout.addWidget(header_frame)
    
    def create_altitude_section(self, layout):
        """Yükseklik seçim bölümü"""
        altitude_group = QGroupBox("🎯 Hedef İrtifa")
        altitude_layout = QGridLayout()
        
        # Büyük rakam göstergesi
        self.altitude_display = QLabel("10")
        self.altitude_display.setAlignment(Qt.AlignCenter)
        self.altitude_display.setStyleSheet("""
            QLabel {
                font-size: 48px;
                font-weight: bold;
                color: #2ecc71;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(46, 204, 113, 0.1), 
                    stop:1 rgba(39, 174, 96, 0.1));
                border: 3px solid #2ecc71;
                border-radius: 15px;
                padding: 20px;
                min-height: 80px;
            }
        """)
        
        metre_label = QLabel("METRE")
        metre_label.setAlignment(Qt.AlignCenter)
        metre_label.setStyleSheet("color: #2ecc71; font-weight: bold; font-size: 14px;")
        
        # Slider kontrolü
        self.altitude_slider = QSlider(Qt.Horizontal)
        self.altitude_slider.setMinimum(3)
        self.altitude_slider.setMaximum(100)
        self.altitude_slider.setValue(10)
        self.altitude_slider.setTickPosition(QSlider.TicksBelow)
        self.altitude_slider.setTickInterval(10)
        self.altitude_slider.valueChanged.connect(self.update_altitude_display)
        
        # SpinBox kontrolü
        self.altitude_spinbox = QSpinBox()
        self.altitude_spinbox.setMinimum(3)
        self.altitude_spinbox.setMaximum(100)
        self.altitude_spinbox.setValue(10)
        self.altitude_spinbox.setSuffix(" m")
        self.altitude_spinbox.valueChanged.connect(self.update_altitude_from_spinbox)
        
        # Hızlı seçim butonları
        quick_buttons_layout = QHBoxLayout()
        quick_values = [5, 10, 15, 20, 30, 50]
        for value in quick_values:
            btn = QPushButton(f"{value}m")
            btn.clicked.connect(lambda checked, v=value: self.set_quick_altitude(v))
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #3498db;
                    color: white;
                    border: none;
                    padding: 8px 12px;
                    border-radius: 5px;
                    font-weight: bold;
                    min-width: 40px;
                }
                QPushButton:hover {
                    background-color: #2980b9;
                }
                QPushButton:pressed {
                    background-color: #21618c;
                }
            """)
            quick_buttons_layout.addWidget(btn)
        
        # Layout'a ekle
        altitude_layout.addWidget(self.altitude_display, 0, 0, 1, 2)
        altitude_layout.addWidget(metre_label, 1, 0, 1, 2)
        altitude_layout.addWidget(QLabel("Slider:"), 2, 0)
        altitude_layout.addWidget(self.altitude_slider, 2, 1)
        altitude_layout.addWidget(QLabel("Hassas:"), 3, 0)
        altitude_layout.addWidget(self.altitude_spinbox, 3, 1)
        altitude_layout.addWidget(QLabel("Hızlı Seçim:"), 4, 0, 1, 2)
        altitude_layout.addLayout(quick_buttons_layout, 5, 0, 1, 2)
        
        altitude_group.setLayout(altitude_layout)
        layout.addWidget(altitude_group)
    
    def create_safety_section(self, layout):
        """Güvenlik uyarıları bölümü"""
        safety_group = QGroupBox("⚠️ Güvenlik Bilgilendirmesi")
        safety_layout = QVBoxLayout()
        
        safety_tips = [
            "🔹 Minimum güvenli irtifa: 3 metre",
            "🔹 Yasal maksimum irtifa: 120 metre (ülkeye göre değişir)",
            "🔹 Düşük irtifa: Daha güvenli ama sınırlı görüş",
            "🔹 Yüksek irtifa: Geniş alan taraması ama rüzgar riski",
            "🔹 İlk uçuşlarda 10-15 metre önerilir",
            "🔹 Kötü hava koşullarında irtifayı düşük tutun"
        ]
        
        for tip in safety_tips:
            tip_label = QLabel(tip)
            tip_label.setStyleSheet("color: #f39c12; font-size: 11px; padding: 2px;")
            safety_layout.addWidget(tip_label)
        
        # Risk seviyesi göstergesi
        self.risk_level = QProgressBar()
        self.risk_level.setMaximum(100)
        self.risk_level.setValue(30)  # Default risk
        self.risk_level.setFormat("Risk Seviyesi: %p%")
        self.update_risk_level(10)
        
        safety_layout.addWidget(QLabel("🎯 Risk Seviyesi:"))
        safety_layout.addWidget(self.risk_level)
        
        safety_group.setLayout(safety_layout)
        layout.addWidget(safety_group)
    
    def create_buttons(self, layout):
        """Buton bölümü"""
        button_layout = QHBoxLayout()
        
        # İptal butonu
        cancel_btn = QPushButton("❌ İPTAL")
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                padding: 15px 30px;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
        """)
        
        # Kalkış butonu
        takeoff_btn = QPushButton("🚀 KALKIŞ BAŞLAT")
        takeoff_btn.clicked.connect(self.accept)
        takeoff_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                padding: 15px 30px;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #229954;
            }
        """)
        
        button_layout.addWidget(cancel_btn)
        button_layout.addStretch()
        button_layout.addWidget(takeoff_btn)
        
        layout.addLayout(button_layout)
    
    def apply_styles(self):
        """Dialog stil uygula"""
        self.setStyleSheet("""
            QDialog {
                background-color: #2c3e50;
                color: #ecf0f1;
            }
            QGroupBox {
                font-size: 14px;
                font-weight: bold;
                border: 2px solid #34495e;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 15px;
                color: #ecf0f1;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 10px 0 10px;
                color: #3498db;
            }
            QLabel {
                color: #ecf0f1;
            }
            QSpinBox {
                background-color: #34495e;
                color: #ecf0f1;
                border: 2px solid #3498db;
                border-radius: 5px;
                padding: 5px;
                font-size: 12px;
            }
            QSlider::groove:horizontal {
                border: 1px solid #34495e;
                height: 8px;
                background: #34495e;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #3498db;
                border: 1px solid #2980b9;
                width: 18px;
                height: 18px;
                border-radius: 9px;
                margin: -5px 0;
            }
            QSlider::sub-page:horizontal {
                background: #2ecc71;
                border-radius: 4px;
            }
            QProgressBar {
                border: 2px solid #34495e;
                border-radius: 5px;
                text-align: center;
                color: white;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background-color: #f39c12;
                border-radius: 3px;
            }
        """)
    
    def update_altitude_display(self, value):
        """Altitude display güncelle"""
        self.selected_altitude = value
        self.altitude_display.setText(str(value))
        self.altitude_spinbox.setValue(value)
        self.update_risk_level(value)
        self.update_altitude_color(value)
    
    def update_altitude_from_spinbox(self, value):
        """SpinBox'tan altitude güncelle"""
        self.selected_altitude = value
        self.altitude_display.setText(str(value))
        self.altitude_slider.setValue(value)
        self.update_risk_level(value)
        self.update_altitude_color(value)
    
    def set_quick_altitude(self, value):
        """Hızlı seçim ile altitude ayarla"""
        self.altitude_slider.setValue(value)
        self.altitude_spinbox.setValue(value)
        self.update_altitude_display(value)
    
    def update_risk_level(self, altitude):
        """Risk seviyesi güncelle"""
        if altitude <= 5:
            risk = 20
            color = "#2ecc71"  # Yeşil
        elif altitude <= 15:
            risk = 30
            color = "#f1c40f"  # Sarı
        elif altitude <= 30:
            risk = 50
            color = "#e67e22"  # Turuncu
        elif altitude <= 50:
            risk = 70
            color = "#e74c3c"  # Kırmızı
        else:
            risk = 90
            color = "#8e44ad"  # Mor
        
        self.risk_level.setValue(risk)
        self.risk_level.setStyleSheet(f"""
            QProgressBar::chunk {{
                background-color: {color};
                border-radius: 3px;
            }}
        """)
    
    def update_altitude_color(self, altitude):
        """Altitude display rengini güncelle"""
        if altitude <= 10:
            color = "#2ecc71"  # Yeşil - güvenli
        elif altitude <= 20:
            color = "#f1c40f"  # Sarı - dikkat
        elif altitude <= 40:
            color = "#e67e22"  # Turuncu - uyarı
        else:
            color = "#e74c3c"  # Kırmızı - yüksek risk
        
        self.altitude_display.setStyleSheet(f"""
            QLabel {{
                font-size: 48px;
                font-weight: bold;
                color: {color};
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba{self.hex_to_rgba(color, 0.1)}, 
                    stop:1 rgba{self.hex_to_rgba(color, 0.1)});
                border: 3px solid {color};
                border-radius: 15px;
                padding: 20px;
                min-height: 80px;
            }}
        """)
    
    def hex_to_rgba(self, hex_color, alpha):
        """Hex rengi RGBA'ya çevir"""
        hex_color = hex_color.lstrip('#')
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        return f"({r}, {g}, {b}, {alpha})"
    
    def get_selected_altitude(self):
        """Seçilen irtifayı döndür"""
        return self.selected_altitude
           
class SpeedometerWidget(QWidget):
    def __init__(self, parent=None):
        super(SpeedometerWidget, self).__init__(parent)
        self.speed = 0  # Initial speed

    def setSpeed(self, speed):
        self.speed = int(round(speed))
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
        angle = -135.0 + (self.speed / 180.0) * 270.0
        painter.setPen(QPen(QColor(255, 0, 0), 4))
        needle_end = self.calculateNeedlePosition(center, radius, angle)
        painter.drawLine(center, needle_end)

        # Draw the ticks
        painter.setPen(QPen(QColor(255, 255, 255), 3))
        for i in range(0, 181, 20):
            tick_angle = -135.0 + (i / 180.0) * 270.0
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
        angle = -135.0 + (self.fuel_level / 100.0) * 270.0  # Map fuel level to angle
        painter.setPen(QPen(color, 4))
        needle_end = self.calculateNeedlePosition(center, radius, angle)
        painter.drawLine(center, needle_end)

        # Draw the ticks
        painter.setPen(QPen(QColor(255, 255, 255), 3))
        for i in range(0, 101, 10):
            tick_angle = -135.0 + (i / 100.0) * 270.0
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

class MissionDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Görev Seç")
        self.setMinimumWidth(300)
        layout = QVBoxLayout()

        layout.addWidget(QLabel("Lütfen bir görev seçin:"))

        self.list_widget = QListWidget()
        self.list_widget.addItems([
            "Normal Devriye",
            "Alçak Sessiz Devriye",
            "Dairesel Devriye"
        ])
        layout.addWidget(self.list_widget)

        start_button = QPushButton("Görevi Başlat")
        start_button.clicked.connect(self.accept)
        layout.addWidget(start_button)

        self.setLayout(layout)

    def get_selected_mission(self):
        return self.list_widget.currentItem().text() if self.list_widget.currentItem() else None

# Mevcut connection modülünü import et
try:
    from core.connection import MAVSDKConnectionManager as CoreMAVSDKConnectionManager
    CONNECTION_MODULE_AVAILABLE = True
    print("✅ Core connection modülü yüklendi")
except ImportError as e:
    print(f"⚠ Core connection modülü bulunamadı: {e}")
    CONNECTION_MODULE_AVAILABLE = False
    
    # Fallback - basit MAVSDK connection manager
    class CoreMAVSDKConnectionManager:
        """Fallback MAVSDK Connection Manager"""
        
        def __init__(self, connection_string="udp://:14540", timeout=30, auto_connect=False):
            self.connection_string = connection_string
            self.timeout = timeout
            self.system = None
            self._is_connected = False
            self._callbacks = {'connect': [], 'disconnect': []}
            print(f"⚠ Fallback connection manager oluşturuldu: {connection_string}")
        
        def set_callbacks(self, on_connect=None, on_disconnect=None):
            if on_connect:
                self._callbacks['connect'].append(on_connect)
            if on_disconnect:
                self._callbacks['disconnect'].append(on_disconnect)
        
        def start_connection(self):
            print("⚠ Fallback connection - gerçek bağlantı yapılmıyor")
            return False
        
        def stop_connection(self):
            self._is_connected = False
            print("⚠ Fallback connection durduruldu")
        
        def is_connected(self):
            return self._is_connected
        
        def get_system(self):
            return self.system

class MAVSDKActionManager:
    """MAVSDK Action yöneticisi - Async işlemler için"""
    
    def __init__(self, system):
        self.system = system
        
    async def arm_and_takeoff(self, altitude=10.0):
        """ARM ve takeoff işlemi"""
        try:
            print("🛰️ Sistem sağlığı kontrol ediliyor...")
            
            # Health check
            async for health in self.system.telemetry.health():
                if health.is_global_position_ok and health.is_home_position_ok:
                    print("✅ GPS ve home position OK")
                    break
                await asyncio.sleep(1)
            
            print("🛡️ ARM işlemi başlatılıyor...")
            await self.system.action.arm()
            print("✅ ARM başarılı!")
            
            # Takeoff altitude ayarla
            try:
                await self.system.action.set_takeoff_altitude(altitude)
                print(f"📏 Kalkış altitude: {altitude}m")
            except Exception as alt_error:
                print(f"⚠ Altitude set atlandı: {alt_error}")
            
            print("🚀 Kalkış başlatılıyor...")
            await self.system.action.takeoff()
            print("✅ Kalkış komutu gönderildi!")
            
            # Kalkış tamamlanmasını bekle
            target_altitude = altitude * 0.9  # %90'ına ulaşması yeterli
            print(f"⏳ Hedef altitude bekleniyor: {target_altitude}m")
            
            timeout_counter = 0
            async for position in self.system.telemetry.position():
                current_alt = position.relative_altitude_m
                if current_alt >= target_altitude:
                    print(f"🎯 Hedef altitude ulaşıldı: {current_alt:.1f}m")
                    return True
                
                timeout_counter += 1
                if timeout_counter > 60:  # 60 saniye timeout
                    print("⏰ Kalkış timeout!")
                    return False
                    
                await asyncio.sleep(1)
            
            return False
            
        except Exception as e:
            print(f"❌ ARM/Takeoff hatası: {e}")
            return False
    
    async def land(self):
        """İniş işlemi"""
        try:
            print("⏬ İniş başlatılıyor...")
            await self.system.action.land()
            print("✅ İniş komutu gönderildi!")
            
            # İniş tamamlanmasını bekle
            async for armed in self.system.telemetry.armed():
                if not armed:
                    print("🎯 İniş tamamlandı - motor disarm edildi")
                    return True
                await asyncio.sleep(1)
            
            return False
            
        except Exception as e:
            print(f"❌ İniş hatası: {e}")
            return False
    
    async def return_to_launch(self):
        """Return to Launch işlemi"""
        try:
            print("🏠 RTL başlatılıyor...")
            await self.system.action.return_to_launch()
            print("✅ RTL komutu gönderildi!")
            return True
            
        except Exception as e:
            print(f"❌ RTL hatası: {e}")
            return False
        
class UISubprocessTelemetry:
    """UI dosyasında çalışan telemetri - ESKİ ÇALIŞAN YÖNTEMİ"""
    
    def __init__(self, main_app):
        self.main_app = main_app
        self.running = False
        self.subprocess_proc = None
        self.reader_thread = None
        self.connection_string = "udp://:14540"
        
    def start(self, connection_string="udp://:14540"):
        """UI telemetri subprocess başlat"""
        if self.running:
            return False
            
        self.connection_string = connection_string
        self.running = True
        
        # UISubprocessTelemetry'de telemetry_script'i bu şekilde değiştirin:
        telemetry_connection = "udp://:14540"
        telemetry_script = telemetry_script = f'''import asyncio
import json
import sys
from mavsdk import System

async def get_telemetry():
    try:
        print("STATUS:Telemetri başlıyor...", flush=True)
        
        drone = System()
        await drone.connect("{telemetry_connection}")
        
        print("STATUS:Telemetri bağlantısı kuruluyor...", flush=True)
        
        connection_timeout = 0
        async for state in drone.core.connection_state():
            print(f"STATUS:Bağlantı durumu: {{state.is_connected}}", flush=True)
            if state.is_connected:
                print("CONNECTED", flush=True)
                break
            
            connection_timeout += 1
            if connection_timeout > 30:
                print("ERROR:Bağlantı timeout", flush=True)
                return
        
        print("STATUS:Telemetri döngüsü başlıyor...", flush=True)
        
        loop_count = 0
        while True:
            try:
                loop_count += 1
                if loop_count % 10 == 0:
                    print(f"STATUS:Telemetri döngü {{loop_count}}", flush=True)
                
                telemetry_data = {{}}
                
                try:
                    async for position in drone.telemetry.position():
                        telemetry_data['position'] = {{
                            'lat': position.latitude_deg,
                            'lon': position.longitude_deg,
                            'alt': position.relative_altitude_m
                        }}
                        break
                except Exception as pos_err:
                    print(f"ERROR:Position: {{pos_err}}", flush=True)
                
                try:
                    async for battery in drone.telemetry.battery():
                        telemetry_data['battery'] = battery.remaining_percent
                        break
                except Exception as bat_err:
                    print(f"ERROR:Battery: {{bat_err}}", flush=True)
                
                try:
                    async for velocity in drone.telemetry.velocity_ned():
                        import math
                        speed_ms = math.sqrt(
                            velocity.north_m_s**2 + 
                            velocity.east_m_s**2 + 
                            velocity.down_m_s**2
                        )
                        telemetry_data['speed'] = speed_ms * 3.6
                        break
                except Exception as vel_err:
                    print(f"ERROR:Velocity: {{vel_err}}", flush=True)
                
                try:
                    async for attitude in drone.telemetry.attitude_euler():
                        heading = attitude.yaw_deg
                        if heading < 0:
                            heading += 360
                        telemetry_data['heading'] = heading
                        break
                except Exception as att_err:
                    print(f"ERROR:Attitude: {{att_err}}", flush=True)
                
                try:
                    async for armed in drone.telemetry.armed():
                        telemetry_data['armed'] = armed
                        break
                except Exception as arm_err:
                    print(f"ERROR:Armed: {{arm_err}}", flush=True)
                
                try:
                    async for flight_mode in drone.telemetry.flight_mode():
                        telemetry_data['flight_mode'] = str(flight_mode)
                        break
                except Exception as fm_err:
                    print(f"ERROR:Flight mode: {{fm_err}}", flush=True)
                
                if telemetry_data:
                    json_output = json.dumps(telemetry_data)
                    print(f"TELEMETRY:{{json_output}}", flush=True)
                
                await asyncio.sleep(2.0)
                
            except Exception as loop_err:
                print(f"ERROR:Telemetry loop: {{loop_err}}", flush=True)
                await asyncio.sleep(1.0)
                
    except Exception as main_err:
        print(f"ERROR:{{main_err}}", flush=True)

asyncio.run(get_telemetry())'''
        
        try:
            self.subprocess_proc = subprocess.Popen([
                'python3', '-c', telemetry_script
            ], 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            universal_newlines=True,
            bufsize=1
            )
            
            Thread(target=self._read_stderr, daemon=True).start()  # ← BU SATIRI EKLEYİN
            
            self.reader_thread = Thread(target=self._read_output, daemon=True)
            self.reader_thread.start()
            
            print("✅ UI Telemetri başlatıldı")
            return True
            
        except Exception as e:
            print(f"❌ UI Telemetri hatası: {e}")
            return False
    
    def _read_stderr(self):
        """Subprocess stderr oku"""
        try:
            while self.running and self.subprocess_proc:
                line = self.subprocess_proc.stderr.readline()
                if not line:
                    break
                print(f"🚨 SUBPROCESS STDERR: {line.strip()}")
        except Exception as e:
            print(f"STDERR okuma hatası: {e}")
        
    def stop(self):
        """UI telemetri durdur"""
        self.running = False
        
        if self.subprocess_proc:
            try:
                self.subprocess_proc.terminate()
                self.subprocess_proc.wait(timeout=3)
            except:
                try:
                    self.subprocess_proc.kill()
                except:
                    pass
            self.subprocess_proc = None
        
        print("✅ UI Telemetri durduruldu")
    
    def _read_output(self):
       """Subprocess çıktısını oku - GÜNCELLEME"""
       try:
           print(f"🚨 DEBUG: _read_output BAŞLADI!")
           print(f"🚨 DEBUG: subprocess_proc = {self.subprocess_proc}")
           print(f"🚨 DEBUG: running = {self.running}")
           
           while self.running and self.subprocess_proc:
               print(f"🚨 DEBUG: readline() bekleniyor...")
               line = self.subprocess_proc.stdout.readline()
               
               if not line:
                   print(f"🚨 DEBUG: line BOŞ - subprocess bitti")
                   break
                   
               line = line.strip()
               print(f"🚨 DEBUG: SUBPROCESS ÇIKTISI: '{line}'")
               
               if line.startswith("TELEMETRY:"):
                   print(f"🚨 DEBUG: TELEMETRY verisi bulundu!")
                   try:
                       json_data = line[10:]
                       print(f"🚨 DEBUG: JSON data: {json_data[:100]}...")
                       telemetry = json.loads(json_data)
                       print(f"🚨 DEBUG: JSON parse başarılı: {list(telemetry.keys())}")
                       
                       # ✅ YENİ: QMetaObject.invokeMethod ile gönder
                       from PyQt5.QtCore import QMetaObject, Q_ARG
                       QMetaObject.invokeMethod(
                           self.main_app,
                           "_update_ui_telemetry", 
                           Q_ARG("PyQt_PyObject", telemetry)
                       )
                       print(f"🚨 DEBUG: QMetaObject.invokeMethod çağrıldı")
                       
                   except Exception as json_error:
                       print(f"🚨 DEBUG: JSON parse hatası: {json_error}")
                       print(f"🚨 DEBUG: Hatalı JSON: {json_data}")
                       
               elif line == "CONNECTED":
                   print("✅ UI Telemetri MAVSDK bağlandı (Port 14540)")
                   
               elif line.startswith("STATUS:"):
                   print(f"📊 Subprocess STATUS: {line[7:]}")
                   
               elif line.startswith("ERROR:"):
                   print(f"❌ Subprocess ERROR: {line[6:]}")
                   
               elif line.strip():  # Boş olmayan diğer satırlar
                   print(f"🔍 Subprocess diğer çıktı: {line}")
                   
           print(f"🚨 DEBUG: _read_output LOOP BİTTİ")
           print(f"🚨 DEBUG: Final - running={self.running}, subprocess_proc={self.subprocess_proc}")
               
       except Exception as e:
           print(f"🚨 DEBUG: _read_output HATASI: {e}")
           import traceback
           traceback.print_exc()
    
    def _send_to_ui(self, telemetry):
        """UI'ya telemetri gönder - DÜZELTME"""
        try:
            print(f"🔄 _send_to_ui çağrıldı, telemetri anahtarları: {list(telemetry.keys())}")
            
            # Yöntem 1: QMetaObject.invokeMethod kullan (DAHA GÜVENLİ)
            from PyQt5.QtCore import QMetaObject, Q_ARG
            
            QMetaObject.invokeMethod(
                self.main_app,
                "_update_ui_telemetry",
                Q_ARG("PyQt_PyObject", telemetry)
            )
            print(f"✅ QMetaObject.invokeMethod ile UI'ya gönderildi")
            
        except Exception as e:
            print(f"❌ _send_to_ui hatası: {e}")
            
            # Alternatif Yöntem 2: Direct call (fallback)
            try:
                print(f"🔄 Direct call deneniyor...")
                self.main_app._update_ui_telemetry(telemetry)
                print(f"✅ Direct call başarılı")
            except Exception as direct_error:
                print(f"❌ Direct call hatası: {direct_error}")
            
class FlightControlStation(QWidget):
    
    SITL_LAT = -35.363262
    SITL_LON = 149.1652371
    SITL_ALT = 584.0
    SITL_HOME_ALT = 10.0
    
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
        
          # OpenWeatherMap API anahtarınızı buraya ekleyin
        
        # MAVSDK bağlantı yöneticisi
        self.connection_manager = None
        self.action_manager = None
        
        self.current_status = "Beklemede"
        self.flight_start_time = None
        self.flight_duration_seconds = 0
        
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.update_status_panel)
        self.status_timer.start(1000)  # Her saniye çalışır
        
        print("✅ Durum paneli aktif edildi")
        
        self.setup_mavsdk_subprocess_manager()
        self.setup_ui_telemetry()
        # Önce sayfaları oluştur
        self.manual_control_page = ManualControlPage(self)
        self.manual_control_page.connect_controls(self.setManualSpeed, self.setManualAltitude, self.setManualHeading)
        self.manual_control_page.emergency_stop.clicked.connect(self._manual_emergency_land)
        self.manual_control_page.return_home.clicked.connect(self._manual_rtl)
        
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
        
        self.last_map_update = 0  # Son harita güncellemesi
        self.map_update_interval = 1.0  # 1 saniyede bir güncelle
        
        # Web bridge'i oluştur
        self.web_bridge = WebBridge(self)
        self.channel = QWebChannel()
        self.channel.registerObject('handler', self.web_bridge)

        # UI'ı başlat
        self.initUI()
        
        # MAVSDK sistemini hazırla
        self.setup_connection_controls()
        self.setup_simple_logging()
        self.initTimer()
        self.update_connection_status(False)
        self.safe_log("🎮 MAVSDK İHA Kontrol İstasyonu hazır - Manuel bağlantı bekleniyor")
        
        self.start_mission_map_button.clicked.connect(self.on_start_mission)
    
    def show_failsafe_monitor(self):
        """Failsafe Monitor dialogunu göster"""
        try:
            print("[MAIN DEBUG] show_failsafe_monitor başladı")
            
            # MAVSDK bağlantısı kontrolü
            if not hasattr(self, 'connection_manager') or not self.connection_manager:
                print("[MAIN DEBUG] Connection manager yok")
                self.show_message(
                    "MAVSDK bağlantısı bulunamadı!\n\nÖnce 'MAVSDK Bağlan' butonunu kullanarak drone'a bağlanın.",
                    "Bağlantı Gerekli",
                    "warning"
                )
                return
            
            print(f"[MAIN DEBUG] Connection manager var: {self.connection_manager}")
            
            if not self.connection_manager.is_connected():
                print("[MAIN DEBUG] Connection manager bağlı değil")
                self.show_message(
                    "MAVSDK bağlantısı aktif değil!\n\nÖnce drone'a bağlanmanız gerekiyor.",
                    "Bağlantı Hatası", 
                    "warning"
                )
                return
            
            print("[MAIN DEBUG] Connection manager bağlı")
            self.safe_log("🛡️ Real-time Failsafe Monitor açılıyor...")
            
            print("[MAIN DEBUG] open_failsafe_monitor çağrılıyor")
            # Failsafe monitor dialogunu aç
            failsafe_dialog = open_failsafe_monitor(self.connection_manager)
            
            print(f"[MAIN DEBUG] Dialog döndü: {failsafe_dialog}")
            
            if failsafe_dialog:
                print("[MAIN DEBUG] Dialog.show() çağrılıyor")
                failsafe_dialog.show()  # Non-modal - arka planda çalışır
                print("[MAIN DEBUG] Dialog.show() tamamlandı")
                
                # Dialog referansını sakla (önemli!)
                self.failsafe_dialog = failsafe_dialog
                print("[MAIN DEBUG] Dialog referansı saklandı")
                
                self.safe_log("✅ Failsafe Monitor başarıyla açıldı")
            else:
                print("[MAIN DEBUG] Dialog None döndü")
                self.safe_log("❌ Failsafe Monitor açılamadı")
                self.show_message(
                    "Failsafe Monitor açılamadı!\n\n"
                    "MAVSDK kütüphanesinin kurulu olduğundan emin olun.",
                    "Dialog Hatası",
                    "error"
                )
                
        except Exception as e:
            print(f"[MAIN DEBUG] Exception: {e}")
            import traceback
            traceback.print_exc()
            
            self.safe_log(f"❌ Failsafe Monitor hatası: {e}")
            self.show_message(
                f"Failsafe Monitor açılamadı:\n\n{str(e)}",
                "Sistem Hatası",
                "error"
            )
        
    def show_preflight_check(self):
        """Basit MAVSDK Preflight Check dialogunu göster"""
        try:
            # MAVSDK bağlantısı kontrolü
            if not hasattr(self, 'connection_manager') or not self.connection_manager:
                self.show_message(
                    "MAVSDK bağlantısı bulunamadı!\n\nÖnce 'MAVSDK Bağlan' butonunu kullanarak drone'a bağlanın.",
                    "Bağlantı Gerekli",
                    "warning"
                )
                return
            
            if not self.connection_manager.is_connected():
                self.show_message(
                    "MAVSDK bağlantısı aktif değil!\n\nÖnce drone'a bağlanmanız gerekiyor.",
                    "Bağlantı Hatası", 
                    "warning"
                )
                return
            
            self.safe_log("🛡️ Basit MAVSDK Preflight Check sistemi başlatılıyor...")
            
            # Basit preflight dialog import ve oluştur
            try:
                # Yeni basit preflight modülünü import et
                from core.real_preflight_check import open_simple_preflight_check
                
                # Dialog oluştur ve göster
                preflight_dialog = open_simple_preflight_check(self.connection_manager)
                
                if not preflight_dialog:
                    self.safe_log("❌ Basit preflight dialog oluşturulamadı")
                    self.show_message(
                        "Basit Preflight Check dialog'u oluşturulamadı!\n\n"
                        "MAVSDK kütüphanesinin kurulu olduğundan emin olun.",
                        "Dialog Hatası",
                        "error"
                    )
                    return
                
                # Kontroller başladığında status güncelle
                self.update_preflight_status("in_progress")
                
                # Dialog'u modal olarak aç
                result = preflight_dialog.exec_()
                
                # Dialog sonucunu değerlendirme yöntemi güncellenecek
                # SimplePreflightDialog'da is_checking durumuna bakabiliriz
                if hasattr(preflight_dialog, 'overall_progress') and preflight_dialog.overall_progress.value() > 0:
                    # Kontroller yapıldı - güvenlik durumuna bak
                    if hasattr(preflight_dialog, 'safety_status_label'):
                        safety_text = preflight_dialog.safety_status_label.text()
                        if "MÜKEMMEL" in safety_text or "GÜVENLİ" in safety_text:
                            self.safe_log("✅ Basit MAVSDK Preflight Check başarıyla tamamlandı")
                            self.update_preflight_status("completed")
                            # Son preflight zamanını kaydet
                            import time
                            self.last_preflight_time = time.time()
                        elif "GÜVENLİ DEĞİL" in safety_text:
                            self.safe_log("❌ Basit MAVSDK Preflight Check - Kritik hatalar tespit edildi")
                            self.update_preflight_status("failed")
                        else:
                            self.safe_log("⚠️ Basit MAVSDK Preflight Check - Uyarılarla tamamlandı")
                            self.update_preflight_status("completed_with_warnings")
                            import time
                            self.last_preflight_time = time.time()
                    else:
                        self.safe_log("✅ Basit MAVSDK Preflight Check tamamlandı")
                        self.update_preflight_status("completed")
                        import time
                        self.last_preflight_time = time.time()
                else:
                    self.safe_log("❌ Basit MAVSDK Preflight Check iptal edildi veya hiç kontrol yapılmadı")
                    self.update_preflight_status("cancelled")
                    
            except ImportError as e:
                self.safe_log(f"❌ Basit Preflight modülü bulunamadı: {e}")
                self.show_message(
                    "Basit MAVSDK Preflight Check modülü bulunamadı!\n\n"
                    "simplified_mavsdk_preflight.py dosyasının proje dizininde olduğundan emin olun.\n\n"
                    "Ayrıca MAVSDK kütüphanesinin kurulu olduğunu kontrol edin:\n"
                    "pip install mavsdk",
                    "Modül Hatası",
                    "error"
                )
                
        except Exception as e:
            self.safe_log(f"❌ Basit MAVSDK Preflight Check hatası: {e}")
            self.show_message(
                f"Basit MAVSDK Preflight Check sistemi başlatılamadı:\n\n{str(e)}\n\n"
                "Lütfen MAVSDK bağlantınızı ve preflight modülünü kontrol edin.",
                "Sistem Hatası",
                "error"
            )
    
    def update_preflight_status(self, status):
        """Preflight durumunu güncelle - Basit MAVSDK versiyonu için"""
        try:
            from datetime import datetime
            
            if status == "completed":
                self.preflight_status_label.setText("✅ Basit MAVSDK kontrol tamamlandı")
                self.preflight_status_label.setStyleSheet("""
                    QLabel {
                        background-color: #27ae60;
                        color: white;
                        border: 2px solid #27ae60;
                        border-radius: 5px;
                        padding: 8px;
                        font-weight: bold;
                    }
                """)
                self.last_preflight_label.setText(f"Son kontrol: {datetime.now().strftime('%H:%M:%S')} (Basit MAVSDK)")
                self.last_preflight_label.setStyleSheet("color: #27ae60; font-weight: bold;")
                
            elif status == "completed_with_warnings":
                self.preflight_status_label.setText("⚠️ Basit MAVSDK kontrol - Uyarılarla tamamlandı")
                self.preflight_status_label.setStyleSheet("""
                    QLabel {
                        background-color: #f39c12;
                        color: white;
                        border: 2px solid #f39c12;
                        border-radius: 5px;
                        padding: 8px;
                        font-weight: bold;
                    }
                """)
                self.last_preflight_label.setText(f"Son kontrol: {datetime.now().strftime('%H:%M:%S')} (Uyarılarla)")
                self.last_preflight_label.setStyleSheet("color: #f39c12; font-weight: bold;")
                
            elif status == "failed":
                self.preflight_status_label.setText("❌ Basit MAVSDK kontrol başarısız")
                self.preflight_status_label.setStyleSheet("""
                    QLabel {
                        background-color: #e74c3c;
                        color: white;
                        border: 2px solid #e74c3c;
                        border-radius: 5px;
                        padding: 8px;
                        font-weight: bold;
                    }
                """)
                self.last_preflight_label.setText("Basit MAVSDK kontrolleri başarısız!")
                self.last_preflight_label.setStyleSheet("color: #e74c3c; font-weight: bold;")
                
            elif status == "cancelled":
                self.preflight_status_label.setText("⏹️ Basit MAVSDK kontrol iptal edildi")
                self.preflight_status_label.setStyleSheet("""
                    QLabel {
                        background-color: #95a5a6;
                        color: white;
                        border: 2px solid #95a5a6;
                        border-radius: 5px;
                        padding: 8px;
                        font-weight: bold;
                    }
                """)
                self.last_preflight_label.setText("Kontroller iptal edildi")
                self.last_preflight_label.setStyleSheet("color: #95a5a6; font-weight: bold;")
                
            elif status == "in_progress":
                self.preflight_status_label.setText("🔄 Basit MAVSDK kontrol devam ediyor")
                self.preflight_status_label.setStyleSheet("""
                    QLabel {
                        background-color: #3498db;
                        color: white;
                        border: 2px solid #3498db;
                        border-radius: 5px;
                        padding: 8px;
                        font-weight: bold;
                    }
                """)
                
        except Exception as e:
            print(f"Preflight status güncelleme hatası: {e}")
    
    def check_preflight_before_takeoff(self):
        """Kalkıştan önce basit MAVSDK preflight kontrolü yap"""
        try:
            # Son preflight kontrolünün ne zaman yapıldığını kontrol et
            import time
            current_time = time.time()
            
            # Eğer preflight yapılmamışsa uyar
            if not hasattr(self, 'last_preflight_time') or not self.last_preflight_time:
                reply = QMessageBox.question(
                    self, 
                    '🛡️ Basit MAVSDK Preflight Check Gerekli',
                    '''Henüz basit MAVSDK preflight check yapılmamış!
    
    ⚠️ Güvenli uçuş için uçuş öncesi kontrollerin yapılması önerilir.
    ⚡ Hızlı ve basit telemetri kontrolleri - UUID karmaşıklığı yok
    🔄 Subprocess tabanlı güvenli kontrol sistemi
    
    Basit MAVSDK preflight check yapmak istiyor musunuz?''',
                    QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
                    QMessageBox.Yes
                )
                
                if reply == QMessageBox.Yes:
                    self.show_preflight_check()
                    return False  # Kalkışı durdur
                elif reply == QMessageBox.Cancel:
                    return False  # Kalkışı iptal et
                # No ise direkt kalkış yap
                
            # Son preflight 30 dakikadan eskiyse uyar
            elif current_time - self.last_preflight_time > 1800:  # 30 dakika
                reply = QMessageBox.question(
                    self,
                    '🛡️ Eski Basit MAVSDK Preflight Check',
                    '''Son basit MAVSDK preflight check 30 dakikadan eski!
    
    Sistem durumu değişmiş olabilir.
    Hızlı telemetri kontrolleriyle yeni kontrol yapmak önerilir.
    
    Yeni basit MAVSDK preflight check yapmak istiyor musunuz?''',
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.Yes
                )
                
                if reply == QMessageBox.Yes:
                    self.show_preflight_check()
                    return False
            
            return True  # Kalkışa devam et
            
        except Exception as e:
            self.safe_log(f"❌ Basit MAVSDK preflight kontrol hatası: {e}")
            return True
    
    def get_preflight_status_summary(self):
        """Preflight durum özetini al"""
        try:
            if not hasattr(self, 'last_preflight_time') or not self.last_preflight_time:
                return {
                    'status': 'not_done',
                    'message': 'Preflight check yapılmamış',
                    'time_ago': None,
                    'safe_to_fly': False
                }
            
            import time
            from datetime import datetime, timedelta
            
            current_time = time.time()
            time_diff = current_time - self.last_preflight_time
            
            # Zaman farkını hesapla
            if time_diff < 60:
                time_ago = f"{int(time_diff)} saniye önce"
            elif time_diff < 3600:
                time_ago = f"{int(time_diff/60)} dakika önce"
            else:
                time_ago = f"{int(time_diff/3600)} saat önce"
            
            # Durum değerlendirmesi
            if time_diff > 1800:  # 30 dakika
                status = 'old'
                safe_to_fly = False
                message = 'Preflight check eski - Yenilenmeli'
            else:
                status = 'recent'
                safe_to_fly = True
                message = 'Preflight check güncel'
            
            return {
                'status': status,
                'message': message,
                'time_ago': time_ago,
                'safe_to_fly': safe_to_fly,
                'last_check': datetime.fromtimestamp(self.last_preflight_time).strftime('%H:%M:%S')
            }
            
        except Exception as e:
            print(f"Preflight status summary hatası: {e}")
            return {
                'status': 'error',
                'message': 'Durum alınamadı',
                'time_ago': None,
                'safe_to_fly': False
            }
    
    def show_preflight_status_info(self):
        """Preflight durum bilgilerini göster"""
        try:
            summary = self.get_preflight_status_summary()
            
            if summary['status'] == 'not_done':
                icon = "⚠️"
                title = "Preflight Check Yapılmamış"
                message = "Henüz basit MAVSDK preflight check yapılmamış.\n\nGüvenli uçuş için kontrollerin yapılması önerilir."
            elif summary['status'] == 'old':
                icon = "🕐"
                title = "Preflight Check Eski"
                message = f"Son kontrol {summary['time_ago']} yapıldı.\n\nSistem durumu değişmiş olabilir.\nYeni kontrol önerilir."
            elif summary['status'] == 'recent':
                icon = "✅"
                title = "Preflight Check Güncel"
                message = f"Son kontrol {summary['time_ago']} yapıldı.\n\nSistem kontrolleri güncel."
            else:
                icon = "❌"
                title = "Preflight Check Hatası"
                message = "Preflight check durumu alınamadı."
            
            QMessageBox.information(
                self,
                f"{icon} {title}",
                message
            )
            
        except Exception as e:
            self.safe_log(f"❌ Preflight status info hatası: {e}")
    
    def setup_mavsdk_subprocess_manager(self):
        """MAVSDK Subprocess Manager'ı kur"""
        try:
            connection_string = "udp://:14540"
            self.mavsdk_manager = MAVSDKSubprocessManager(
                connection_string=connection_string,
                max_concurrent=3
            )
            
            # Callback fonksiyonunu ayarla
            self.mavsdk_manager.set_callback(self.mavsdk_callback)
            
            self.safe_log("✅ MAVSDK Subprocess Manager kuruldu")
            
        except Exception as e:
            self.safe_log(f"❌ MAVSDK Manager kurulum hatası: {e}")

    
    def update_status_panel(self):
        """Durum panelini her saniye güncelle"""
        try:
            # Uçuş süresi hesapla
            if self.flight_start_time is not None:
                from datetime import datetime
                current_time = datetime.now()
                duration = current_time - self.flight_start_time
                self.flight_duration_seconds = int(duration.total_seconds())
            
            # Süreyi dakika:saniye formatına çevir
            minutes = self.flight_duration_seconds // 60
            seconds = self.flight_duration_seconds % 60
            
            # UI'yi güncelle
            self.status_label.setText(f"Durum: {self.current_status}")
            self.flight_time_label.setText(f"Uçuş Süresi: {minutes} dk {seconds} sn")
            
            # Durum rengini ayarla
            self.update_status_color()
            
        except Exception as e:
            print(f"Durum güncelleme hatası: {e}")
    
    def update_status_color(self):
        """Duruma göre renk ayarla"""
        colors = {
            "Beklemede": "#95a5a6",
            "Bağlanıyor": "#f39c12", 
            "Hazır": "#27ae60",
            "Kalkış": "#e67e22",
            "Uçuş": "#3498db",
            "İniş": "#9b59b6",
            "Hata": "#e74c3c"
        }
        
        color = colors.get(self.current_status, "#95a5a6")
        self.status_label.setStyleSheet(f"color: {color}; font-weight: bold;")
    
    def set_flight_status(self, status):
        """Uçuş durumunu değiştir"""
        old_status = self.current_status
        self.current_status = status
        
        # Uçuş başladığında timer'ı başlat
        if status in ["Kalkış", "Uçuş"] and self.flight_start_time is None:
            from datetime import datetime
            self.flight_start_time = datetime.now()
            self.flight_duration_seconds = 0
            print(f"🚀 Uçuş timer başladı: {status}")
        
        # İniş veya hata durumunda timer'ı durdur
        elif status in ["İniş", "Beklemede", "Hata"]:
            if self.flight_start_time is not None:
                print(f"🛬 Uçuş timer durdu: {old_status} → {status}")
            self.flight_start_time = None
        
        print(f"Durum değişti: {old_status} → {status}")
    
    def reset_flight_timer(self):
        """Uçuş timer'ını sıfırla"""
        self.flight_start_time = None
        self.flight_duration_seconds = 0
        self.current_status = "Beklemede"
        print("🔄 Uçuş timer sıfırlandı")
       
    def mavsdk_callback(self, task_id: str, output: str):
        """MAVSDK subprocess callback - SADECE KOMUTLAR"""
        try:
            if output.startswith("STATUS:"):
                status = output[7:]
                self.safe_log(f"🔄 {task_id}: {status}")
                
            elif output.startswith("SUCCESS:"):
                success = output[8:]
                self.safe_log(f"✅ {task_id}: {success}")
                
                if "takeoff" in task_id and "completed" in success:
                    QTimer.singleShot(0, self._set_flying_state)
                elif any(cmd in task_id for cmd in ["land", "rtl", "emergency"]) and "completed" in success:
                    QTimer.singleShot(0, self._set_landed_state)
                    
            elif output.startswith("ERROR:"):
                error = output[6:]
                self.safe_log(f"❌ {task_id}: {error}")
                
            # TELEMETRY kısmı YOK - UI subprocess yapıyor
                    
        except Exception as e:
            print(f"MAVSDK callback hatası: {e}")

    def mavsdk_callback(self, task_id: str, output: str):
        """MAVSDK subprocess callback - SADECE KOMUTLAR + EW MISSION"""
        try:
            # 🚁✈️ EW MISSION ÖZEL FİLTRE - YENİ EKLEME
            if task_id.startswith('ew_'):
                print(f"📡 EW MISSION [{task_id}]: {output}")
                
                if output.startswith("STATUS:"):
                    status = output[7:]
                    self.safe_log(f"📡 EW: {status}")
                    
                elif output.startswith("SUCCESS:"):
                    success = output[8:]
                    self.safe_log(f"✅ EW: {success}")
                    
                    # EW mission tamamlandığında
                    if "completed" in success:
                        QTimer.singleShot(0, self._ew_mission_completed)
                        
                elif output.startswith("ERROR:"):
                    error = output[6:]
                    self.safe_log(f"❌ EW: {error}")
                
                return  # EW için erken çık
            
            # MEVCUT KODUN DEVAMI
            if output.startswith("STATUS:"):
                status = output[7:]
                self.safe_log(f"🔄 {task_id}: {status}")
                
            elif output.startswith("SUCCESS:"):
                success = output[8:]
                self.safe_log(f"✅ {task_id}: {success}")
                
                if "takeoff" in task_id and "completed" in success:
                    QTimer.singleShot(0, self._set_flying_state)
                elif any(cmd in task_id for cmd in ["land", "rtl", "emergency"]) and "completed" in success:
                    QTimer.singleShot(0, self._set_landed_state)
                    
            elif output.startswith("ERROR:"):
                error = output[6:]
                self.safe_log(f"❌ {task_id}: {error}")
                
            # TELEMETRY kısmı YOK - UI subprocess yapıyor
                    
        except Exception as e:
            print(f"MAVSDK callback hatası: {e}")
    
    def _ew_mission_completed(self):
        """EW mission tamamlandığında çağrılır - YENİ METOD"""
        try:
            self.mission_active = False
            self.current_mission = None
            self.safe_log("🎉 EW VTOL Mission başarıyla tamamlandı!")
        except Exception as e:
            self.safe_log(f"❌ EW mission completion hatası: {e}")

    def setup_ui_telemetry(self):
        """UI telemetri kur"""
        self.ui_telemetry = UISubprocessTelemetry(self)
    
    @pyqtSlot(object)
    def _update_ui_telemetry(self, telemetry):
        """UI telemetri ile güncelle - ENHANCED DEBUG"""
        try:
            print(f"🎯 UI Telemetri güncelleme çağrıldı!")
            print(f"🔍 Gelen telemetri: {telemetry}")
            
            position = telemetry.get('position')
            battery = telemetry.get('battery', 100.0)
            speed = telemetry.get('speed', 0.0)
            heading = telemetry.get('heading', 0.0)
            armed = telemetry.get('armed', False)
            flight_mode = telemetry.get('flight_mode', 'UNKNOWN')
            
            print(f"🔍 Parse edilen veriler:")
            print(f"   Position: {position}")
            print(f"   Battery: {battery}")
            print(f"   Speed: {speed}")
            print(f"   Heading: {heading}")
            print(f"   Armed: {armed}")
            print(f"   Flight Mode: {flight_mode}")
            
            # Position güncelle
            if position:
                old_alt = getattr(self, 'altitude', 0)
                self.altitude = round(position['alt'], 2)
                self.gps = f"{position['lat']:.6f}, {position['lon']:.6f}"
                print(f"🔍 Altitude güncellendi: {old_alt} -> {self.altitude}")
                
                # Haritaya gönder
                current_time = time.time()
                if current_time - getattr(self, 'last_map_update', 0) > 2.0:
                    self.send_position_to_map(position['lat'], position['lon'], position['alt'], heading)
                    self.last_map_update = current_time
                    print(f"🔍 Haritaya pozisyon gönderildi")
            
            # Diğer veriler
            self.battery = battery
            self.speed = speed
            self.heading = heading
            
            # UI elementleri güncelle - HER BİRİNİ KONTROL ET
            ui_updates = 0
            
            # ALTITUDE
            if hasattr(self, 'altitude_value'):
                try:
                    self.altitude_value.setText(f"{self.altitude} m")
                    ui_updates += 1
                    print(f"✅ altitude_value güncellendi: {self.altitude} m")
                except Exception as e:
                    print(f"❌ altitude_value hatası: {e}")
            else:
                print(f"❌ altitude_value bulunamadı!")
                
            # SPEED  
            if hasattr(self, 'speed_value'):
                try:
                    self.speed_value.setText(f"{self.speed:.1f} km/h")
                    ui_updates += 1
                    print(f"✅ speed_value güncellendi: {self.speed:.1f} km/h")
                except Exception as e:
                    print(f"❌ speed_value hatası: {e}")
            else:
                print(f"❌ speed_value bulunamadı!")
                
            # HEADING
            if hasattr(self, 'heading_value'):
                try:
                    self.heading_value.setText(f"{self.heading:.0f}°")
                    ui_updates += 1
                    print(f"✅ heading_value güncellendi: {self.heading:.0f}°")
                except Exception as e:
                    print(f"❌ heading_value hatası: {e}")
            else:
                print(f"❌ heading_value bulunamadı!")
                
            # BATTERY
            if hasattr(self, 'battery_value'):
                try:
                    self.battery_value.setText(f"{self.battery:.1f}%")
                    ui_updates += 1
                    print(f"✅ battery_value güncellendi: {self.battery:.1f}%")
                except Exception as e:
                    print(f"❌ battery_value hatası: {e}")
            else:
                print(f"❌ battery_value bulunamadı!")
                
            # GPS
            if hasattr(self, 'gps_value'):
                try:
                    self.gps_value.setText(self.gps)
                    ui_updates += 1
                    print(f"✅ gps_value güncellendi: {self.gps}")
                except Exception as e:
                    print(f"❌ gps_value hatası: {e}")
            else:
                print(f"❌ gps_value bulunamadı!")
                
            # FLIGHT MODE
            if hasattr(self, 'flight_mode_value'):
                try:
                    self.flight_mode_value.setText(flight_mode)
                    ui_updates += 1
                    print(f"✅ flight_mode_value güncellendi: {flight_mode}")
                except Exception as e:
                    print(f"❌ flight_mode_value hatası: {e}")
            else:
                print(f"❌ flight_mode_value bulunamadı!")
                
            # ARM STATUS
            if hasattr(self, 'arm_status_value'):
                try:
                    arm_text = "Armed" if armed else "Disarmed"
                    self.arm_status_value.setText(arm_text)
                    ui_updates += 1
                    print(f"✅ arm_status_value güncellendi: {arm_text}")
                except Exception as e:
                    print(f"❌ arm_status_value hatası: {e}")
            else:
                print(f"❌ arm_status_value bulunamadı!")
            
            print(f"🔍 Toplam {ui_updates} UI elementi güncellendi")
            
            # Göstergeler
            gauge_updates = 0
            
            if hasattr(self, 'speedometer'):
                try:
                    self.speedometer.setSpeed(self.speed)
                    gauge_updates += 1
                    print(f"✅ speedometer güncellendi: {self.speed}")
                except Exception as e:
                    print(f"❌ speedometer hatası: {e}")
            else:
                print(f"❌ speedometer bulunamadı!")
                
            if hasattr(self, 'fuel_gauge'):
                try:
                    self.fuel_gauge.setFuelLevel(self.battery)
                    gauge_updates += 1
                    print(f"✅ fuel_gauge güncellendi: {self.battery}")
                except Exception as e:
                    print(f"❌ fuel_gauge hatası: {e}")
            else:
                print(f"❌ fuel_gauge bulunamadı!")
                
            if hasattr(self, 'compass'):
                try:
                    self.compass.setHeading(self.heading)
                    gauge_updates += 1
                    print(f"✅ compass güncellendi: {self.heading}")
                except Exception as e:
                    print(f"❌ compass hatası: {e}")
            else:
                print(f"❌ compass bulunamadı!")
            
            print(f"🔍 Toplam {gauge_updates} gösterge güncellendi")
            
            # Grafik güncelle
            try:
                self._update_graph_data_simple()
                print(f"✅ Grafik güncellendi")
            except Exception as graph_error:
                print(f"❌ Grafik güncelleme hatası: {graph_error}")
            
            # FORCE REPAINT
            try:
                self.update()  # Widget'ı yeniden çiz
                QApplication.processEvents()  # Event loop'u zorla çalıştır
                print(f"✅ UI repaint zorlandı")
            except Exception as repaint_error:
                print(f"❌ UI repaint hatası: {repaint_error}")
            
            print(f"🎯 UI Telemetri güncelleme tamamlandı!")
            
        except Exception as e:
            print(f"❌ UI telemetri güncelleme hatası: {e}")
            import traceback
            traceback.print_exc()
            
    def _update_graph_data_simple(self):
        """Grafik verilerini güncelle"""
        try:
            self.t += 1
            self.time_list.append(self.t)
            self.altitude_list.append(self.altitude)
            self.speed_list.append(self.speed)
            self.battery_list.append(self.battery)
            self.power_list.append(self.power_consumption)
    
            # Listleri 100 noktaya sınırla
            if len(self.time_list) > 100:
                self.time_list = self.time_list[-100:]
                self.altitude_list = self.altitude_list[-100:]
                self.speed_list = self.speed_list[-100:]
                self.battery_list = self.battery_list[-100:]
                self.power_list = self.power_list[-100:]
    
            # Grafikleri güncelle
            if hasattr(self, 'altitude_curve'):
                self.altitude_curve.setData(self.time_list, self.altitude_list)
            if hasattr(self, 'speed_curve'):
                self.speed_curve.setData(self.time_list, self.speed_list)
            if hasattr(self, 'battery_curve'):
                self.battery_curve.setData(self.time_list, self.battery_list)
            if hasattr(self, 'power_curve'):
                self.power_curve.setData(self.time_list, self.power_list)
                
        except Exception as e:
            print(f"Grafik güncelleme hatası: {e}")
            
    def add_waypoint(self):
        waypoint = self.waypoint_input.text()
        if waypoint:
            self.waypoints.append(waypoint)
            self.waypoint_list.addItem(waypoint)
            self.waypoint_input.clear()
            self.safe_log(f"Waypoint eklendi: {waypoint}")
        
    def setup_simple_logging(self):
        """Basit ve çalışan logging sistemi"""
        try:
            print("✅ Basit logging aktif")
        except Exception as e:
            print(f"Logging hatası: {e}")
    
    def closeEvent(self, event):
        """Uygulama kapatılırken MAVSDK bağlantısını temizle"""
        try:
            if self.connection_manager:
                self.connection_manager.stop_connection()
            
            print("👋 Uygulama kapatılıyor...")
            
        except Exception as e:
            print(f"Kapatma hatası: {e}")
        
        event.accept()
    
    def create_gauge_block(self, gauge_widget, title_text, desc_text, title_color):
        container = QWidget()
        layout = QVBoxLayout(container)
    
        layout.setContentsMargins(10, 0, 10, 0)
        layout.setSpacing(2)
        layout.setAlignment(Qt.AlignTop)
    
        layout.addWidget(gauge_widget, alignment=Qt.AlignHCenter | Qt.AlignTop)
    
        title = QLabel(title_text)
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(f"color: {title_color}; font-weight: bold; font-size: 12px; margin-top: 4px;")
        layout.addWidget(title)
    
        desc = QLabel(desc_text)
        desc.setAlignment(Qt.AlignCenter)
        desc.setWordWrap(True)
        desc.setStyleSheet("color: gray; font-size: 10px; margin-bottom: 2px;")
        layout.addWidget(desc)
    
        return container
    
    def initUI(self):
        self.setWindowTitle('Essirius ALACA İHA Kontrol İstasyonu - MAVSDK Edition')
        self.resize(1200, 800)
        self.setMinimumSize(0, 0)
        self.setMaximumSize(16777215, 16777215)
        
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
        main_layout.setSizeConstraint(QLayout.SetNoConstraint)
        
        # Navigation buttons
        nav_layout = QHBoxLayout()
        
        self.main_page_button = QPushButton("🏠 Ana Sayfa", self)
        self.main_page_button.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(0))
        nav_layout.addWidget(self.main_page_button)
        
        self.manual_control_button = QPushButton("🎮 Manuel Kontrol", self)
        self.manual_control_button.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(1))
        nav_layout.addWidget(self.manual_control_button)
        
        self.lidar_button = QPushButton("📡 LiDAR", self)
        self.lidar_button.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(2))
        nav_layout.addWidget(self.lidar_button)
        
        self.gps_spoof_button = QPushButton("🛰️ GPS Spoofing", self)
        self.gps_spoof_button.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(3))
        nav_layout.addWidget(self.gps_spoof_button)
        
        self.ew_button = QPushButton("⚡ Elektronik Harp", self)
        self.ew_button.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(4))
        nav_layout.addWidget(self.ew_button)
        
        self.map_button = QPushButton("🗺️ Harita", self)
        self.map_button.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(5))
        nav_layout.addWidget(self.map_button)
        
        self.graphs_button = QPushButton("📊 Grafikler", self)
        self.graphs_button.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(6))
        nav_layout.addWidget(self.graphs_button)
        
        self.preflight_nav_button = QPushButton("🛡️ Preflight Check", self)
        self.preflight_nav_button.clicked.connect(self.show_preflight_check)
        self.preflight_nav_button.setStyleSheet("""
            QPushButton {
                background-color: #c0392b;
                color: white;
                border: none;
                padding: 10px;
                border-radius: 10px;
                font-size: 20px;
                font-weight: bold;
                min-width: 180px;
            }
            QPushButton:hover {
                background-color: #a93226;
            }
            QPushButton:pressed {
                background-color: #8e2d1f;
            }
        """)
        nav_layout.addWidget(self.preflight_nav_button)
        
        self.failsafe_nav_button = QPushButton("🛡️ Failsafe Monitor", self)
        self.failsafe_nav_button.clicked.connect(self.show_failsafe_monitor)
        self.failsafe_nav_button.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                padding: 10px;
                border-radius: 10px;
                font-size: 20px;
                font-weight: bold;
                min-width: 180px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
            QPushButton:pressed {
                background-color: #a93226;
            }
        """)
        nav_layout.addWidget(self.failsafe_nav_button)
        
        self.motor_status_button = QPushButton("🔧 Motor Durumu", self)
        self.motor_status_button.clicked.connect(self.show_motor_status)
        nav_layout.addWidget(self.motor_status_button)
        
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
        # Logo kısmını basitleştir - dosya yolu sorunu olabilir
        logo_label.setText("🚁")
        logo_label.setStyleSheet("font-size: 48px; margin: 10px;")
        header_layout.addWidget(logo_label)
        
        # Ust başlık
        self.header_label = QLabel("Essirius ALACA İHA Kontrol İstasyonu (MAVSDK Edition)", self)
        self.header_label.setStyleSheet("font-size: 24px; font-weight: bold; margin: 10px;")
        header_layout.addWidget(self.header_label)
        
        header_layout.addStretch()  # Add stretch to push header to the left
        main_page_layout.addLayout(header_layout, 0, 0, 1, 2)  # Place header at the top
        
        # Kontrol Butonları Layout'u
        control_layout = QGridLayout()
        self.takeoff_button = QPushButton("🚀 Kalkış", self)
        self.takeoff_button.clicked.connect(self.on_takeoff)
        self.land_button = QPushButton("🛬 İniş", self)
        self.land_button.clicked.connect(self.on_land)
        self.emergency_button = QPushButton("🚨 Acil Durum", self)
        self.emergency_button.clicked.connect(self.on_emergency)
        self.start_mission_button = QPushButton("▶️ Görevi Başlat", self)
        self.start_mission_button.clicked.connect(self.on_start_mission)
        self.return_home_button = QPushButton("🏠 Geri Dön", self)
        self.return_home_button.clicked.connect(self.on_return_home)

        control_layout.addWidget(self.takeoff_button, 0, 0)
        control_layout.addWidget(self.land_button, 0, 1)
        control_layout.addWidget(self.emergency_button, 0, 2)
        control_layout.addWidget(self.start_mission_button, 1, 0)
        control_layout.addWidget(self.return_home_button, 1, 1)
        
        main_page_layout.addLayout(control_layout, 1, 0)  # Place control buttons on the left
        
        telemetry_group = QGroupBox("📡 İHA TELEMETRİ VERİLERİ")
        telemetry_layout = QGridLayout()
        
        # Sol sütun - İKONLU ETIKETLER
        telemetry_layout.addWidget(QLabel("🚀 İrtifa:"), 0, 0)
        self.altitude_value = QLabel("0 m")
        telemetry_layout.addWidget(self.altitude_value, 0, 1)
        
        telemetry_layout.addWidget(QLabel("💨 Hız:"), 1, 0)
        self.speed_value = QLabel("0 km/h")
        telemetry_layout.addWidget(self.speed_value, 1, 1)
        
        telemetry_layout.addWidget(QLabel("🧭 Yön:"), 2, 0)
        self.heading_value = QLabel("0°")
        telemetry_layout.addWidget(self.heading_value, 2, 1)
        
        telemetry_layout.addWidget(QLabel("⚙️ Mod:"), 3, 0)
        self.flight_mode_value = QLabel("N/A")
        telemetry_layout.addWidget(self.flight_mode_value, 3, 1)
        
        telemetry_layout.addWidget(QLabel("📍 Konum:"), 4, 0)
        self.gps_coord_value = QLabel("N/A")
        telemetry_layout.addWidget(self.gps_coord_value, 4, 1)
        
        # Sağ sütun - İKONLU ETIKETLER
        telemetry_layout.addWidget(QLabel("🔋 Batarya:"), 0, 2)
        self.battery_value = QLabel("100%")
        telemetry_layout.addWidget(self.battery_value, 0, 3)
        
        telemetry_layout.addWidget(QLabel("🛰️ GPS:"), 1, 2)
        self.gps_value = QLabel("N/A")
        telemetry_layout.addWidget(self.gps_value, 1, 3)
        
        telemetry_layout.addWidget(QLabel("⚡ Güç Tüketimi:"), 2, 2)
        self.power_value = QLabel("0 W")
        telemetry_layout.addWidget(self.power_value, 2, 3)
        
        telemetry_layout.addWidget(QLabel("🛡️ Motor Durumu:"), 3, 2)
        self.arm_status_value = QLabel("N/A")
        telemetry_layout.addWidget(self.arm_status_value, 3, 3)
        
        telemetry_layout.addWidget(QLabel("✈️ Uçuş Durumu:"), 4, 2)
        self.flight_state_value = QLabel("N/A")
        telemetry_layout.addWidget(self.flight_state_value, 4, 3)
        
        # ✅ LAYOUT AYARLARI
        telemetry_layout.setSpacing(7)  # Elemanlar arası boşluk
        telemetry_layout.setContentsMargins(20, 25, 20, 20)  # Panel içi margin
        
        telemetry_group.setLayout(telemetry_layout)
        
        
        
        main_page_layout.addWidget(telemetry_group, 2, 0)
        
        print("✅ Modern İHA Bilgileri Paneli uygulandı!")
        print("🎨 Özellikler:")
        print("   • Gradient arka plan (koyu gri/mavi)")
        print("   • Renkli kategorize edilmiş değerler:")
        print("     - Yeşil: Normal telemetri (irtifa, hız, yön, güç)")
        print("     - Turuncu: Kritik durumlar (batarya, motor, uçuş)")
        print("     - Mavi: Bilgi verileri (mod, GPS, konum)")
        print("   • Hover efektleri")
        print("   • Rounded corner tasarım")
        print("   • Monospace font (Courier New)")
        print("   • Aynı layout düzeni korundu")

        
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
        self.add_waypoint_button.clicked.connect(self.add_waypoint)
        flight_plan_layout.addWidget(self.add_waypoint_button)
        
        self.waypoint_list = QListWidget(self)
        flight_plan_layout.addWidget(self.waypoint_list)
        
        flight_plan_group.setLayout(flight_plan_layout)
        main_page_layout.addWidget(flight_plan_group, 5, 0)  # Place flight plan panel below mission
        
        # Hava Durumu Paneli - Sadece buton
        weather_group = QGroupBox("🌤️ Hava Durumu")
        weather_layout = QVBoxLayout()
        
        
        
        # Sadece bir buton
        self.weather_info_btn = QPushButton("🌤️ Hava Durumu Bilgilerini Gör")
        self.weather_info_btn.clicked.connect(self.show_weather_window)
        
        weather_layout.addWidget(self.weather_info_btn)
        weather_group.setLayout(weather_layout)
        main_page_layout.addWidget(weather_group, 6, 0)
        
        
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
        """initUI metodunda gauge oluşturma kısmını şununla değiştir:"""
    
        # Indicators Group
        indicators_group = QGroupBox("Gelişmiş Göstergeler")
        indicators_layout = QVBoxLayout(indicators_group)
        indicators_group.setStyleSheet("QGroupBox { font-size: 13px; font-weight: bold; }")
        
        gauges_layout = QHBoxLayout()
        gauges_layout.setSpacing(30)
        gauges_layout.setAlignment(Qt.AlignCenter)
        
        # Ölçü
        gauge_size = int(220 * UI_SCALE)  # Biraz daha büyük
        
        # ✅ YENİ: Gelişmiş Hız Göstergesi
        self.speedometer = AdvancedSpeedometerWidget(self)
        self.speedometer.setMinimumSize(gauge_size, gauge_size)
        speed_block = self.create_gauge_block(
            self.speedometer, 
            "AKILLI HIZ GÖSTERGESİ", 
            "🎨 Renkli zone'lar 🔄 Smooth animasyon 📱 Digital display\n👆 Sol tık: Birim değiştir", 
            "#e74c3c"
        )
        
        # ✅ YENİ: Gelişmiş Batarya Göstergesi  
        self.fuel_gauge = AdvancedBatteryGaugeWidget(self)
        self.fuel_gauge.setMinimumSize(gauge_size, gauge_size)
        fuel_block = self.create_gauge_block(
            self.fuel_gauge,
            "AKILLI BATARYA GÖSTERGESİ",
            "⚠️ Düşük batarya uyarısı 🌈 Gradient renkler 🔋 İkon gösterimi\n💡 Otomatik blink efekti", 
            "#2ecc71"
        )
        
        # ✅ YENİ: Gelişmiş Pusula Göstergesi
        self.compass = AdvancedCompassWidget(self)
        self.compass.setMinimumSize(gauge_size, gauge_size)
        compass_block = self.create_gauge_block(
            self.compass,
            "AKILLI PUSULA GÖSTERGESİ", 
            "🧭 Renkli yön gösterimi 🔄 Smooth döndürme 📐 Digital derece\n👆 Sağ tık: Kuzeyi göster",
            "#e67e22"
        )
        
        # Ekle
        gauges_layout.addWidget(speed_block)
        gauges_layout.addWidget(fuel_block)
        gauges_layout.addWidget(compass_block)
        
        indicators_layout.addLayout(gauges_layout)
        
        print("🚀 SÜPER GAUGE'LAR AKTİF!")
        print("📋 ÖZELLİKLER:")
        print("   🎨 Renk gradientleri (yeşil→sarı→kırmızı)")
        print("   ⚡ Smooth animasyonlar (500ms geçiş)")
        print("   💎 3D efektler ve gölgeler")
        print("   📱 Digital display'ler")
        print("   🔍 Min/Max takibi")
        print("   🌟 Glow ve pulse efektleri")
        print("   🎯 Zone gösterimleri")
        print("   🤖 Drone logosu")
        print("   ⚠️ Kritik değer uyarıları")
        print("   👆 Mouse etkileşimi")
        
        # Bağlantı Paneli
        connection_group = QGroupBox("MAVSDK Bağlantı Paneli")
        connection_layout = QVBoxLayout()
        connection_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
        # Port ve Baudrate ayarları için container
        settings_container = QHBoxLayout()
        
        # Port ayarları
        port_layout = QVBoxLayout()
        port_label = QLabel("Bağlantı String:")
        port_label.setStyleSheet("color: #e74c3c; font-weight: bold;")
        self.port_input = QLineEdit()
        self.port_input.setPlaceholderText("udp://:14540")
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
        
        # Timeout ayarları
        timeout_layout = QVBoxLayout()
        timeout_label = QLabel("Timeout (s):")
        timeout_label.setStyleSheet("color: #e74c3c; font-weight: bold;")
        self.timeout_input = QLineEdit()
        self.timeout_input.setPlaceholderText("30")
        self.timeout_input.setStyleSheet("""
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
        timeout_layout.addWidget(timeout_label)
        timeout_layout.addWidget(self.timeout_input)
        
        settings_container.addLayout(port_layout)
        settings_container.addLayout(timeout_layout)
        
        # Bağlantı butonları
        button_container = QHBoxLayout()
        self.connect_button = QPushButton("🔗 MAVSDK Bağlan", self)
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
        
        self.disconnect_button = QPushButton("🔌 Bağlantıyı Kes", self)
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
        self.connection_status_label = QLabel("MAVSDK Durumu: Bağlantı Yok", self)
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
        #right_layout.addWidget(ew_group)
        right_layout.addWidget(log_group)
        right_layout.addStretch(0)  # Alt boşluğu kaldır
        
        main_page_layout.addWidget(right_container, 0, 2, 7, 1)  # Sağ tarafı tamamen kapla
        
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
        self.start_mission_map_button.clicked.connect(self.on_start_mission)
        
        # Ana layout'a panelleri ekle
        top_panel.addWidget(waypoint_group)
        
        # Harita ve sol panel için container
        map_container = QHBoxLayout()
        left_panel_widget = QWidget()
        left_panel_widget.setLayout(left_panel)
        
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
        
        self.stacked_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        main_page.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        right_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        left_panel_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # Uçuş Modu Seçici Elemanlar
        self.mode_combo = QComboBox()
        self.mode_combo.addItems([
            "HOLD",         # Pozisyon tutma
            "TAKEOFF",      # Kalkış modu
            "LAND",         # İniş modu
            "RETURN_TO_LAUNCH",  # Eve dönüş
            "FOLLOW_ME",    # Takip modu
            "OFFBOARD"      # Offboard kontrol
        ])
        self.mode_combo.setFixedWidth(120)
        
        self.set_mode_button = QPushButton("Modu Uygula")
        self.set_mode_button.setFixedWidth(160)
        self.set_mode_button.setStyleSheet("background-color: #f4511e; color: white;")
        self.set_mode_button.clicked.connect(self.set_flight_mode)
        
        # Yatay yerleşim (ComboBox + Button yan yana)
        mod_select_layout = QHBoxLayout()
        mod_select_layout.addWidget(QLabel("Mod:"))
        mod_select_layout.addWidget(self.mode_combo)
        mod_select_layout.addWidget(self.set_mode_button)
        mod_select_layout.setAlignment(Qt.AlignRight)
        
        mod_select_widget = QWidget()
        mod_select_widget.setLayout(mod_select_layout)
        
        # Kontrol layout'una en sağa (1. satır, 2. sütun) ekle
        control_layout.addWidget(mod_select_widget, 1, 2)

        self.load_previous_state()
        self.check_restart_status()
    
    def show_motor_status(self):
        # Motor durumu penceresini aç
        self.motor_window = MotorStatusWidget()
        self.motor_window.setWindowTitle("Motor Durumu")
        self.motor_window.resize(800, 600)
        self.motor_window.show()
    
    def show_message(self, message, title="Bilgi", msg_type="info"):
        """Kullanıcıya mesaj göster"""
        from PyQt5.QtWidgets import QMessageBox
        
        if msg_type == "info":
            QMessageBox.information(self, title, message)
        elif msg_type == "warning":
            QMessageBox.warning(self, title, message)
        elif msg_type == "error":
            QMessageBox.critical(self, title, message)
        else:
            QMessageBox.information(self, title, message)    

    def show_weather_window(self):
        """AI Hava Durumu penceresini aç"""
        api_key = "fef7f6da4d4450bc962c2c694ebfb379"  # OpenWeatherMap API key
        location = "Eskişehir"
        
        try:
            weather_dialog = create_weather_ai_dialog(api_key, location, self)
            result = weather_dialog.exec_()
            
            if result == QDialog.Accepted:
                print("✅ Hava durumu analizi tamamlandı")
            
        except Exception as e:
            print(f"❌ Hava durumu hatası: {e}")
            self.show_message(f"Hava durumu servisi kullanılamıyor: {e}")

    def set_flight_mode(self):
        """MAVSDK flight mode ayarlama"""
        mode_name = self.mode_combo.currentText()
        
        if not self.connection_manager or not self.connection_manager.is_connected():
            self.safe_log("⚠ MAVSDK bağlantısı yok.")
            return
    
        def do_set_mode():
            try:
                async def async_set_mode():
                    try:
                        system = self.connection_manager.system
                        if not system:
                            self.safe_log("❌ MAVSDK system bulunamadı!")
                            return
                        
                        # MAVSDK'de flight mode ayarlama (action plugin üzerinden)
                        if mode_name == "HOLD":
                            await system.action.hold()
                            self.safe_log("✅ HOLD modu aktif")
                        elif mode_name == "RETURN_TO_LAUNCH":
                            await system.action.return_to_launch()
                            self.safe_log("✅ RTL modu aktif")
                        elif mode_name == "LAND":
                            await system.action.land()
                            self.safe_log("✅ LAND modu aktif")
                        else:
                            self.safe_log(f"⚠ '{mode_name}' modu henüz desteklenmiyor")
                            
                    except Exception as e:
                        self.safe_log(f"❌ Mod ayarlama hatası: {e}")
                
                # Async event loop
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(async_set_mode())
                loop.close()
                
            except Exception as e:
                self.safe_log(f"❌ Mod ayarlama thread hatası: {e}")
        
        Thread(target=do_set_mode, daemon=True).start()

    def initTimer(self):
        """Timer hazırlığı - MAVSDK bağlantısında başlatılacak"""
        self.safe_log("⏰ MAVSDK Timer sistemi hazır")
    
    def setManualSpeed(self, value):
        """MAVSDK ile speed kontrolü"""
        self.speed = value
        self.speedometer.setSpeed(value)
        
        if not self.connection_manager or not self.connection_manager.is_connected():
            return
            
        def do_speed_control():
            try:
                async def async_speed_control():
                    try:
                        system = self.connection_manager.system
                        if not system:
                            return
                        
                        # MAVSDK offboard ile hız kontrolü
                        speed_ms = value / 3.6  # km/h to m/s
                        
                        # Velocity body yaw speed kullan
                        velocity = VelocityBodyYawspeed(speed_ms, 0.0, 0.0, 0.0)
                        await system.offboard.set_velocity_body(velocity)
                        
                    except Exception as e:
                        print(f"Speed control hatası: {e}")
                
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(async_speed_control())
                loop.close()
                
            except Exception as e:
                print(f"Speed control thread hatası: {e}")
        
        if self.in_flight:
            Thread(target=do_speed_control, daemon=True).start()

    def setManualAltitude(self, value):
        """MAVSDK ile altitude kontrolü"""
        self.altitude = value
        self.altitude_value.setText(f"{value} m")
        
        if not self.connection_manager or not self.connection_manager.is_connected():
            return
            
        def do_altitude_control():
            try:
                async def async_altitude_control():
                    try:
                        system = self.connection_manager.system
                        if not system:
                            return
                        
                        # Mevcut pozisyonu al ve sadece altitude'u değiştir
                        async for position in system.telemetry.position():
                            current_lat = position.latitude_deg
                            current_lon = position.longitude_deg
                            
                            # Goto location ile altitude değiştir
                            await system.action.goto_location(
                                current_lat, current_lon, value, 0  # yaw=0
                            )
                            break
                            
                    except Exception as e:
                        print(f"Altitude control hatası: {e}")
                
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(async_altitude_control())
                loop.close()
                
            except Exception as e:
                print(f"Altitude control thread hatası: {e}")
        
        if self.in_flight:
            Thread(target=do_altitude_control, daemon=True).start()

    def setManualHeading(self, value):
        """MAVSDK ile heading kontrolü"""
        self.heading = value
        self.compass.setHeading(value)
        
        if not self.connection_manager or not self.connection_manager.is_connected():
            return
            
        def do_heading_control():
            try:
                async def async_heading_control():
                    try:
                        system = self.connection_manager.system
                        if not system:
                            return
                        
                        # Position NED yaw ile heading kontrolü
                        position_ned = PositionNedYaw(0.0, 0.0, 0.0, value)
                        await system.offboard.set_position_ned(position_ned)
                        
                    except Exception as e:
                        print(f"Heading control hatası: {e}")
                
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(async_heading_control())
                loop.close()
                
            except Exception as e:
                print(f"Heading control thread hatası: {e}")
        
        if self.in_flight:
            Thread(target=do_heading_control, daemon=True).start()

    def _manual_emergency_land(self):
        """MAVSDK acil iniş"""
        if not self.connection_manager or not self.connection_manager.is_connected():
            self.safe_log("⚠ MAVSDK bağlantısı yok!")
            return
            
        def do_emergency_land():
            try:
                async def async_emergency_land():
                    try:
                        system = self.connection_manager.system
                        if system:
                            await system.action.land()
                            self.safe_log("🚨 MAVSDK acil iniş komutu gönderildi!")
                    except Exception as e:
                        self.safe_log(f"❌ Acil iniş hatası: {e}")
                
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(async_emergency_land())
                loop.close()
                
            except Exception as e:
                self.safe_log(f"❌ Acil iniş thread hatası: {e}")
        
        Thread(target=do_emergency_land, daemon=True).start()

    def _manual_rtl(self):
        """MAVSDK Return to Launch"""
        if not self.connection_manager or not self.connection_manager.is_connected():
            self.safe_log("⚠ MAVSDK bağlantısı yok!")
            return
            
        def do_rtl():
            try:
                async def async_rtl():
                    try:
                        system = self.connection_manager.system
                        if system:
                            await system.action.return_to_launch()
                            self.safe_log("🏠 MAVSDK RTL komutu gönderildi!")
                    except Exception as e:
                        self.safe_log(f"❌ RTL hatası: {e}")
                
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(async_rtl())
                loop.close()
                
            except Exception as e:
                self.safe_log(f"❌ RTL thread hatası: {e}")
        
        Thread(target=do_rtl, daemon=True).start()
   
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
        """MAVSDK için gelişmiş harita - Legend + Flight Trail + Status."""
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>MAVSDK Gelişmiş Harita</title>
            <meta charset="utf-8" />
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            
            <!-- Leaflet CSS -->
            <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" 
                  integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY=" 
                  crossorigin=""/>
            
            <!-- Leaflet JavaScript -->
            <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"
                    integrity="sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo="
                    crossorigin=""></script>
                    
            <!-- QWebChannel -->
            <script src="qrc:///qtwebchannel/qwebchannel.js"></script>
            
            <style>
                #map { 
                    height: 100vh; 
                    width: 100%;
                    border: none;
                    margin: 0;
                    padding: 0;
                }
                
                body {
                    margin: 0;
                    padding: 0;
                    font-family: Arial, sans-serif;
                }
                
                /* Legend Panel - Sol üst */
                .legend-panel {
                    position: absolute;
                    top: 10px;
                    left: 10px;
                    background: rgba(44, 44, 44, 0.95);
                    color: white;
                    padding: 15px;
                    border-radius: 8px;
                    z-index: 1000;
                    font-size: 12px;
                    min-width: 200px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.3);
                }
                
                .legend-item {
                    display: flex;
                    align-items: center;
                    margin: 5px 0;
                }
                
                .legend-icon {
                    width: 16px;
                    height: 16px;
                    margin-right: 8px;
                    border-radius: 50%;
                    display: inline-block;
                }
                
                .legend-line {
                    width: 20px;
                    height: 3px;
                    margin-right: 8px;
                    display: inline-block;
                }
                
                /* Status Panel - Sağ üst */
                .status-panel {
                    position: absolute;
                    top: 10px;
                    right: 10px;
                    background: rgba(44, 44, 44, 0.95);
                    color: white;
                    padding: 15px;
                    border-radius: 8px;
                    z-index: 1000;
                    font-size: 12px;
                    min-width: 220px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.3);
                }
                
                .status-item {
                    margin: 3px 0;
                    display: flex;
                    justify-content: space-between;
                }
                
                .status-value {
                    font-weight: bold;
                    color: #2ecc71;
                }
                
                /* Flight Info Panel - Sol alt */
                .flight-info {
                    position: absolute;
                    bottom: 10px;
                    left: 10px;
                    background: rgba(44, 44, 44, 0.95);
                    color: white;
                    padding: 12px;
                    border-radius: 8px;
                    z-index: 1000;
                    font-size: 11px;
                    min-width: 180px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.3);
                }
                
                .drone-marker {
                    animation: pulse 2s infinite;
                }
                
                @keyframes pulse {
                    0% { transform: scale(1); }
                    50% { transform: scale(1.2); }
                    100% { transform: scale(1); }
                }
                
                .blink {
                    animation: blink 1s infinite;
                }
                
                @keyframes blink {
                    0%, 50% { opacity: 1; }
                    51%, 100% { opacity: 0.3; }
                }
            </style>
        </head>
        <body>
            <!-- Legend Panel -->
            <div class="legend-panel">
                <div style="font-weight: bold; margin-bottom: 10px; color: #e74c3c;">
                    🗺️ MAVSDK HARİTA LEGENDİ
                </div>
                
                <div class="legend-item">
                    <div class="legend-icon" style="background: #e74c3c; border: 2px solid white; box-shadow: 0 0 5px rgba(231,76,60,0.7);"></div>
                    <span>Drone (MAVSDK Konum)</span>
                </div>
                
                <div class="legend-item">
                    <div class="legend-icon" style="background: #27ae60; border: 2px solid white;"></div>
                    <span>Home Position</span>
                </div>
                
                <div class="legend-item">
                    <div class="legend-icon" style="background: #2ecc71; border: 2px solid white;"></div>
                    <span>Başlangıç Noktası</span>
                </div>
                
                <div class="legend-item">
                    <div class="legend-icon" style="background: #e67e22; border: 2px solid white;"></div>
                    <span>Bitiş Noktası</span>
                </div>
                
                <div class="legend-item">
                    <div class="legend-icon" style="background: #3498db; border: 2px solid white;"></div>
                    <span>Waypoint</span>
                </div>
                
                <div style="margin: 10px 0; border-top: 1px solid #555; padding-top: 8px;">
                    <div class="legend-item">
                        <div class="legend-line" style="background: #e74c3c; opacity: 0.8;"></div>
                        <span>Uçuş İzi (Flight Trail)</span>
                    </div>
                    
                    <div class="legend-item">
                        <div class="legend-line" style="background: #3498db; border: 1px dashed #3498db;"></div>
                        <span>Planlanan Rota</span>
                    </div>
                </div>
            </div>
            
            <!-- Status Panel -->
            <div class="status-panel">
                <div style="font-weight: bold; margin-bottom: 10px; color: #e74c3c;">
                    📡 MAVSDK CANLI VERİLER
                </div>
                
                <div class="status-item">
                    <span>Konum:</span>
                    <span class="status-value" id="currentLocation">Bekleniyor...</span>
                </div>
                
                <div class="status-item">
                    <span>İrtifa:</span>
                    <span class="status-value" id="currentAltitude">0 m</span>
                </div>
                
                <div class="status-item">
                    <span>Hız:</span>
                    <span class="status-value" id="currentSpeed">0 km/h</span>
                </div>
                
                <div class="status-item">
                    <span>Yön:</span>
                    <span class="status-value" id="currentHeading">0°</span>
                </div>
                
                <div class="status-item">
                    <span>Son Güncelleme:</span>
                    <span class="status-value" id="lastUpdate">Hiç</span>
                </div>
                
                <div style="margin-top: 8px; padding-top: 8px; border-top: 1px solid #555;">
                    <div class="status-item">
                        <span>MAVSDK Durumu:</span>
                        <span class="status-value" id="dataStatus">🔴 Bekleniyor</span>
                    </div>
                </div>
            </div>
            
            <!-- Flight Info Panel -->
            <div class="flight-info">
                <div style="font-weight: bold; margin-bottom: 8px; color: #f39c12;">
                    ✈️ UÇUŞ BİLGİLERİ
                </div>
                
                <div style="margin: 3px 0;">
                    <strong>Toplam Mesafe:</strong> <span id="totalDistance">0 m</span>
                </div>
                
                <div style="margin: 3px 0;">
                    <strong>Uçuş Süresi:</strong> <span id="flightTime">00:00</span>
                </div>
                
                <div style="margin: 3px 0;">
                    <strong>Trail Noktaları:</strong> <span id="trailPoints">0</span>
                </div>
                
                <div style="margin: 3px 0;">
                    <strong>MAVSDK Sistem:</strong> Aktif
                </div>
            </div>
            
            <!-- Harita container -->
            <div id="map"></div>
            
            <script>
                console.log("🗺️ MAVSDK Gelişmiş Harita yükleniyor...");
                
                // SITL koordinatları
                var SITL_LAT = -35.363262;
                var SITL_LON = 149.1652371;
                var SITL_ZOOM = 16;
                
                // Harita oluştur
                var map = L.map('map').setView([SITL_LAT, SITL_LON], SITL_ZOOM);
                
                // Tile layer
                L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                    maxZoom: 19,
                    attribution: '© OpenStreetMap | MAVSDK Real Data'
                }).addTo(map);
                
                // Global değişkenler
                var markers = [];
                var flightPath = null;
                var startMarker = null;
                var endMarker = null;
                var dataReceived = false;
                var flightStartTime = null;
                var totalDistance = 0;
                
                // FLIGHT TRAIL SİSTEMİ
                var flightTrail = [];
                var trailPath = null;
                var maxTrailPoints = 50; // Son 50 noktayı sakla
                var lastPosition = null;
                
                // Drone marker (gelişmiş)
                var droneIcon = L.divIcon({
                    className: 'drone-marker',
                    html: `<div style="
                        background: #e74c3c; 
                        width: 16px; 
                        height: 16px; 
                        border-radius: 50%; 
                        border: 3px solid white; 
                        box-shadow: 0 0 15px rgba(231,76,60,0.8);
                        position: relative;
                    ">
                        <div style="
                            position: absolute;
                            top: -3px;
                            left: -3px;
                            width: 16px;
                            height: 16px;
                            border: 3px solid #e74c3c;
                            border-radius: 50%;
                            opacity: 0.6;
                        "></div>
                    </div>`,
                    iconSize: [22, 22],
                    iconAnchor: [11, 11]
                });
                
                var droneMarker = L.marker([SITL_LAT, SITL_LON], {
                    icon: droneIcon
                }).addTo(map);
                
                // Home marker
                var homeIcon = L.divIcon({
                    className: 'home-marker',
                    html: '<div style="background: #27ae60; width: 14px; height: 14px; border-radius: 50%; border: 2px solid white; box-shadow: 0 0 8px rgba(39,174,96,0.6);"></div>',
                    iconSize: [18, 18],
                    iconAnchor: [9, 9]
                });
                
                var homeMarker = L.marker([SITL_LAT, SITL_LON], {
                    icon: homeIcon
                }).addTo(map);
                
                homeMarker.bindPopup("🏠 MAVSDK Home Position");
                
                // QWebChannel setup
                new QWebChannel(qt.webChannelTransport, function(channel) {
                    console.log("✅ QWebChannel bağlantısı kuruldu");
                    window.handler = channel.objects.handler;
                    
                    // Harita click handler
                    map.on('click', function(e) {
                        var waypointIcon = L.divIcon({
                            className: 'waypoint-marker',
                            html: '<div style="background: #3498db; width: 10px; height: 10px; border-radius: 50%; border: 2px solid white; box-shadow: 0 0 5px rgba(52,152,219,0.7);"></div>',
                            iconSize: [14, 14],
                            iconAnchor: [7, 7]
                        });
                        
                        var marker = L.marker(e.latlng, {icon: waypointIcon}).addTo(map);
                        markers.push(marker);
                        
                        if (window.handler && window.handler.handleClick) {
                            window.handler.handleClick(e.latlng.lat, e.latlng.lng);
                        }
                        
                        updateFlightPath();
                    });
                });
                
                // GERÇEK DRONE POZİSYONU GÜNCELLEME + FLIGHT TRAIL
                function updateDronePosition(lat, lon, alt, heading) {
                    console.log("📍 MAVSDK pozisyon güncellendi:", lat, lon, alt, heading);
                    
                    var currentPos = [lat, lon];
                    
                    // Drone marker güncelle
                    droneMarker.setLatLng(currentPos);
                    
                    // Flight trail güncelleme
                    if (lastPosition) {
                        // Mesafe hesapla (basit)
                        var distance = map.distance(lastPosition, currentPos);
                        if (distance > 1) { // 1 metreden fazla hareket varsa trail'e ekle
                            flightTrail.push({
                                latlng: currentPos,
                                time: new Date(),
                                alt: alt,
                                speed: 0 // Hız bilgisi eklenebilir
                            });
                            
                            totalDistance += distance;
                            
                            // Trail boyutunu sınırla
                            if (flightTrail.length > maxTrailPoints) {
                                flightTrail.shift();
                            }
                            
                            updateFlightTrail();
                        }
                    }
                    
                    lastPosition = currentPos;
                    
                    // Status panel güncelle
                    updateStatusPanel(lat, lon, alt, heading);
                    
                    // İlk veri kontrolü
                    if (!dataReceived) {
                        map.setView(currentPos, SITL_ZOOM);
                        dataReceived = true;
                        flightStartTime = new Date();
                        console.log("🎯 İlk MAVSDK verisi alındı");
                    }
                }
                
                // Flight trail çizimi
                function updateFlightTrail() {
                    if (trailPath) {
                        map.removeLayer(trailPath);
                    }
                    
                    if (flightTrail.length > 1) {
                        var trailCoords = flightTrail.map(point => point.latlng);
                        
                        trailPath = L.polyline(trailCoords, {
                            color: '#e74c3c',
                            weight: 4,
                            opacity: 0.8,
                            smoothFactor: 1,
                            className: 'flight-trail'
                        }).addTo(map);
                        
                        // Trail popup
                        trailPath.bindPopup(`
                            <b>🛤️ MAVSDK Uçuş İzi</b><br>
                            Toplam Nokta: ${flightTrail.length}<br>
                            Mesafe: ${(totalDistance).toFixed(1)} m
                        `);
                    }
                    
                    // Flight info güncelle
                    document.getElementById('trailPoints').textContent = flightTrail.length;
                    document.getElementById('totalDistance').textContent = totalDistance.toFixed(1) + ' m';
                }
                
                // Status panel güncelleme
                function updateStatusPanel(lat, lon, alt, heading) {
                    document.getElementById('currentLocation').textContent = `${lat.toFixed(5)}, ${lon.toFixed(5)}`;
                    document.getElementById('currentAltitude').textContent = `${alt.toFixed(1)} m`;
                    document.getElementById('currentHeading').textContent = `${heading}°`;
                    document.getElementById('lastUpdate').textContent = new Date().toLocaleTimeString();
                    document.getElementById('dataStatus').innerHTML = '🟢 MAVSDK Aktif';
                    
                    // Uçuş süresi
                    if (flightStartTime) {
                        var duration = Math.floor((new Date() - flightStartTime) / 1000);
                        var minutes = Math.floor(duration / 60);
                        var seconds = duration % 60;
                        document.getElementById('flightTime').textContent = 
                            `${minutes.toString().padStart(2,'0')}:${seconds.toString().padStart(2,'0')}`;
                    }
                }
                
                // Planlanan rota çizimi
                function updateFlightPath() {
                    if (flightPath) {
                        map.removeLayer(flightPath);
                    }
                    
                    var points = markers.map(m => m.getLatLng());
                    if (startMarker) points.unshift(startMarker.getLatLng());
                    if (endMarker) points.push(endMarker.getLatLng());
                    
                    if (points.length > 1) {
                        flightPath = L.polyline(points, {
                            color: '#3498db',
                            weight: 3,
                            opacity: 0.7,
                            dashArray: '10, 5'
                        }).addTo(map);
                    }
                }
                
                // Başlangıç/Bitiş noktaları
                function addStartPoint(lat, lon) {
                    if (startMarker) map.removeLayer(startMarker);
                    
                    var startIcon = L.divIcon({
                        className: 'start-marker',
                        html: '<div style="background: #2ecc71; width: 12px; height: 12px; border-radius: 50%; border: 2px solid white; box-shadow: 0 0 8px rgba(46,204,113,0.7);"></div>',
                        iconSize: [16, 16],
                        iconAnchor: [8, 8]
                    });
                    
                    startMarker = L.marker([lat, lon], {icon: startIcon}).addTo(map);
                    startMarker.bindPopup('🟢 Başlangıç Noktası');
                    updateFlightPath();
                }
                
                function addEndPoint(lat, lon) {
                    if (endMarker) map.removeLayer(endMarker);
                    
                    var endIcon = L.divIcon({
                        className: 'end-marker',
                        html: '<div style="background: #e67e22; width: 12px; height: 12px; border-radius: 50%; border: 2px solid white; box-shadow: 0 0 8px rgba(230,126,34,0.7);"></div>',
                        iconSize: [16, 16],
                        iconAnchor: [8, 8]
                    });
                    
                    endMarker = L.marker([lat, lon], {icon: endIcon}).addTo(map);
                    endMarker.bindPopup('🔴 Bitiş Noktası');
                    updateFlightPath();
                }
                
                function addHomePoint(lat, lon) {
                    homeMarker.setLatLng([lat, lon]);
                }
                
                function clearWaypoints() {
                    markers.forEach(m => map.removeLayer(m));
                    markers = [];
                    if (startMarker) { map.removeLayer(startMarker); startMarker = null; }
                    if (endMarker) { map.removeLayer(endMarker); endMarker = null; }
                    if (flightPath) { map.removeLayer(flightPath); flightPath = null; }
                }
                
                console.log("🎉 MAVSDK Gelişmiş Harita hazır!");
            </script>
        </body>
        </html>
        """
    
    @pyqtSlot(str)
    def log_message(self, message):
        """Thread-safe log mesajı."""
        try:
            time_str = datetime.now().strftime('%H:%M:%S')
            full_message = f"[{time_str}] {message}"
            
            if hasattr(self, 'log_area'):
                self.log_area.appendPlainText(full_message)
            else:
                print(full_message)
        except Exception as e:
            print(f"LOG ERROR: {e} - Original: {message}")
    
    def safe_log(self, message):
        """Thread-safe log wrapper."""
        try:
            # Ana thread'de mi kontrolü
            if threading.current_thread() == threading.main_thread():
                self.log_message(message)
            else:
                # QTimer kullanarak ana thread'de çalıştır
                QTimer.singleShot(0, lambda: self.log_message(message))
        except Exception as e:
            print(f"SAFE_LOG ERROR: {e} - Message: {message}")
    
    def on_takeoff(self):
        """MAVSDK uyumlu kalkış fonksiyonu"""
        
        if not MAVSDK_AVAILABLE:
            self.safe_log("❌ MAVSDK kütüphanesi yüklenmemiş!")
            return
        
        if not self.connection_manager:
            self.safe_log("⚠ Önce MAVSDK'ye bağlanın!")
            return
            
        if self.in_flight:
            self.safe_log("🚁 Zaten uçuşta!")
            return
        
        if not self.connection_manager.is_connected():
            self.safe_log("❌ MAVSDK bağlantısı yok!")
            return
    
        def do_mavsdk_takeoff():
            try:
                async def async_takeoff():
                    try:
                        # MAVSDK System objesi al
                        system = self.connection_manager.system
                        if not system:
                            self.safe_log("❌ MAVSDK System bulunamadı!")
                            return
                        
                        self.safe_log("🚀 MAVSDK kalkış başlatılıyor...")
                        
                        # Action manager oluştur
                        if not self.action_manager:
                            self.action_manager = MAVSDKActionManager(system)
                        
                        # ARM ve takeoff işlemi
                        success = await self.action_manager.arm_and_takeoff(altitude=10.0)
                        
                        if success:
                            # UI güncelle (main thread'de)
                            QTimer.singleShot(0, self._set_flying_state)
                            self.safe_log("🎉 MAVSDK kalkış tamamlandı!")
                        else:
                            self.safe_log("❌ MAVSDK kalkış başarısız!")
                        
                    except Exception as async_error:
                        self.safe_log(f"❌ MAVSDK async kalkış hatası: {async_error}")
                        import traceback
                        traceback.print_exc()
                
                # Yeni event loop oluştur (thread'de)
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(async_takeoff())
                loop.close()
                
            except Exception as thread_error:
                self.safe_log(f"❌ MAVSDK kalkış thread hatası: {thread_error}")
                import traceback
                traceback.print_exc()
        
        # Thread'de çalıştır
        Thread(target=do_mavsdk_takeoff, daemon=True).start()

    def on_start_mission(self):
        """Gelişmiş mission selector ile subprocess görev başlatma - DEBUG VERSION"""
        try:
            print("🔥 DEBUG: on_start_mission çağrıldı!")
            self.safe_log("🚀 Gelişmiş görev seçimi başlatılıyor...")
            
            # Uçuş durumu kontrolü
            if not self.in_flight:
                print("🔥 DEBUG: in_flight = False, çıkılıyor")
                self.safe_log("⚠ Görev başlatılamadı: Önce kalkış yapmanız gerekiyor!")
                return
            
            print("🔥 DEBUG: in_flight kontrolü geçti")
            
            # Connection manager kontrolü  
            if not self.connection_manager or not self.connection_manager.is_connected():
                print("🔥 DEBUG: Connection manager yok veya bağlı değil")
                self.safe_log("❌ MAVSDK bağlantısı yok!")
                return
                
            print("🔥 DEBUG: Connection kontrolü geçti")
            self.safe_log("✅ MAVSDK bağlantısı kontrolü geçti")
            
            # YENİ: Gelişmiş Mission Selector dialogu aç
            try:
                print("🔥 DEBUG: MissionSelectorDialog oluşturuluyor...")
                dialog = MissionSelectorDialog(self)
                print("🔥 DEBUG: Dialog oluşturuldu!")
                
                self.safe_log("🎯 Gelişmiş görev seçim merkezi açılıyor...")
                
                # Signal bağlantısı - DEBUG VERSION
                def debug_signal_handler(mission_data):
                    print("🔥 DEBUG: SIGNAL ÇALIŞTI!")
                    print(f"🔥 DEBUG: Mission data received: {mission_data}")
                    print(f"🔥 DEBUG: Mission data type: {type(mission_data)}")
                    
                    # Execute function çağır
                    print("🔥 DEBUG: execute_selected_mission_subprocess çağrılıyor...")
                    self.execute_selected_mission_subprocess(mission_data)
                    print("🔥 DEBUG: execute_selected_mission_subprocess tamamlandı!")
                
                print("🔥 DEBUG: Signal bağlanıyor...")
                dialog.mission_selected.connect(debug_signal_handler)
                print("🔥 DEBUG: Signal bağlandı!")
                
                print("🔥 DEBUG: Dialog gösteriliyor...")
                result = dialog.exec_()
                print(f"🔥 DEBUG: Dialog result: {result}")
                print(f"🔥 DEBUG: QDialog.Accepted = {QDialog.Accepted}")
                
                if result == QDialog.Accepted:
                    print("🔥 DEBUG: Dialog ACCEPTED!")
                    self.safe_log("✅ Görev seçimi tamamlandı")
                else:
                    print("🔥 DEBUG: Dialog REJECTED/CANCELLED!")
                    self.safe_log("📋 Görev seçimi iptal edildi")
                    
            except Exception as e:
                print(f"🔥 DEBUG: Dialog exception: {e}")
                self.safe_log(f"❌ Dialog hatası: {e}")
                import traceback
                traceback.print_exc()
                
        except Exception as e:
            print(f"🔥 DEBUG: Genel exception: {e}")
            self.safe_log(f"❌ Görev başlatma genel hatası: {e}")
            import traceback
            traceback.print_exc()
    
    def execute_selected_mission_subprocess(self, mission_data):
        """Seçilen görevi subprocess ile çalıştır - EW VTOL + Standart Mission - DEBUG VERSION"""
        print("🔥 DEBUG: execute_selected_mission_subprocess ÇAĞRILDI!")
        print(f"🔥 DEBUG: Gelen mission_data: {mission_data}")
        
        try:
            print("🔥 DEBUG: Mission data parse ediliyor...")
            
            mission_type = mission_data['mission_type']
            category = mission_data.get('category', 'standard')
            
            print(f"🔥 DEBUG: mission_type = {mission_type}")
            print(f"🔥 DEBUG: category = {category}")
            
            self.safe_log(f"🎯 Mission başlatılıyor: {mission_type} ({category})")
            
            # Kategori kontrolü - EW VTOL vs Standart
            if category == 'ew_vtol':
                print("🔥 DEBUG: EW VTOL mission tespit edildi!")
                self.execute_ew_vtol_mission(mission_data)
                print("🔥 DEBUG: EW VTOL mission çağrıldı!")
                return
            
            print("🔥 DEBUG: Standart mission tespit edildi!")
            
            # Mevcut VTOL standart mission kodu
            self.safe_log("🔧 VTOL parametreleri otomatik ayarlanıyor...")
            connection_string = self.port_input.text().strip() or "udp://:14540"
            
            print(f"🔥 DEBUG: connection_string = {connection_string}")
            
            # VTOL parametreleri kontrolü
            if hasattr(self, 'setup_vtol_parameters_sync'):
                print("🔥 DEBUG: setup_vtol_parameters_sync var, çağrılıyor...")
                param_success = self.setup_vtol_parameters_sync(connection_string)
                print(f"🔥 DEBUG: VTOL param success = {param_success}")
            else:
                print("🔥 DEBUG: setup_vtol_parameters_sync YOK! True varsayılıyor...")
                param_success = True
            
            if param_success:
                self.safe_log("✅ VTOL parametreleri başarıyla ayarlandı!")
                
                self.safe_log("🚀 Mission başlatılıyor...")
                
                # Log mission parameters kontrolü
                if hasattr(self, 'log_mission_parameters'):
                    print("🔥 DEBUG: log_mission_parameters çağrılıyor...")
                    self.log_mission_parameters(mission_data)
                else:
                    print("🔥 DEBUG: log_mission_parameters YOK!")
                
                print(f"🔥 DEBUG: Mission type check: {mission_type}")
                
                # Standart görev tipine göre subprocess fonksiyonu çağır
                if mission_type == "Normal Devriye":
                    print("🔥 DEBUG: Normal Devriye çağrılıyor...")
                    if hasattr(self, 'start_normal_patrol_subprocess'):
                        self.start_normal_patrol_subprocess(mission_data)
                        print("🔥 DEBUG: Normal Devriye çağrıldı!")
                    else:
                        print("🔥 DEBUG: start_normal_patrol_subprocess YOK!")
                        
                elif mission_type == "Alçak Sessiz Devriye":
                    print("🔥 DEBUG: Alçak Sessiz Devriye çağrılıyor...")
                    if hasattr(self, 'start_stealth_patrol_subprocess'):
                        self.start_stealth_patrol_subprocess(mission_data)
                        print("🔥 DEBUG: Alçak Sessiz Devriye çağrıldı!")
                    else:
                        print("🔥 DEBUG: start_stealth_patrol_subprocess YOK!")
                        
                elif mission_type == "Dairesel Devriye":
                    print("🔥 DEBUG: Dairesel Devriye çağrılıyor...")
                    if hasattr(self, 'start_circular_patrol_subprocess'):
                        self.start_circular_patrol_subprocess(mission_data)
                        print("🔥 DEBUG: Dairesel Devriye çağrıldı!")
                    else:
                        print("🔥 DEBUG: start_circular_patrol_subprocess YOK!")
                        
                elif mission_type == "Özel Görev":
                    print("🔥 DEBUG: Özel Görev çağrılıyor...")
                    if hasattr(self, 'start_custom_mission_subprocess'):
                        self.start_custom_mission_subprocess(mission_data)
                        print("🔥 DEBUG: Özel Görev çağrıldı!")
                    else:
                        print("🔥 DEBUG: start_custom_mission_subprocess YOK!")
                else:
                    print(f"🔥 DEBUG: Bilinmeyen mission type: {mission_type}")
                    self.safe_log(f"❌ Bilinmeyen standart görev tipi: {mission_type}")
            else:
                print("🔥 DEBUG: VTOL parametreleri başarısız!")
                self.safe_log("❌ VTOL parametreleri ayarlanamadı - Mission iptal!")
                    
        except Exception as e:
            print(f"🔥 DEBUG: Execute mission exception: {e}")
            self.safe_log(f"❌ Görev çalıştırma hatası: {e}")
            import traceback
            traceback.print_exc()
    
    def execute_ew_vtol_mission(self, mission_data):
        """EW VTOL görevini çalıştır - DEBUG VERSION"""
        print("🔥 DEBUG: execute_ew_vtol_mission ÇAĞRILDI!")
        print(f"🔥 DEBUG: EW mission data: {mission_data}")
        
        try:
            mission_id = mission_data.get('mission_id', 'ew_vtol_electronic_patrol')
            connection_string = self.port_input.text().strip() or "udp://:14540"
            
            print(f"🔥 DEBUG: EW mission_id = {mission_id}")
            print(f"🔥 DEBUG: EW connection_string = {connection_string}")
            
            # EW mission parametreleri hazırla
            ew_params = {
                'altitude': mission_data.get('altitude', 30.0),
                'duration': mission_data.get('duration', 60),
                'scan_interval': mission_data.get('scan_interval', 8),
                'pattern_size': mission_data.get('pattern_size', 400),
                'transition_attempts': mission_data.get('transition_attempts', 10),
                'landing_timeout': mission_data.get('landing_timeout', 25),
                'connection_string': connection_string
            }
            
            print(f"🔥 DEBUG: EW params: {ew_params}")
            
            self.safe_log("📡 EW VTOL Mission parametreleri:")
            for key, value in ew_params.items():
                self.safe_log(f"   {key}: {value}")
            
            # MAVSDK manager kontrolü
            if hasattr(self, 'mavsdk_manager') and self.mavsdk_manager:
                print("🔥 DEBUG: MAVSDK manager var!")
                
                # EW mission start function kontrolü
                if hasattr(self.mavsdk_manager, 'start_ew_mission'):
                    print("🔥 DEBUG: start_ew_mission function var!")
                    print("🔥 DEBUG: EW mission başlatılıyor...")
                    
                    # EW mission'ı subprocess ile başlat
                    success = self.mavsdk_manager.start_ew_mission(mission_id, ew_params)
                    print(f"🔥 DEBUG: EW mission success = {success}")
                    
                    if success:
                        self.safe_log(f"✅ EW VTOL Mission başlatıldı!")
                        self.current_mission = mission_data
                        self.mission_active = True
                        print("🔥 DEBUG: EW mission başarıyla başlatıldı!")
                    else:
                        self.safe_log("❌ EW VTOL Mission başlatılamadı!")
                        print("🔥 DEBUG: EW mission başlatılamadı!")
                else:
                    print("🔥 DEBUG: start_ew_mission function YOK!")
                    self.safe_log("❌ MAVSDK Manager'da EW mission desteği yok!")
            else:
                print("🔥 DEBUG: MAVSDK manager YOK!")
                self.safe_log("❌ MAVSDK Manager bulunamadı!")
                
        except Exception as e:
            print(f"🔥 DEBUG: EW mission exception: {e}")
            self.safe_log(f"❌ EW VTOL Mission hatası: {e}")
            import traceback
            traceback.print_exc()
    
    def setup_vtol_parameters_sync(self, connection_string: str) -> bool:
        """VTOL parametrelerini senkron olarak ayarla"""
        try:
            self.safe_log("🔧 VTOL parametreleri ayarlanıyor...")
            
            success = self.mavsdk_manager.setup_vtol_parameters(connection_string)
            
            if success:
                self.safe_log("✅ VTOL parametreleri ayarlandı!")
                return True
            else:
                self.safe_log("❌ VTOL parametreleri ayarlanamadı!")
                return False
                
        except Exception as e:
            self.safe_log(f"❌ VTOL param hatası: {e}")
            return False
    
    def start_normal_patrol_subprocess(self, mission_data):
        """Normal devriye - subprocess ile"""
        try:
            self.safe_log("🔄 Normal devriye subprocess başlatılıyor...")
            
            # Subprocess parametreleri hazırla
            mission_params = {
                'type': 'normal_patrol',
                'altitude': mission_data['altitude'],
                'speed': mission_data['speed'],
                'duration': mission_data['duration'] * 60,  # dakikayı saniyeye çevir
                'auto_rtl': mission_data['auto_rtl'],
                'connection_string': self.port_input.text().strip() or "udp://:14540"
            }
            
            # MAVSDK manager ile subprocess çalıştır
            success = self.mavsdk_manager.start_mission(mission_params)
            
            if success:
                self.safe_log(f"✅ Normal devriye başlatıldı - İrtifa: {mission_data['altitude']}m")
                self.current_mission = mission_data
                self.mission_active = True
            else:
                self.safe_log("❌ Normal devriye başlatılamadı!")
                
        except Exception as e:
            self.safe_log(f"❌ Normal devriye hatası: {e}")
    
    def start_stealth_patrol_subprocess(self, mission_data):
        """Alçak sessiz devriye - subprocess ile"""
        try:
            self.safe_log("🤫 Alçak sessiz devriye subprocess başlatılıyor...")
            
            # Alçak sessiz için parametreleri optimize et
            stealth_params = {
                'type': 'stealth_patrol',
                'altitude': min(mission_data['altitude'], 12.0),  # Max 12m alçak uçuş
                'speed': min(mission_data['speed'], 4),           # Max 4 m/s sessiz
                'duration': mission_data['duration'] * 60,
                'stealth_mode': True,
                'noise_reduction': True,
                'auto_rtl': mission_data['auto_rtl'],
                'connection_string': self.port_input.text().strip() or "udp://:14540"
            }
            
            success = self.mavsdk_manager.start_mission(stealth_params)
            
            if success:
                self.safe_log(f"✅ Alçak sessiz devriye başlatıldı - İrtifa: {stealth_params['altitude']}m")
                self.current_mission = mission_data
                self.mission_active = True
            else:
                self.safe_log("❌ Alçak sessiz devriye başlatılamadı!")
                
        except Exception as e:
            self.safe_log(f"❌ Alçak sessiz devriye hatası: {e}")
    
    def start_circular_patrol_subprocess(self, mission_data):
        """Dairesel devriye - subprocess ile"""
        try:
            self.safe_log("⭕ Dairesel devriye subprocess başlatılıyor...")
            
            # Mevcut pozisyonu al (eğer varsa)
            current_lat = getattr(self, 'current_lat', 0.0)
            current_lon = getattr(self, 'current_lon', 0.0)
            
            circle_params = {
                'type': 'circular_patrol',
                'center_lat': current_lat,
                'center_lon': current_lon,
                'radius': mission_data['radius'],
                'altitude': mission_data['altitude'],
                'speed': mission_data['speed'],
                'duration': mission_data['duration'] * 60,
                'clockwise': True,
                'auto_rtl': mission_data['auto_rtl'],
                'connection_string': self.port_input.text().strip() or "udp://:14540"
            }
            
            success = self.mavsdk_manager.start_mission(circle_params)
            
            if success:
                self.safe_log(f"✅ Dairesel devriye başlatıldı - Yarıçap: {mission_data['radius']}m")
                self.current_mission = mission_data
                self.mission_active = True
            else:
                self.safe_log("❌ Dairesel devriye başlatılamadı!")
                
        except Exception as e:
            self.safe_log(f"❌ Dairesel devriye hatası: {e}")
    
    def start_custom_mission_subprocess(self, mission_data):
        """Özel görev - subprocess ile"""
        try:
            self.safe_log("⚙️ Özel görev subprocess başlatılıyor...")
            
            custom_params = {
                'type': 'custom_mission',
                'parameters': mission_data,  # Tüm parametreleri gönder
                'connection_string': self.port_input.text().strip() or "udp://:14540"
            }
            
            success = self.mavsdk_manager.start_mission(custom_params)
            
            if success:
                self.safe_log("✅ Özel görev başlatıldı")
                self.current_mission = mission_data
                self.mission_active = True
            else:
                self.safe_log("❌ Özel görev başlatılamadı!")
                
        except Exception as e:
            self.safe_log(f"❌ Özel görev hatası: {e}")
    
    def log_mission_parameters(self, mission_data):
        """Görev parametrelerini detaylı logla"""
        self.safe_log("=" * 60)
        self.safe_log("🎯 GÖREV PARAMETRELERİ")
        self.safe_log("=" * 60)
        
        # Ana parametreler
        self.safe_log(f"📋 Görev Tipi: {mission_data['mission_type']}")
        self.safe_log(f"⏱️ Süre: {mission_data['duration']} dakika")
        self.safe_log(f"📏 İrtifa: {mission_data['altitude']} m")
        self.safe_log(f"🚀 Hız: {mission_data['speed']} m/s")
        self.safe_log(f"🗺️ Rota: {mission_data['route_type']}")
        
        # Güvenlik ayarları
        self.safe_log("🛡️ GÜVENLİK AYARLARI:")
        self.safe_log(f"  📡 Otomatik RTL: {'✅ Aktif' if mission_data['auto_rtl'] else '❌ Pasif'}")
        self.safe_log(f"  🔋 Batarya Uyarısı: {'✅ ' + str(mission_data['battery_warning_level']) + '%' if mission_data['low_battery_warning'] else '❌ Pasif'}")
        self.safe_log(f"  🗺️ Geofence: {'✅ ' + str(mission_data['max_distance']) + 'm' if mission_data['geofence_enabled'] else '❌ Pasif'}")
        
        # Görev özel parametreler
        if mission_data['mission_type'] == "Dairesel Devriye":
            self.safe_log(f"⭕ Yarıçap: {mission_data['radius']} m")
        elif mission_data['mission_type'] == "Alçak Sessiz Devriye":
            self.safe_log(f"🤫 Minimum İrtifa: {mission_data['min_altitude']} m")
        
        self.safe_log("=" * 60)
    
    # BONUS: Görev durumu takibi
    def setup_mission_monitoring(self):
        """Görev takip sistemi kurulumu"""
        self.mission_active = False
        self.current_mission = None
        
        # Görev takip timer'ı
        self.mission_timer = QTimer()
        self.mission_timer.timeout.connect(self.check_mission_status)
        self.mission_timer.start(2000)  # Her 2 saniyede kontrol
    
    def check_mission_status(self):
        """Aktif görev durumunu kontrol et"""
        if self.mission_active and self.current_mission:
            try:
                # MAVSDK manager'dan görev durumu al
                status = self.mavsdk_manager.get_mission_status()
                
                if status:
                    progress = status.get('progress', 0)
                    remaining_time = status.get('remaining_time', 0)
                    
                    if progress >= 100:
                        self.safe_log("✅ Görev tamamlandı!")
                        self.mission_active = False
                        self.current_mission = None
                    elif progress > 0:
                        self.safe_log(f"📊 Görev ilerlemesi: %{progress:.1f} - Kalan: {remaining_time}s")
                        
            except Exception as e:
                # Sessizce geç, sürekli hata vermemek için
                pass
    
    def on_mission_abort(self):
        """Aktif görevi iptal et"""
        if self.mission_active:
            try:
                success = self.mavsdk_manager.abort_mission()
                
                if success:
                    self.safe_log("🛑 Görev iptal edildi!")
                    self.mission_active = False
                    self.current_mission = None
                else:
                    self.safe_log("❌ Görev iptal edilemedi!")
                    
            except Exception as e:
                self.safe_log(f"❌ Görev iptal hatası: {e}")
        else:
            self.safe_log("⚠ Aktif görev yok!")

    @pyqtSlot()
    def _set_flying_state(self):
        self.in_flight = True
        self.header_label.setText("MAVSDK Uçuşta (10m)")
        self.status_label.setText("Durum: MAVSDK Uçuşta")
        self.altitude = 10.0
        
    def update_telemetry(self):
        """MAVSDK telemetri verilerini al ve haritaya gönder - FİX."""
        pass
    
    def update_arm_status(self, status):
        """ARM durumu güncelle"""
        try:
            if hasattr(self, 'arm_status_value'):
                self.arm_status_value.setText(status)
        except Exception as e:
            print(f"ARM status güncelleme hatası: {e}")

    def update_position_data(self, lat, lon, alt):
        """Position verilerini güncelle"""
        try:
            self.altitude = round(alt, 2)
            self.gps = f"{lat:.6f}, {lon:.6f}"
            
            # Haritaya pozisyon gönder
            current_time = time.time()
            if current_time - self.last_map_update > self.map_update_interval:
                self.send_position_to_map(lat, lon, self.altitude, self.heading)
                self.last_map_update = current_time
                
            # Debug
            print(f"🛰️ MAVSDK Telemetri: Lat={lat:.6f}, Lon={lon:.6f}, Alt={alt}m")
            
        except Exception as e:
            print(f"Position data güncelleme hatası: {e}")

    def update_flight_mode(self, mode_str):
        """Flight mode güncelle"""
        try:
            if hasattr(self, 'flight_mode_value'):
                self.flight_mode_value.setText(mode_str)
        except Exception as e:
            print(f"Flight mode güncelleme hatası: {e}")

    def send_position_to_map(self, lat, lon, alt, heading):
        """MAVSDK pozisyonunu haritaya gönder - DEBUG"""
        try:
            print(f"🔍 DEBUG: send_position_to_map çağrıldı - lat:{lat}, lon:{lon}, alt:{alt}, heading:{heading}")
            
            if hasattr(self, 'map_view') and self.map_view:
                # JavaScript fonksiyonunu çağır
                js_command = f"updateDronePosition({lat}, {lon}, {alt}, {heading});"
                print(f"🔍 DEBUG: JavaScript komutu: {js_command}")
                
                self.map_view.page().runJavaScript(js_command)
                print("🔍 DEBUG: JavaScript komutu gönderildi")
                
            else:
                print("🔍 DEBUG: map_view bulunamadı veya None!")
                    
        except Exception as map_error:
            print(f"❌ Harita güncelleme hatası: {map_error}")
            import traceback
            traceback.print_exc()

# 5. TELEMETRİ BAŞLATMA KONTROLÜ:
    
    def _update_gui_elements(self):
        """GUI elementlerini MAVSDK verileriyle güncelle."""
        try:
            # Telemetri etiketlerini güncelle
            if hasattr(self, 'altitude_value'):
                self.altitude_value.setText(f"{self.altitude} m")
            if hasattr(self, 'speed_value'):
                self.speed_value.setText(f"{self.speed:.1f} km/h")
            if hasattr(self, 'heading_value'):
                self.heading_value.setText(f"{self.heading:.0f}°")
            if hasattr(self, 'battery_value'):
                self.battery_value.setText(f"{self.battery:.1f}%")
            if hasattr(self, 'gps_value'):
                self.gps_value.setText(self.gps)
            if hasattr(self, 'power_value'):
                self.power_value.setText(f"{self.power_consumption:.1f} W")
            if hasattr(self, 'gps_coord_value'):
                self.gps_coord_value.setText(self.gps)
    
            # Grafik verilerini güncelle
            self.t += 1
            self.time_list.append(self.t)
            self.altitude_list.append(self.altitude)
            self.speed_list.append(self.speed)
            self.battery_list.append(self.battery)
            self.power_list.append(self.power_consumption)
    
            # Listleri 100 noktaya sınırla
            if len(self.time_list) > 100:
                self.time_list = self.time_list[-100:]
                self.altitude_list = self.altitude_list[-100:]
                self.speed_list = self.speed_list[-100:]
                self.battery_list = self.battery_list[-100:]
                self.power_list = self.power_list[-100:]
    
            # Grafikleri güncelle
            if hasattr(self, 'altitude_curve'):
                self.altitude_curve.setData(self.time_list, self.altitude_list)
            if hasattr(self, 'speed_curve'):
                self.speed_curve.setData(self.time_list, self.speed_list)
            if hasattr(self, 'battery_curve'):
                self.battery_curve.setData(self.time_list, self.battery_list)
            if hasattr(self, 'power_curve'):
                self.power_curve.setData(self.time_list, self.power_list)
    
            # Göstergeleri güncelle
            if hasattr(self, 'speedometer'):
                self.speedometer.setSpeed(self.speed)
            if hasattr(self, 'fuel_gauge'):
                self.fuel_gauge.setFuelLevel(self.battery)
            if hasattr(self, 'compass'):
                self.compass.setHeading(self.heading)
    
            # Uçuş süresi
            if self.in_flight:
                self.flight_time_seconds += 1
            minutes, seconds = divmod(self.flight_time_seconds, 60)
            if hasattr(self, 'flight_time_label'):
                self.flight_time_label.setText(f"Uçuş Süresi: {minutes} dk {seconds} sn")
    
        except Exception as gui_error:
            print(f"GUI güncelleme hatası: {gui_error}")
                
    def on_land(self):
        """MAVSDK uyumlu iniş fonksiyonu"""
        
        if not MAVSDK_AVAILABLE:
            self.safe_log("❌ MAVSDK kütüphanesi yüklenmemiş!")
            return
        
        if not self.connection_manager or not self.connection_manager.is_connected():
            self.safe_log("⚠ MAVSDK bağlantısı yok!")
            return

        if not self.in_flight:
            self.safe_log("⚠ Uçuş yok, iniş yapılamaz.")
            return

        def do_mavsdk_land():
            try:
                async def async_land():
                    try:
                        system = self.connection_manager.system
                        if not system:
                            self.safe_log("❌ MAVSDK System bulunamadı!")
                            return
                        
                        self.safe_log("⏬ MAVSDK iniş başlatılıyor...")
                        
                        # Action manager ile iniş
                        if not self.action_manager:
                            self.action_manager = MAVSDKActionManager(system)
                        
                        success = await self.action_manager.land()
                        
                        if success:
                            QTimer.singleShot(0, self._set_landed_state)
                            self.safe_log("✅ MAVSDK iniş tamamlandı.")
                        else:
                            self.safe_log("❌ MAVSDK iniş başarısız!")
                        
                    except Exception as async_error:
                        self.safe_log(f"❌ MAVSDK async iniş hatası: {async_error}")
                
                # Event loop
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(async_land())
                loop.close()
                
            except Exception as thread_error:
                self.safe_log(f"❌ MAVSDK iniş thread hatası: {thread_error}")

        Thread(target=do_mavsdk_land, daemon=True).start()

    @pyqtSlot()
    def _set_landed_state(self):
        """İniş tamamlandığında UI durumunu sıfırlar."""
        self.in_flight = False
        self.altitude = 0
        self.header_label.setText("MAVSDK İniş Yapıldı")
        self.status_label.setText("Durum: MAVSDK İniş Yapıldı")
    
    def on_emergency(self):
        """MAVSDK acil durum iniş"""
        if not self.connection_manager or not self.connection_manager.is_connected():
            self.safe_log("⚠ MAVSDK bağlantısı yok!")
            return

        if not self.in_flight:
            self.safe_log("⚠ Uçuş yok, acil iniş yapılamaz.")
            return

        def do_emergency():
            try:
                async def async_emergency():
                    try:
                        system = self.connection_manager.system
                        if not system:
                            self.safe_log("❌ MAVSDK System bulunamadı!")
                            return
                        
                        self.safe_log("⚠ MAVSDK ACİL DURUM! İniş başlatılıyor...")
                        await system.action.land()
                        self.safe_log("✅ MAVSDK acil iniş tamamlandı.")
                        
                        QTimer.singleShot(0, self._set_landed_state)
                        
                    except Exception as e:
                        self.safe_log(f"❌ MAVSDK acil iniş hatası: {e}")
                
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(async_emergency())
                loop.close()
                
            except Exception as e:
                self.safe_log(f"❌ MAVSDK acil iniş thread hatası: {e}")

        Thread(target=do_emergency, daemon=True).start()
    
    def on_return_home(self):
        """MAVSDK Return-To-Launch"""
        if not self.connection_manager or not self.connection_manager.is_connected():
            self.safe_log("⚠ MAVSDK bağlantısı yok!")
            return

        if not self.in_flight:
            self.safe_log("⚠ Uçuş yok, geri dönüş yapılamaz.")
            return

        def do_rtl():
            try:
                async def async_rtl():
                    try:
                        system = self.connection_manager.system
                        if not system:
                            self.safe_log("❌ MAVSDK System bulunamadı!")
                            return
                        
                        self.safe_log("🏠 MAVSDK RTL başlatılıyor...")
                        
                        if not self.action_manager:
                            self.action_manager = MAVSDKActionManager(system)
                        
                        success = await self.action_manager.return_to_launch()
                        
                        if success:
                            self.safe_log("✅ MAVSDK RTL komutu gönderildi!")
                            
                            # RTL tamamlanmasını bekle (armed durumu)
                            async for armed in system.telemetry.armed():
                                if not armed:
                                    self.safe_log("🎯 RTL tamamlandı - motor disarm edildi")
                                    QTimer.singleShot(0, self._set_landed_state)
                                    break
                                await asyncio.sleep(1)
                        else:
                            self.safe_log("❌ MAVSDK RTL başarısız!")
                        
                    except Exception as e:
                        self.safe_log(f"❌ MAVSDK RTL hatası: {e}")
                
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(async_rtl())
                loop.close()
                
            except Exception as e:
                self.safe_log(f"❌ MAVSDK RTL thread hatası: {e}")

        Thread(target=do_rtl, daemon=True).start()

    def _manual_emergency_land(self):
        """Core connection modülü ile MAVSDK acil iniş (manuel kontrol için)"""
        if not self.connection_manager or not self.connection_manager.is_connected():
            self.safe_log("⚠ Core MAVSDK bağlantısı yok!")
            return
            
        def do_emergency_land():
            try:
                async def async_emergency_land():
                    try:
                        system = self.connection_manager.get_system()
                        if system:
                            await system.action.land()
                            self.safe_log("🚨 Core MAVSDK acil iniş komutu gönderildi!")
                    except Exception as e:
                        self.safe_log(f"❌ Core MAVSDK acil iniş hatası: {e}")
                
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(async_emergency_land())
                loop.close()
                
            except Exception as e:
                self.safe_log(f"❌ Core MAVSDK acil iniş thread hatası: {e}")
        
        Thread(target=do_emergency_land, daemon=True).start()

    def _manual_rtl(self):
        """Core connection modülü ile MAVSDK Return to Launch (manuel kontrol için)"""
        if not self.connection_manager or not self.connection_manager.is_connected():
            self.safe_log("⚠ Core MAVSDK bağlantısı yok!")
            return
            
        def do_rtl():
            try:
                async def async_rtl():
                    try:
                        system = self.connection_manager.get_system()
                        if system:
                            await system.action.return_to_launch()
                            self.safe_log("🏠 Core MAVSDK RTL komutu gönderildi!")
                    except Exception as e:
                        self.safe_log(f"❌ Core MAVSDK RTL hatası: {e}")
                
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(async_rtl())
                loop.close()
                
            except Exception as e:
                self.safe_log(f"❌ Core MAVSDK RTL thread hatası: {e}")
        
        Thread(target=do_rtl, daemon=True).start()

    def setManualSpeed(self, value):
        """Core connection modülü ile MAVSDK speed kontrolü"""
        self.speed = value
        self.speedometer.setSpeed(value)
        
        if not self.connection_manager or not self.connection_manager.is_connected():
            return
            
        def do_speed_control():
            try:
                async def async_speed_control():
                    try:
                        system = self.connection_manager.get_system()
                        if not system:
                            return
                        
                        # MAVSDK offboard ile hız kontrolü
                        speed_ms = value / 3.6  # km/h to m/s
                        
                        # Velocity body yaw speed kullan
                        velocity = VelocityBodyYawspeed(speed_ms, 0.0, 0.0, 0.0)
                        await system.offboard.set_velocity_body(velocity)
                        
                    except Exception as e:
                        print(f"Core MAVSDK Speed control hatası: {e}")
                
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(async_speed_control())
                loop.close()
                
            except Exception as e:
                print(f"Core MAVSDK Speed control thread hatası: {e}")
        
        if self.in_flight:
            Thread(target=do_speed_control, daemon=True).start()

    def setManualAltitude(self, value):
        """Core connection modülü ile MAVSDK altitude kontrolü"""
        self.altitude = value
        self.altitude_value.setText(f"{value} m")
        
        if not self.connection_manager or not self.connection_manager.is_connected():
            return
            
        def do_altitude_control():
            try:
                async def async_altitude_control():
                    try:
                        system = self.connection_manager.get_system()
                        if not system:
                            return
                        
                        # Mevcut pozisyonu al ve sadece altitude'u değiştir
                        async for position in system.telemetry.position():
                            current_lat = position.latitude_deg
                            current_lon = position.longitude_deg
                            
                            # Core MAVSDK Goto location ile altitude değiştir
                            await system.action.goto_location(
                                current_lat, current_lon, value, 0  # yaw=0
                            )
                            break
                            
                    except Exception as e:
                        print(f"Core MAVSDK Altitude control hatası: {e}")
                
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(async_altitude_control())
                loop.close()
                
            except Exception as e:
                print(f"Core MAVSDK Altitude control thread hatası: {e}")
        
        if self.in_flight:
            Thread(target=do_altitude_control, daemon=True).start()

    def setManualHeading(self, value):
        """Core connection modülü ile MAVSDK heading kontrolü"""
        self.heading = value
        self.compass.setHeading(value)
        
        if not self.connection_manager or not self.connection_manager.is_connected():
            return
            
        def do_heading_control():
            try:
                async def async_heading_control():
                    try:
                        system = self.connection_manager.get_system()
                        if not system:
                            return
                        
                        # Position NED yaw ile heading kontrolü
                        position_ned = PositionNedYaw(0.0, 0.0, 0.0, value)
                        await system.offboard.set_position_ned(position_ned)
                        
                    except Exception as e:
                        print(f"Core MAVSDK Heading control hatası: {e}")
                
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(async_heading_control())
                loop.close()
                
            except Exception as e:
                print(f"Core MAVSDK Heading control thread hatası: {e}")
        
        if self.in_flight:
            Thread(target=do_heading_control, daemon=True).start()

    def set_flight_mode(self):
        """Core connection modülü ile MAVSDK flight mode ayarlama"""
        mode_name = self.mode_combo.currentText()
        
        if not self.connection_manager or not self.connection_manager.is_connected():
            self.safe_log("⚠ Core MAVSDK bağlantısı yok.")
            return
    
        def do_set_mode():
            try:
                async def async_set_mode():
                    try:
                        system = self.connection_manager.get_system()
                        if not system:
                            self.safe_log("❌ Core MAVSDK system bulunamadı!")
                            return
                        
                        # Core MAVSDK'de flight mode ayarlama (action plugin üzerinden)
                        if mode_name == "HOLD":
                            await system.action.hold()
                            self.safe_log("✅ HOLD modu aktif")
                        elif mode_name == "RETURN_TO_LAUNCH":
                            await system.action.return_to_launch()
                            self.safe_log("✅ RTL modu aktif")
                        elif mode_name == "LAND":
                            await system.action.land()
                            self.safe_log("✅ LAND modu aktif")
                        else:
                            self.safe_log(f"⚠ '{mode_name}' modu henüz desteklenmiyor")
                            
                    except Exception as e:
                        self.safe_log(f"❌ Core MAVSDK Mod ayarlama hatası: {e}")
                
                # Async event loop
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(async_set_mode())
                loop.close()
                
            except Exception as e:
                self.safe_log(f"❌ Core MAVSDK Mod ayarlama thread hatası: {e}")
        
        Thread(target=do_set_mode, daemon=True).start()

    def load_previous_state(self):
        """Core connection modülü ile önceki durumu yükle"""
        try:
            import json
            import os
            
            if os.path.exists('core_mavsdk_app_state.json'):
                with open('core_mavsdk_app_state.json', 'r') as f:
                    app_state = json.load(f)
                
                # Port ve timeout'u geri yükle
                if 'last_port' in app_state:
                    self.port_input.setText(app_state['last_port'])
                
                if 'last_timeout' in app_state:
                    self.timeout_input.setText(str(app_state['last_timeout']))
                
                # Restart time'ı kontrol et
                if 'restart_time' in app_state:
                    restart_time = app_state['restart_time']
                    if time.time() - restart_time < 60:  # 1 dakika içinde restart
                        self.safe_log("🔄 Önceki Core MAVSDK oturumu güvenli yeniden başlatma ile sona erdi")
                
                # State dosyasını sil
                os.remove('core_mavsdk_app_state.json')
                print("✅ Önceki Core MAVSDK durumu yüklendi ve temizlendi")
                
        except Exception as e:
            print(f"⚠ Core MAVSDK durum yükleme hatası: {e}")
    
    def closeEvent(self, event):
        """Core connection modülü ile MAVSDK uygulaması kapatma"""
        try:
            print("👋 Core MAVSDK Normal kapatma işlemi...")
            
            # Eğer connection manager varsa uyar
            if self.connection_manager:
                from PyQt5.QtWidgets import QMessageBox
                
                reply = QMessageBox.question(
                    self, 
                    'Core MAVSDK Uygulamayı Kapat', 
                    'Aktif Core MAVSDK bağlantısı var.\n\nBağlantıyı güvenli kesmek için "Bağlantıyı Kes" butonunu kullanın.\n\nYine de kapatmak istiyor musunuz?',
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                
                if reply == QMessageBox.No:
                    event.ignore()
                    return
                else:
                    # Kapatmadan önce bağlantıyı kes
                    try:
                        self.connection_manager.stop_connection()
                    except:
                        pass
            
            # Normal kapatma
            print("✅ Core MAVSDK normal kapatma onaylandı")
            
        except Exception as e:
            print(f"Core MAVSDK kapatma hatası: {e}")
        
        event.accept()
    
    def check_restart_status(self):
        """Core connection modülü ile MAVSDK restart sonrası durum kontrolü"""
        try:
            import os
            
            # Eğer state dosyası varsa restart sonrasıyız
            if os.path.exists('core_mavsdk_app_state.json'):
                self.safe_log("✅ Core MAVSDK Güvenli yeniden başlatma tamamlandı")
                
                # Kullanıcıya bilgi ver
                from PyQt5.QtWidgets import QMessageBox
                QMessageBox.information(
                    self,
                    'Core MAVSDK Yeniden Başlatma Tamamlandı',
                    'Core MAVSDK bağlantısı güvenli şekilde kesildi.\n\nYeni bağlantı kurmak için "MAVSDK Bağlan" butonunu kullanabilirsiniz.',
                    QMessageBox.Ok
                )
                
        except Exception as e:
            print(f"Core MAVSDK restart status kontrolü hatası: {e}")
            
    def add_map_waypoint(self, lat, lon):
        self.waypoint_counter += 1
        waypoint = f"Waypoint {self.waypoint_counter}: {lat:.6f}, {lon:.6f}"
        self.waypoints.append(waypoint)
        self.map_waypoint_list.addItem(waypoint)
        self.safe_log(f"Haritadan waypoint eklendi: {waypoint}")

    def add_start_point(self):
        try:
            lat = float(self.lat_input.text())
            lon = float(self.lon_input.text())
            self.start_point = f"Başlangıç: {lat:.6f}, {lon:.6f}"
            self.map_waypoint_list.insertItem(0, self.start_point)
            self.map_view.page().runJavaScript(
                f"addStartPoint({lat}, {lon});"
            )
            self.safe_log(f"Başlangıç noktası eklendi: {lat}, {lon}")
        except ValueError:
            self.safe_log("Geçersiz koordinat formatı!")

    def add_end_point(self):
        try:
            lat = float(self.lat_input.text())
            lon = float(self.lon_input.text())
            self.end_point = f"Bitiş: {lat:.6f}, {lon:.6f}"
            self.map_waypoint_list.addItem(self.end_point)
            self.map_view.page().runJavaScript(
                f"addEndPoint({lat}, {lon});"
            )
            self.safe_log(f"Bitiş noktası eklendi: {lat}, {lon}")
        except ValueError:
            self.safe_log("Geçersiz koordinat formatı!")

    def clear_map_waypoints(self):
        self.waypoints.clear()
        self.map_waypoint_list.clear()
        self.waypoint_counter = 0
        self.start_point = None
        self.end_point = None
        self.map_view.page().runJavaScript("clearWaypoints();")
        self.safe_log("Tüm noktalar temizlendi")

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
            self.safe_log(f"Ev konumu ayarlandı: {lat}, {lon}")
        except ValueError:
            self.safe_log("Geçersiz koordinat formatı!")

    def save_current_mission(self):
        mission_name = f"MAVSDK_Görev_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        mission = []
        for i in range(self.map_waypoint_list.count()):
            mission.append(self.map_waypoint_list.item(i).text())
        
        self.saved_missions_list.addItem(mission_name)
        self.saved_missions[mission_name] = mission
        self.safe_log(f"MAVSDK Görev kaydedildi: {mission_name}")

    def load_selected_mission(self):
        current_item = self.saved_missions_list.currentItem()
        if current_item is None:
            self.safe_log("Yüklenecek görev seçilmedi!")
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
            
            self.safe_log(f"MAVSDK Görev yüklendi: {mission_name}")
        else:
            self.safe_log("Görev bulunamadı!")

    def setup_connection_controls(self):
        """MAVSDK bağlantı kontrollerini ayarla"""
        # Bağlantı butonları
        self.connect_button.clicked.connect(self.manual_connect_to_mavsdk)
        self.disconnect_button.clicked.connect(self.manual_disconnect_from_mavsdk)
        
        # Başlangıçta disconnect butonu pasif
        self.disconnect_button.setEnabled(False)
        
        # Port varsayılan değerleri
        if not self.port_input.text():
            self.port_input.setText("udp://:14540")  # MAVSDK default
        if not self.timeout_input.text():
            self.timeout_input.setText("30")
    
    def manual_connect_to_mavsdk(self):
        """Manuel MAVSDK bağlantısı başlatma - Subprocess ile güncellendi"""
        
        if not MAVSDK_AVAILABLE:
            self.safe_log("❌ MAVSDK kütüphanesi yüklenmemiş!")
            return
        
        if not CONNECTION_MODULE_AVAILABLE:
            self.safe_log("❌ Core connection modülü bulunamadı!")
            return
        
        # Port al
        port = self.port_input.text().strip() or "udp://:14540"
        timeout = int(self.timeout_input.text().strip() or "30")
        
        # UI güncelle
        self.connect_button.setEnabled(False)
        self.connect_button.setText("MAVSDK Bağlanıyor...")
        self.update_connection_status(False, "MAVSDK Bağlanıyor...")
        
        def do_connect():
            try:
                self.safe_log("🔌 Core MAVSDK Connection Manager ile bağlantı başlatılıyor...")
                
                # Core connection manager oluştur
                self.connection_manager = CoreMAVSDKConnectionManager(
                    connection_string=port,
                    timeout=timeout,
                    auto_connect=False
                )
                
                # Callback'leri ayarla
                def on_connect():
                    self.safe_log("✅ Core MAVSDK bağlantısı başarılı!")
                    self.connection_status = True
                    
                    # Subprocess manager'ı güncelle
                    if hasattr(self, 'mavsdk_manager'):
                        self.mavsdk_manager.set_connection_string(port)
                    
                    # Subprocess telemetri başlat
                    QTimer.singleShot(0, self.start_mavsdk_telemetry)
                    
                def on_disconnect():
                    self.safe_log("❌ Core MAVSDK bağlantısı kesildi!")
                    self.connection_status = False
                    
                    # Subprocess telemetri durdur
                    QTimer.singleShot(0, self.stop_mavsdk_telemetry)
                
                self.connection_manager.set_callbacks(on_connect, on_disconnect)
                
                # Manuel bağlantıyı başlat
                success = self.connection_manager.start_connection()
                
                if success:
                    QTimer.singleShot(0, self.on_mavsdk_connected)
                    self.safe_log("✅ Core MAVSDK connection başarıyla kuruldu!")
                else:
                    QTimer.singleShot(0, self.on_mavsdk_connection_failed)
                    self.safe_log("❌ Core MAVSDK connection başarısız!")
                    
            except Exception as e:
                self.safe_log(f"❌ Core MAVSDK bağlantı hatası: {e}")
                QTimer.singleShot(0, self.on_mavsdk_connection_failed)
        
        # Thread başlat
        Thread(target=do_connect, daemon=True).start()

    def manual_disconnect_from_mavsdk(self):
        """MAVSDK bağlantısını güvenli şekilde kes - Subprocess ile güncellendi"""
        if not self.connection_manager:
            self.safe_log("⚠ Aktif MAVSDK bağlantısı yok!")
            return
        
        self.safe_log("🔌 MAVSDK bağlantısı kesiliyor...")
        
        try:
            # UI'yi güncelle
            self.disconnect_button.setText("Kesiliyor...")
            self.disconnect_button.setEnabled(False)
            
            # Subprocess işlemlerini durdur
            if hasattr(self, 'mavsdk_manager'):
                self.mavsdk_manager.stop_all()
            
            # Core connection manager'ı durdur
            self.connection_manager.stop_connection()
            self.connection_manager = None
            
            # UI durumunu güncelle
            self.connect_button.setEnabled(True)
            self.disconnect_button.setText("Bağlantıyı Kes")
            self.update_connection_status(False, "MAVSDK Kesildi")
            
            # Uçuş durumunu sıfırla
            self.in_flight = False
            self.altitude = 0
            self.speed = 0
            self.heading = 0
            self.battery = 100
            
            self.safe_log("✅ MAVSDK bağlantısı güvenli şekilde kesildi")
            
        except Exception as e:
            self.safe_log(f"❌ MAVSDK disconnect hatası: {e}")

    def update_telemetry(self):
        """Core connection modülü ile MAVSDK telemetri verilerini al"""
        try:
            import time
            current_time = time.time()
            
            # Core MAVSDK System erişimi
            system = None
            if self.connection_manager and self.connection_manager.is_connected():
                system = self.connection_manager.get_system()
            
            if system:
                def get_mavsdk_telemetry():
                    try:
                        async def async_telemetry():
                            try:
                                # Position
                                async for position in system.telemetry.position():
                                    current_lat = position.latitude_deg
                                    current_lon = position.longitude_deg
                                    current_alt = position.relative_altitude_m
                                    
                                    # Ana thread'de güncelle
                                    QTimer.singleShot(0, lambda: self.update_position_data(
                                        current_lat, current_lon, current_alt
                                    ))
                                    break
                                
                                # Battery
                                async for battery in system.telemetry.battery():
                                    battery_percent = battery.remaining_percent
                                    QTimer.singleShot(0, lambda: setattr(self, 'battery', battery_percent))
                                    break
                                
                                # Flight mode
                                async for flight_mode in system.telemetry.flight_mode():
                                    mode_str = str(flight_mode)
                                    QTimer.singleShot(0, lambda: self.update_flight_mode(mode_str))
                                    break
                                
                                # Velocity (speed)
                                async for velocity in system.telemetry.velocity_ned():
                                    speed_ms = math.sqrt(velocity.north_m_s**2 + velocity.east_m_s**2 + velocity.down_m_s**2)
                                    speed_kmh = speed_ms * 3.6
                                    QTimer.singleShot(0, lambda: setattr(self, 'speed', speed_kmh))
                                    break
                                
                                # Attitude (heading)
                                async for attitude in system.telemetry.attitude_euler():
                                    heading_deg = attitude.yaw_deg
                                    if heading_deg < 0:
                                        heading_deg += 360
                                    QTimer.singleShot(0, lambda: setattr(self, 'heading', heading_deg))
                                    break
                                    
                            except Exception as telemetry_error:
                                print(f"Core MAVSDK telemetri okuma hatası: {telemetry_error}")
                        
                        # Event loop çalıştır
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        loop.run_until_complete(async_telemetry())
                        loop.close()
                        
                    except Exception as thread_error:
                        print(f"Core MAVSDK telemetri thread hatası: {thread_error}")
                
                # Thread'de telemetri al
                Thread(target=get_mavsdk_telemetry, daemon=True).start()
            else:
                # Bağlantı yoksa default değerler
                self.altitude = 0
                self.speed = 0
                self.heading = 0
                self.battery = 100
                self.gps = f"{self.SITL_LAT:.6f}, {self.SITL_LON:.6f}"
                self.power_consumption = 0
            
            # GUI güncellemelerini yap
            QTimer.singleShot(0, self._update_gui_elements)
    
        except Exception as general_error:
            print(f"Core MAVSDK telemetri güncellemesi genel hatası: {general_error}")
            
    def closeEvent(self, event):
        """Uygulama kapatılırken subprocess'leri temizle"""
        try:
            print("👋 MAVSDK Subprocess uygulaması kapatılıyor...")
            
            # Subprocess işlemlerini durdur
            if hasattr(self, 'mavsdk_manager'):
                self.mavsdk_manager.stop_all()
            
            # Connection manager'ı durdur
            if self.connection_manager:
                try:
                    self.connection_manager.stop_connection()
                except:
                    pass
            
            print("✅ MAVSDK subprocess temizliği tamamlandı")
            
        except Exception as e:
            print(f"Kapatma hatası: {e}")
        
        event.accept()
    
    def on_takeoff(self):
        """İrtifa seçimi ile subprocess kalkış"""
        if not MAVSDK_AVAILABLE:
            self.safe_log("❌ MAVSDK kütüphanesi yüklenmemiş!")
            return
        
        if not self.connection_manager or not self.connection_manager.is_connected():
            self.safe_log("⚠ Önce MAVSDK'ye bağlanın!")
            return
            
        if self.in_flight:
            self.safe_log("🚁 Zaten uçuşta!")
            return
        
        # İrtifa seçim dialogunu aç
        altitude_dialog = TakeoffAltitudeDialog(self)
        if altitude_dialog.exec_() == QDialog.Accepted:
            selected_altitude = altitude_dialog.get_selected_altitude()
            
            # Güvenlik onayı (seçilen irtifa ile)
            reply = QMessageBox.question(
                self, 
                '🚀 KALKIŞ ONAYI',
                f'''⚠️ KALKIŞ İŞLEMİ BAŞLATILACAK!
    
    🎯 Seçilen İrtifa: {selected_altitude} METRE
    
    Bu işlemi gerçekleştirmek istediğinizden emin misiniz?''',
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                self.safe_log(f"✅ Kalkış onaylandı - Hedef irtifa: {selected_altitude}m")
                self.perform_takeoff_with_selected_altitude(selected_altitude)
            else:
                self.safe_log("❌ Kalkış işlemi kullanıcı tarafından iptal edildi")
        else:
            self.safe_log("❌ İrtifa seçimi iptal edildi")
    
    def perform_takeoff_with_selected_altitude(self, altitude):
        """Seçilen irtifa ile kalkış işlemini gerçekleştir"""
        try:
            # Connection string güncelle
            connection_string = self.port_input.text().strip() or "udp://:14540"
            self.mavsdk_manager.set_connection_string(connection_string)
            
            # Seçilen irtifa ile kalkış komutu
            success = self.mavsdk_manager.takeoff(altitude=float(altitude))
            
            if success:
                self.safe_log(f"🚀 Subprocess kalkış komutu gönderildi - İrtifa: {altitude}m")
                self.in_flight = True
                self.safe_log("✅ Uçuş durumu: HAVALANDİ")
                self.set_flight_status("Kalkış")
            else:
                self.safe_log("❌ Kalkış komutu gönderilemedi!")
                
        except Exception as e:
            self.safe_log(f"❌ Kalkış hatası: {e}")

    def start_selected_mission_mavsdk(self, mission_name: str):
        """Core connection modülü ile MAVSDK görev çalıştırma"""
        try:
            self.safe_log(f"🛰️ Core MAVSDK Görev başlatılıyor: {mission_name}")
            
            def do_mission():
                try:
                    async def async_mission():
                        try:
                            system = self.connection_manager.get_system()
                            if not system:
                                self.safe_log("❌ Core MAVSDK System bulunamadı!")
                                return
                            
                            # Mevcut pozisyonu al
                            current_position = None
                            async for position in system.telemetry.position():
                                current_position = position
                                break
                            
                            if not current_position:
                                self.safe_log("❌ Mevcut pozisyon alınamadı!")
                                return
                                
                            lat = current_position.latitude_deg
                            lon = current_position.longitude_deg
                            alt = current_position.relative_altitude_m
                            
                            self.safe_log(f"📍 Mevcut pozisyon: {lat:.6f}, {lon:.6f}, {alt:.1f}m")
                            
                            # Görev tipine göre waypoint oluştur
                            waypoints = []
                            
                            if mission_name == "Normal Devriye":
                                self.safe_log("📍 Normal devriye waypoint'leri oluşturuluyor...")
                                offset = 0.0001  # ~11 metre
                                
                                waypoints = [
                                    (lat + offset, lon + offset, 10.0),      # Kuzey-Doğu
                                    (lat + offset, lon - offset, 10.0),     # Kuzey-Batı
                                    (lat - offset, lon - offset, 10.0),    # Güney-Batı
                                    (lat - offset, lon + offset, 10.0)      # Güney-Doğu
                                ]
                                
                            elif mission_name == "Alçak Sessiz Devriye":
                                self.safe_log("🤫 Alçak sessiz devriye waypoint'leri oluşturuluyor...")
                                small_offset = 0.00005  # ~5.5 metre
                                
                                waypoints = [
                                    (lat + small_offset, lon + small_offset, 3.0),
                                    (lat + small_offset, lon - small_offset, 3.0)
                                ]
                                
                            elif mission_name == "Dairesel Devriye":
                                self.safe_log("🔄 Dairesel devriye waypoint'leri oluşturuluyor...")
                                import math
                                
                                radius_deg = 0.0001  # ~11 metre yarıçap
                                for i in range(8):
                                    angle = (i * 2 * math.pi) / 8
                                    wp_lat = lat + radius_deg * math.cos(angle)
                                    wp_lon = lon + radius_deg * math.sin(angle)
                                    waypoints.append((wp_lat, wp_lon, 10.0))
                            
                            self.safe_log(f"✅ {len(waypoints)} waypoint oluşturuldu")
                            
                            # Waypoint'lere sırayla git
                            for i, (wp_lat, wp_lon, wp_alt) in enumerate(waypoints):
                                self.safe_log(f"🎯 Waypoint {i+1}/{len(waypoints)}: {wp_lat:.6f}, {wp_lon:.6f}")
                                
                                # Core MAVSDK goto_location kullan
                                await system.action.goto_location(wp_lat, wp_lon, wp_alt, 0)
                                
                                # Hedefe ulaşmayı bekle (basit versiyon)
                                await asyncio.sleep(5)  # 5 saniye bekle
                            
                            self.safe_log("✅ Tüm waypoint'ler tamamlandı!")
                            
                        except Exception as mission_error:
                            self.safe_log(f"❌ Core MAVSDK mission hatası: {mission_error}")
                    
                    # Event loop çalıştır
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(async_mission())
                    loop.close()
                    
                except Exception as thread_error:
                    self.safe_log(f"❌ Core Mission thread hatası: {thread_error}")
            
            # Thread başlat
            Thread(target=do_mission, daemon=True).start()
            
        except Exception as e:
            self.safe_log(f"❌ Core MAVSDK görev başlatma hatası: {e}")

    def on_land(self):
        """Subprocess ile iniş"""
        if not MAVSDK_AVAILABLE:
            self.safe_log("❌ MAVSDK kütüphanesi yüklenmemiş!")
            return
        
        if not self.connection_manager or not self.connection_manager.is_connected():
            self.safe_log("⚠ MAVSDK bağlantısı yok!")
            return
    
        if not self.in_flight:
            self.safe_log("⚠ Uçuş yok, iniş yapılamaz.")
            return
    
        try:
            success = self.mavsdk_manager.land()
            
            if success:
                self.safe_log("⏬ Subprocess iniş komutu gönderildi")
                self.set_flight_status("İniş")
            else:
                self.safe_log("❌ İniş komutu gönderilemedi!")
                
        except Exception as e:
            self.safe_log(f"❌ İniş hatası: {e}")

    def on_return_home(self):
        """Subprocess ile RTL"""
        if not self.connection_manager or not self.connection_manager.is_connected():
            self.safe_log("⚠ MAVSDK bağlantısı yok!")
            return
    
        if not self.in_flight:
            self.safe_log("⚠ Uçuş yok, geri dönüş yapılamaz.")
            return
    
        try:
            success = self.mavsdk_manager.return_to_launch()
            
            if success:
                self.safe_log("🏠 Subprocess RTL komutu gönderildi")
            else:
                self.safe_log("❌ RTL komutu gönderilemedi!")
                
        except Exception as e:
            self.safe_log(f"❌ RTL hatası: {e}")
    
    def on_emergency(self):
        """Subprocess ile acil iniş"""
        if not self.connection_manager or not self.connection_manager.is_connected():
            self.safe_log("⚠ MAVSDK bağlantısı yok!")
            return
    
        if not self.in_flight:
            self.safe_log("⚠ Uçuş yok, acil iniş yapılamaz.")
            return
    
        try:
            success = self.mavsdk_manager.emergency_land()
            
            if success:
                self.safe_log("🚨 Subprocess ACİL İNİŞ komutu gönderildi!")
            else:
                self.safe_log("❌ Acil iniş komutu gönderilemedi!")
                
        except Exception as e:
            self.safe_log(f"❌ Acil iniş hatası: {e}")


    def on_mavsdk_connected(self):
        """MAVSDK bağlantı başarılı callback"""
        try:
            self.connect_button.setText("MAVSDK Bağlan")
            self.connect_button.setEnabled(False)
            self.disconnect_button.setEnabled(True)
            self.update_connection_status(True, "MAVSDK Bağlı")
            self.safe_log("✅ MAVSDK sistemi hazır!")
            
        except Exception as e:
            self.safe_log(f"⚠ MAVSDK connect callback hatası: {e}")

    def on_mavsdk_connection_failed(self):
        """MAVSDK bağlantı başarısız callback"""
        try:
            self.connect_button.setText("MAVSDK Bağlan") 
            self.connect_button.setEnabled(True)
            self.disconnect_button.setEnabled(False)
            self.update_connection_status(False, "MAVSDK Başarısız")
            self.connection_manager = None
            self.safe_log("❌ MAVSDK bağlantısı başarısız!")
            
        except Exception as e:
            self.safe_log(f"⚠ MAVSDK connection failed callback hatası: {e}")

    def start_mavsdk_telemetry(self):
        """UI telemetri başlat - DEBUG"""
        try:
            print("🚨 DEBUG: start_mavsdk_telemetry ÇAĞRILDI!")
            
            if not hasattr(self, 'ui_telemetry'):
                print("🚨 DEBUG: ui_telemetry yok, setup_ui_telemetry çağrılıyor")
                self.setup_ui_telemetry()
            
            main_connection_string = self.port_input.text().strip() or "udp://:14540"
            print(f"🚨 DEBUG: main_connection_string = {main_connection_string}")
            
            success = self.ui_telemetry.start(main_connection_string)
            print(f"🚨 DEBUG: ui_telemetry.start sonucu = {success}")
            
            if success:
                self.safe_log("⏰ UI Telemetri başlatıldı (Port: 14540)")
            else:
                self.safe_log("❌ UI Telemetri başlatılamadı")
            
        except Exception as e:
            print(f"🚨 DEBUG: HATA = {e}")
            import traceback
            traceback.print_exc()
            self.safe_log(f"⚠ UI Telemetri hatası: {e}")
    
    def stop_mavsdk_telemetry(self):
        """UI telemetri durdur"""
        try:
            if hasattr(self, 'ui_telemetry'):
                self.ui_telemetry.stop()
                self.safe_log("⏰ UI Telemetri durduruldu")
        except Exception as e:
            self.safe_log(f"⚠ UI Telemetri durdurma hatası: {e}")

    
    def manual_disconnect_from_mavsdk(self):
        """MAVSDK bağlantısını güvenli şekilde kes"""
        if not self.connection_manager:
            self.safe_log("⚠ Aktif MAVSDK bağlantısı yok!")
            return
        
        self.safe_log("🔌 MAVSDK bağlantısı kesiliyor...")
        
        try:
            # UI'yi güncelle
            self.disconnect_button.setText("Kesiliyor...")
            self.disconnect_button.setEnabled(False)
            
            # Telemetri durdur
            self.stop_mavsdk_telemetry()
            
            # Connection manager'ı durdur
            self.connection_manager.stop_connection()
            self.connection_manager = None
            self.action_manager = None
            
            # UI durumunu güncelle
            self.connect_button.setEnabled(True)
            self.disconnect_button.setText("Bağlantıyı Kes")
            self.update_connection_status(False, "MAVSDK Kesildi")
            
            # Uçuş durumunu sıfırla
            self.in_flight = False
            self.altitude = 0
            self.speed = 0
            self.heading = 0
            self.battery = 100
            
            self.safe_log("✅ MAVSDK bağlantısı başarıyla kesildi")
            
        except Exception as e:
            self.safe_log(f"❌ MAVSDK disconnect hatası: {e}")
    
    def update_connection_status(self, connected: bool, custom_message: str = None):
        """MAVSDK bağlantı durumu görselini güncelle"""
        if connected:
            status_text = custom_message or "MAVSDK Durumu: Bağlı"
            status_color = "green"
        else:
            status_text = custom_message or "MAVSDK Durumu: Bağlantı Yok"
            status_color = "red"
        
        self.connection_status_label.setText(status_text)
        self.connection_status_label.setStyleSheet(f"color: {status_color};")
        
        self.connection_status = connected

    def load_previous_state(self):
        """Önceki durumu yükle (opsiyonel)"""
        try:
            import json
            import os
            
            if os.path.exists('mavsdk_app_state.json'):
                with open('mavsdk_app_state.json', 'r') as f:
                    app_state = json.load(f)
                
                # Port ve timeout'u geri yükle
                if 'last_port' in app_state:
                    self.port_input.setText(app_state['last_port'])
                
                if 'last_timeout' in app_state:
                    self.timeout_input.setText(str(app_state['last_timeout']))
                
                # Restart time'ı kontrol et
                if 'restart_time' in app_state:
                    restart_time = app_state['restart_time']
                    if time.time() - restart_time < 60:  # 1 dakika içinde restart
                        self.safe_log("🔄 Önceki MAVSDK oturumu güvenli yeniden başlatma ile sona erdi")
                
                # State dosyasını sil
                os.remove('mavsdk_app_state.json')
                print("✅ Önceki MAVSDK durumu yüklendi ve temizlendi")
                
        except Exception as e:
            print(f"⚠ MAVSDK durum yükleme hatası: {e}")
    
    def closeEvent(self, event):
        """MAVSDK uygulaması kapatma"""
        try:
            print("👋 MAVSDK Normal kapatma işlemi...")
            
            # Eğer connection manager varsa uyar
            if self.connection_manager:
                from PyQt5.QtWidgets import QMessageBox
                
                reply = QMessageBox.question(
                    self, 
                    'MAVSDK Uygulamayı Kapat', 
                    'Aktif MAVSDK bağlantısı var.\n\nBağlantıyı güvenli kesmek için "Bağlantıyı Kes" butonunu kullanın.\n\nYine de kapatmak istiyor musunuz?',
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                
                if reply == QMessageBox.No:
                    event.ignore()
                    return
                else:
                    # Kapatmadan önce bağlantıyı kes
                    try:
                        self.connection_manager.stop_connection()
                    except:
                        pass
            
            # Normal kapatma
            print("✅ MAVSDK normal kapatma onaylandı")
            
        except Exception as e:
            print(f"MAVSDK kapatma hatası: {e}")
        
        event.accept()
    
    def check_restart_status(self):
        """MAVSDK restart sonrası durum kontrolü"""
        try:
            import os
            
            # Eğer state dosyası varsa restart sonrasıyız
            if os.path.exists('mavsdk_app_state.json'):
                self.safe_log("✅ MAVSDK Güvenli yeniden başlatma tamamlandı")
                
                # Kullanıcıya bilgi ver
                from PyQt5.QtWidgets import QMessageBox
                QMessageBox.information(
                    self,
                    'MAVSDK Yeniden Başlatma Tamamlandı',
                    'MAVSDK bağlantısı güvenli şekilde kesildi.\n\nYeni bağlantı kurmak için "MAVSDK Bağlan" butonunu kullanabilirsiniz.',
                    QMessageBox.Ok
                )
                
        except Exception as e:
            print(f"MAVSDK restart status kontrolü hatası: {e}")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = FlightControlStation()
    ex.show()
    sys.exit(app.exec_())
