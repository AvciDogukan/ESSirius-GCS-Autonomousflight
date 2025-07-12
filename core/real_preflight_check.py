#!/usr/bin/env python3
"""
simplified_mavsdk_preflight.py
Basitleştirilmiş MAVSDK subprocess preflight check sistemi
UUID karmaşıklığı yok - Sadece basit telemetri kontrolleri
"""

import sys
import time
import subprocess
import json
import tempfile
import os
import math
import asyncio
import traceback
from datetime import datetime
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QProgressBar, QListWidget, QListWidgetItem,
                             QFrame, QGroupBox, QGridLayout, QTextEdit, QScrollArea,
                             QWidget, QSplitter, QTabWidget, QCheckBox, QSpinBox,
                             QFileDialog, QMessageBox)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal, QPropertyAnimation, QEasingCurve, pyqtProperty
from PyQt5.QtGui import QFont, QIcon, QPixmap, QPainter, QColor, QBrush, QPen

# MAVSDK import kontrolü
try:
    from mavsdk import System
    MAVSDK_AVAILABLE = True
except ImportError:
    MAVSDK_AVAILABLE = False
    print("⚠️ MAVSDK kütüphanesi bulunamadı!")

# ==================== BASIT SUBPROCESS RUNNER SCRIPT ====================

SIMPLE_SUBPROCESS_RUNNER = '''#!/usr/bin/env python3
"""
Basit subprocess runner - Direkt telemetri kontrolleri
UUID yok, sadece basit MAVSDK telemetri verileri
"""

import sys
import json
import asyncio
import math
import traceback

try:
    from mavsdk import System
    MAVSDK_AVAILABLE = True
except ImportError:
    MAVSDK_AVAILABLE = False

class SimplePreflightChecker:
    """Basit MAVSDK preflight checker - UUID yok"""
    
    def __init__(self, connection_string="udp://:14540", timeout=10):
        self.connection_string = connection_string
        self.timeout = timeout
        self.system = None
        
    async def connect_simple(self):
        """Basit MAVSDK bağlantısı - UUID kontrolü yok"""
        if not MAVSDK_AVAILABLE:
            raise Exception("MAVSDK kütüphanesi mevcut değil")
        
        self.system = System()
        print(f"Connecting to {self.connection_string}")
        await self.system.connect(system_address=self.connection_string)
        
        # Basit bağlantı bekleme - UUID yok
        print("Waiting for connection...")
        async for state in self.system.core.connection_state():
            if state.is_connected:
                print("Connected!")
                break
        
        return self.system
    
    async def get_telemetry_simple(self, telemetry_stream, timeout=5.0):
        """Basit telemetri verisi alma - Python 3.8+ uyumlu"""
        try:
            # Timeout ile async iterator kullanımı
            async def get_first_item():
                async for data in telemetry_stream:
                    return data
                raise StopAsyncIteration("Stream bitti")
            
            data = await asyncio.wait_for(get_first_item(), timeout=timeout)
            return data, None
            
        except asyncio.TimeoutError:
            return None, "Timeout"
        except StopAsyncIteration:
            return None, "Stream bitti"  
        except Exception as e:
            return None, str(e)
    
    async def check_connection(self):
        """Basit bağlantı kontrolü"""
        try:
            if not MAVSDK_AVAILABLE:
                return "failed", "MAVSDK kütüphanesi yok"
            
            system = await self.connect_simple()
            
            # Sadece bağlantı durumu - UUID yok
            state, error = await self.get_telemetry_simple(
                system.core.connection_state(), timeout=3.0
            )
            
            if error:
                return "failed", f"Bağlantı durumu alınamadı: {error}"
            
            if state and state.is_connected:
                return "passed", "MAVSDK bağlantısı OK"
            else:
                return "failed", "Bağlantı yok"
                
        except Exception as e:
            return "failed", f"Bağlantı hatası: {str(e)}"
    
    async def check_gps_simple(self):
        """Basit GPS kontrolü"""
        try:
            if not self.system:
                await self.connect_simple()
            
            gps, error = await self.get_telemetry_simple(
                self.system.telemetry.gps_info(), timeout=self.timeout
            )
            
            if error:
                return "failed", f"GPS verisi yok: {error}"
            
            satellites = gps.num_satellites
            fix_type = gps.fix_type
            
            if fix_type >= 3 and satellites >= 6:
                return "passed", f"GPS OK - {satellites} uydu, 3D fix"
            elif fix_type >= 2:
                return "warning", f"GPS zayıf - {satellites} uydu, {fix_type}D fix"
            else:
                return "failed", f"GPS yok - {satellites} uydu, fix yok"
            
        except Exception as e:
            return "failed", f"GPS kontrolü hatası: {str(e)}"
    
    async def check_battery_simple(self):
        """Basit batarya kontrolü"""
        try:
            if not self.system:
                await self.connect_simple()
            
            battery, error = await self.get_telemetry_simple(
                self.system.telemetry.battery(), timeout=self.timeout
            )
            
            if error:
                return "failed", f"Batarya verisi yok: {error}"
            
            percent = battery.remaining_percent
            voltage = battery.voltage_v
            
            if percent >= 60:
                return "passed", f"Batarya iyi - %{percent:.1f}, {voltage:.1f}V"
            elif percent >= 30:
                return "warning", f"Batarya orta - %{percent:.1f}, {voltage:.1f}V"
            else:
                return "failed", f"Batarya düşük - %{percent:.1f}, {voltage:.1f}V"
            
        except Exception as e:
            return "failed", f"Batarya kontrolü hatası: {str(e)}"
    
    async def check_position_simple(self):
        """Basit pozisyon kontrolü"""
        try:
            if not self.system:
                await self.connect_simple()
            
            pos, error = await self.get_telemetry_simple(
                self.system.telemetry.position(), timeout=self.timeout
            )
            
            if error:
                return "failed", f"Pozisyon verisi yok: {error}"
            
            lat = pos.latitude_deg
            lon = pos.longitude_deg
            alt = pos.relative_altitude_m
            
            if abs(lat) < 0.0001 and abs(lon) < 0.0001:
                return "failed", "Geçersiz pozisyon (0,0)"
            
            return "passed", f"Pozisyon OK - {lat:.6f}, {lon:.6f}, {alt:.1f}m"
            
        except Exception as e:
            return "failed", f"Pozisyon kontrolü hatası: {str(e)}"
    
    async def check_armed_simple(self):
        """Basit ARM durumu kontrolü"""
        try:
            if not self.system:
                await self.connect_simple()
            
            armed, error = await self.get_telemetry_simple(
                self.system.telemetry.armed(), timeout=self.timeout
            )
            
            if error:
                return "failed", f"ARM durumu alınamadı: {error}"
            
            if armed:
                return "warning", "Motorlar ARM'lı - DİKKAT!"
            else:
                return "passed", "Motorlar DISARM - Güvenli"
            
        except Exception as e:
            return "failed", f"ARM kontrolü hatası: {str(e)}"
    
    async def check_flight_mode_simple(self):
        """Basit uçuş modu kontrolü"""
        try:
            if not self.system:
                await self.connect_simple()
            
            mode, error = await self.get_telemetry_simple(
                self.system.telemetry.flight_mode(), timeout=self.timeout
            )
            
            if error:
                return "failed", f"Uçuş modu alınamadı: {error}"
            
            mode_str = str(mode)
            
            # Basit mod kontrolü
            if "MANUAL" in mode_str.upper() or "STABILIZE" in mode_str.upper():
                return "passed", f"Güvenli mod: {mode_str}"
            elif "AUTO" in mode_str.upper() or "GUIDED" in mode_str.upper():
                return "warning", f"Otomatik mod: {mode_str}"
            else:
                return "warning", f"Bilinmeyen mod: {mode_str}"
            
        except Exception as e:
            return "failed", f"Uçuş modu kontrolü hatası: {str(e)}"
    
    async def check_velocity_simple(self):
        """Basit hız kontrolü"""
        try:
            if not self.system:
                await self.connect_simple()
            
            vel, error = await self.get_telemetry_simple(
                self.system.telemetry.velocity_ned(), timeout=self.timeout
            )
            
            if error:
                return "warning", f"Hız verisi yok: {error}"
            
            speed = math.sqrt(vel.north_m_s**2 + vel.east_m_s**2)
            speed_kmh = speed * 3.6
            
            if speed_kmh > 5:
                return "warning", f"Yüksek hız: {speed_kmh:.1f} km/h"
            else:
                return "passed", f"Hız normal: {speed_kmh:.1f} km/h"
            
        except Exception as e:
            return "failed", f"Hız kontrolü hatası: {str(e)}"
    
    async def check_attitude_simple(self):
        """Basit açı kontrolü"""
        try:
            if not self.system:
                await self.connect_simple()
            
            att, error = await self.get_telemetry_simple(
                self.system.telemetry.attitude_euler(), timeout=self.timeout
            )
            
            if error:
                return "warning", f"Açı verisi yok: {error}"
            
            roll = abs(att.roll_deg)
            pitch = abs(att.pitch_deg)
            
            if roll > 45 or pitch > 45:
                return "warning", f"Yüksek açı - Roll: {roll:.1f}°, Pitch: {pitch:.1f}°"
            else:
                return "passed", f"Açı normal - Roll: {roll:.1f}°, Pitch: {pitch:.1f}°"
            
        except Exception as e:
            return "failed", f"Açı kontrolü hatası: {str(e)}"

async def run_simple_check(params):
    """Basit preflight check runner"""
    try:
        check_type = params.get('check_type')
        connection_string = params.get('connection_string', 'udp://:14540')
        timeout = params.get('timeout', 10)
        
        checker = SimplePreflightChecker(connection_string, timeout)
        
        # Basit check fonksiyonları
        check_functions = {
            'connection': checker.check_connection,
            'gps': checker.check_gps_simple,
            'battery': checker.check_battery_simple,
            'position': checker.check_position_simple,
            'armed': checker.check_armed_simple,
            'flight_mode': checker.check_flight_mode_simple,
            'velocity': checker.check_velocity_simple,
            'attitude': checker.check_attitude_simple
        }
        
        if check_type not in check_functions:
            return {
                'status': 'failed',
                'details': f'Bilinmeyen check: {check_type}'
            }
        
        status, details = await asyncio.wait_for(
            check_functions[check_type](), 
            timeout=timeout + 5
        )
        
        return {
            'status': status,
            'details': details
        }
        
    except asyncio.TimeoutError:
        return {
            'status': 'failed',
            'details': f'Timeout: {timeout + 5} saniye'
        }
    except Exception as e:
        return {
            'status': 'failed',
            'details': f'Hata: {str(e)}'
        }

def main():
    """Subprocess entry point"""
    try:
        if len(sys.argv) != 2:
            print("Usage: python runner.py <params_file>")
            sys.exit(1)
        
        params_file = sys.argv[1]
        
        with open(params_file, 'r') as f:
            params = json.load(f)
        
        result = asyncio.run(run_simple_check(params))
        print(json.dumps(result))
        
    except Exception as e:
        error_result = {
            'status': 'failed',
            'details': f'Runner hatası: {str(e)}'
        }
        print(json.dumps(error_result))
        sys.exit(1)

if __name__ == "__main__":
    main()
'''

# ==================== PREFLIGHT CHECK ITEMS ====================

class PreflightCheckItem:
    """Basit preflight kontrol öğesi"""
    def __init__(self, name, description, check_type, critical=True):
        self.name = name
        self.description = description
        self.check_type = check_type
        self.critical = critical
        self.status = "pending"
        self.details = ""
        self.timestamp = None

# ==================== UI COMPONENTS ====================

class AnimatedStatusIcon(QLabel):
    """Animasyonlu durum ikonu"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(24, 24)
        self.status = "pending"
        self.pulse_value = 0
        
        self.animation = QPropertyAnimation(self, b"pulseValue")
        self.animation.setDuration(1500)
        self.animation.setStartValue(0)
        self.animation.setEndValue(360)
        self.animation.setEasingCurve(QEasingCurve.InOutSine)
        self.animation.setLoopCount(-1)
        
    @pyqtProperty(float)
    def pulseValue(self):
        return self.pulse_value
    
    @pulseValue.setter
    def pulseValue(self, value):
        self.pulse_value = value
        self.update()
        
    def set_status(self, status):
        self.status = status
        if status == "checking":
            self.animation.start()
        else:
            self.animation.stop()
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        center_x, center_y = self.width() // 2, self.height() // 2
        radius = min(self.width(), self.height()) // 2 - 2
        
        if self.status == "pending":
            painter.setBrush(QBrush(QColor(150, 150, 150)))
            painter.setPen(QPen(QColor(100, 100, 100), 2))
            painter.drawEllipse(center_x - radius, center_y - radius, radius * 2, radius * 2)
            painter.setPen(QPen(QColor(255, 255, 255), 2))
            painter.drawText(self.rect(), Qt.AlignCenter, "?")
            
        elif self.status == "checking":
            import math
            angle = math.radians(self.pulse_value)
            
            painter.setBrush(QBrush(QColor(255, 165, 0, 100 + int(50 * math.sin(angle)))))
            painter.setPen(QPen(QColor(255, 140, 0), 2))
            painter.drawEllipse(center_x - radius, center_y - radius, radius * 2, radius * 2)
            
            end_x = center_x + int((radius - 4) * math.cos(angle))
            end_y = center_y + int((radius - 4) * math.sin(angle))
            painter.setPen(QPen(QColor(255, 255, 255), 3))
            painter.drawLine(center_x, center_y, end_x, end_y)
            
        elif self.status == "passed":
            painter.setBrush(QBrush(QColor(46, 204, 113)))
            painter.setPen(QPen(QColor(39, 174, 96), 2))
            painter.drawEllipse(center_x - radius, center_y - radius, radius * 2, radius * 2)
            painter.setPen(QPen(QColor(255, 255, 255), 3))
            painter.drawText(self.rect(), Qt.AlignCenter, "✓")
            
        elif self.status == "failed":
            painter.setBrush(QBrush(QColor(231, 76, 60)))
            painter.setPen(QPen(QColor(192, 57, 43), 2))
            painter.drawEllipse(center_x - radius, center_y - radius, radius * 2, radius * 2)
            painter.setPen(QPen(QColor(255, 255, 255), 3))
            painter.drawText(self.rect(), Qt.AlignCenter, "✗")
            
        elif self.status == "warning":
            painter.setBrush(QBrush(QColor(241, 196, 15)))
            painter.setPen(QPen(QColor(243, 156, 18), 2))
            painter.drawEllipse(center_x - radius, center_y - radius, radius * 2, radius * 2)
            painter.setPen(QPen(QColor(255, 255, 255), 3))
            painter.drawText(self.rect(), Qt.AlignCenter, "!")

# ==================== WORKER THREAD ====================

class SimplePreflightWorker(QThread):
    """Basit subprocess worker"""
    item_started = pyqtSignal(int)
    item_completed = pyqtSignal(int, str, str, str)
    all_completed = pyqtSignal()
    log_message = pyqtSignal(str)
    
    def __init__(self, check_items, connection_string=None, timeout=15):
        super().__init__()
        self.check_items = check_items
        self.connection_string = connection_string or "udp://:14540"
        self.timeout = timeout
        self.should_stop = False
        
    def run(self):
        """Ana thread - basit subprocess'ler çalıştır"""
        for i, item in enumerate(self.check_items):
            if self.should_stop:
                break
                
            self.item_started.emit(i)
            
            try:
                check_params = {
                    'check_type': item.check_type,
                    'connection_string': self.connection_string,
                    'timeout': self.timeout
                }
                
                self.log_message.emit(f"🔄 {datetime.now().strftime('%H:%M:%S')} - {item.name} kontrol ediliyor...")
                
                status, details = self.run_simple_subprocess(check_params)
                
            except Exception as e:
                status = "failed"
                details = f"Subprocess hatası: {str(e)}"
                self.log_message.emit(f"❌ Hata: {e}")
            
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.item_completed.emit(i, status, details, timestamp)
            
            time.sleep(0.3)  # Daha hızlı
            
        if not self.should_stop:
            self.all_completed.emit()
    
    def run_simple_subprocess(self, params):
        """Basit subprocess çalıştır"""
        try:
            # Geçici runner dosyası
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as runner_file:
                runner_file.write(SIMPLE_SUBPROCESS_RUNNER)
                runner_path = runner_file.name
            
            # Parametreler dosyası
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as params_file:
                json.dump(params, params_file, indent=2)
                params_path = params_file.name
            
            try:
                # Subprocess çalıştır
                cmd = [sys.executable, runner_path, params_path]
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout + 5,
                    cwd=os.path.dirname(os.path.abspath(__file__))
                )
                
                if result.returncode == 0:
                    try:
                        output_lines = result.stdout.strip().split('\n')
                        json_result = output_lines[-1]
                        data = json.loads(json_result)
                        return data.get('status', 'failed'), data.get('details', 'Detay yok')
                    except (json.JSONDecodeError, IndexError):
                        return "failed", f"Çıktı parse edilemedi: {result.stdout[:100]}"
                else:
                    error_detail = result.stderr.strip() if result.stderr else "Bilinmeyen hata"
                    return "failed", f"Subprocess hatası: {error_detail[:200]}"
                    
            finally:
                # Temizlik
                try:
                    os.unlink(runner_path)
                    os.unlink(params_path)
                except:
                    pass
                    
        except subprocess.TimeoutExpired:
            return "failed", f"Timeout: {self.timeout + 5} saniye"
        except Exception as e:
            return "failed", f"Subprocess hatası: {str(e)}"
    
    def stop(self):
        self.should_stop = True

# ==================== MAIN DIALOG ====================

class SimplePreflightDialog(QDialog):
    """Basit MAVSDK Preflight Check Dialog"""
    
    def __init__(self, parent=None, connection_manager=None):
        super().__init__(parent)
        self.connection_manager = connection_manager
        self.check_items = []
        self.check_widgets = []
        self.worker = None
        self.is_checking = False
        
        self.setup_check_items()
        self.setup_ui()
        self.setup_styles()
        
    def get_connection_string(self):
        """Bağlantı string'ini al"""
        if self.connection_manager and hasattr(self.connection_manager, 'connection_string'):
            return self.connection_manager.connection_string
        elif self.connection_manager and hasattr(self.connection_manager, 'get_connection_string'):
            return self.connection_manager.get_connection_string()
        else:
            return "udp://:14540"
        
    def setup_check_items(self):
        """Basit check item'larını tanımla"""
        
        # Temel kontroller - Basit ve hızlı
        self.check_items = [
            PreflightCheckItem("MAVSDK Bağlantısı", "Temel MAVSDK bağlantı kontrolü", 
                             "connection", True),
            PreflightCheckItem("GPS Durumu", "GPS uydu sayısı ve fix kalitesi", 
                             "gps", True),
            PreflightCheckItem("Batarya Seviyesi", "Batarya yüzdesi ve voltaj", 
                             "battery", True),
            PreflightCheckItem("Pozisyon Bilgisi", "Geçerli GPS koordinatları", 
                             "position", True),
            PreflightCheckItem("Motor ARM Durumu", "Motor arming kontrolü", 
                             "armed", True),
            PreflightCheckItem("Uçuş Modu", "Aktif flight mode", 
                             "flight_mode", False),
            PreflightCheckItem("Hız Kontrolü", "Mevcut hareket hızı", 
                             "velocity", False),
            PreflightCheckItem("Açı Durumu", "Roll/Pitch açıları", 
                             "attitude", False),
        ]
        
    def setup_ui(self):
        """UI kurulumu"""
        self.setWindowTitle("🚁 BASİT MAVSDK PREFLIGHT CHECK")
        self.setFixedSize(1200, 800)
        self.setModal(True)
        
        # Ana layout
        main_layout = QVBoxLayout()
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # Header
        self.create_header(main_layout)
        
        # Ana içerik
        splitter = QSplitter(Qt.Horizontal)
        
        # Sol panel - Check listesi
        left_panel = self.create_check_list_panel()
        splitter.addWidget(left_panel)
        
        # Sağ panel - Kontroller
        right_panel = self.create_control_panel()
        splitter.addWidget(right_panel)
        
        splitter.setSizes([600, 300])
        main_layout.addWidget(splitter)
        
        # Footer
        self.create_footer(main_layout)
        
        self.setLayout(main_layout)
        
    def create_header(self, layout):
        """Header bölümü"""
        header_frame = QFrame()
        header_layout = QVBoxLayout(header_frame)
        
        # Başlık
        title = QLabel("🚁 BASİT MAVSDK PREFLIGHT CHECK")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("""
            QLabel {
                font-size: 20px;
                font-weight: bold;
                color: #27ae60;
                padding: 12px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(39, 174, 96, 0.1), 
                    stop:1 rgba(46, 204, 113, 0.1));
                border: 2px solid #27ae60;
                border-radius: 8px;
                margin-bottom: 8px;
            }
        """)
        
        # Alt başlık
        subtitle = QLabel("⚡ Hızlı ve basit telemetri kontrolleri - UUID karmaşıklığı yok!")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("color: #7f8c8d; font-size: 11px; margin-bottom: 8px;")
        
        # Bağlantı durumu
        conn_string = self.get_connection_string()
        conn_label = QLabel(f"🔗 Bağlantı: {conn_string}")
        conn_label.setAlignment(Qt.AlignCenter)
        conn_label.setStyleSheet("font-weight: bold; color: #2c3e50; margin-bottom: 8px;")
        
        # Progress bar
        self.overall_progress = QProgressBar()
        self.overall_progress.setMinimum(0)
        self.overall_progress.setMaximum(len(self.check_items))
        self.overall_progress.setValue(0)
        self.overall_progress.setFormat("İlerleme: %v/%m (%p%)")
        
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        header_layout.addWidget(conn_label)
        header_layout.addWidget(self.overall_progress)
        
        layout.addWidget(header_frame)
        
    def create_check_list_panel(self):
        """Sol panel - Check listesi"""
        panel = QFrame()
        layout = QVBoxLayout(panel)
        
        # Liste başlığı
        list_title = QLabel("📋 Kontrol Listesi")
        list_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #34495e; margin-bottom: 10px;")
        layout.addWidget(list_title)
        
        # Scroll area
        scroll_area = QScrollArea()
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        
        # Check item'ları oluştur
        for i, item in enumerate(self.check_items):
            item_widget = self.create_check_item_widget(item, i)
            scroll_layout.addWidget(item_widget)
            self.check_widgets.append(item_widget)
        
        scroll_layout.addStretch()
        scroll_content.setLayout(scroll_layout)
        scroll_area.setWidget(scroll_content)
        scroll_area.setWidgetResizable(True)
        
        layout.addWidget(scroll_area)
        return panel
        
    def create_check_item_widget(self, item, index):
        """Check item widget'ı"""
        frame = QFrame()
        frame.setFrameStyle(QFrame.Box)
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(8, 6, 8, 6)
        
        # Status ikonu
        status_icon = AnimatedStatusIcon()
        layout.addWidget(status_icon)
        
        # İçerik
        content_layout = QVBoxLayout()
        
        # İsim
        name_label = QLabel(item.name)
        if item.critical:
            name_label.setStyleSheet("font-weight: bold; color: #c0392b;")
        else:
            name_label.setStyleSheet("color: #34495e;")
            
        # Açıklama
        desc_label = QLabel(item.description)
        desc_label.setStyleSheet("color: #7f8c8d; font-size: 10px;")
        desc_label.setWordWrap(True)
        
        # Check tipi
        check_label = QLabel(f"Check: {item.check_type}")
        check_label.setStyleSheet("color: #27ae60; font-size: 9px; font-style: italic;")
        
        # Kritik işaret
        if item.critical:
            critical_label = QLabel("🔴 KRİTİK")
            critical_label.setStyleSheet("color: #c0392b; font-size: 9px; font-weight: bold;")
            content_layout.addWidget(critical_label)
        
        content_layout.addWidget(name_label)
        content_layout.addWidget(desc_label)
        content_layout.addWidget(check_label)
        
        layout.addLayout(content_layout, 1)
        
        # Sonuç bölümü
        result_layout = QVBoxLayout()
        timestamp_label = QLabel("")
        timestamp_label.setStyleSheet("color: #95a5a6; font-size: 9px;")
        
        details_label = QLabel("")
        details_label.setStyleSheet("color: #7f8c8d; font-size: 9px;")
        details_label.setWordWrap(True)
        details_label.setMaximumWidth(120)
        
        result_layout.addWidget(timestamp_label)
        result_layout.addWidget(details_label)
        layout.addLayout(result_layout)
        
        # Widget referansları
        frame.status_icon = status_icon
        frame.name_label = name_label
        frame.desc_label = desc_label
        frame.timestamp_label = timestamp_label
        frame.details_label = details_label
        frame.item = item
        frame.index = index
        
        return frame
    
    def create_control_panel(self):
        """Sağ panel - Kontroller"""
        panel = QFrame()
        layout = QVBoxLayout(panel)
        
        # Durum özeti
        summary_group = QGroupBox("📊 DURUM ÖZETİ")
        summary_layout = QGridLayout()
        
        self.total_checks_label = QLabel(str(len(self.check_items)))
        self.passed_count = QLabel("0")
        self.failed_count = QLabel("0")
        self.warning_count = QLabel("0")
        
        summary_layout.addWidget(QLabel("Toplam:"), 0, 0)
        summary_layout.addWidget(self.total_checks_label, 0, 1)
        summary_layout.addWidget(QLabel("✅ Başarılı:"), 1, 0)
        summary_layout.addWidget(self.passed_count, 1, 1)
        summary_layout.addWidget(QLabel("❌ Başarısız:"), 2, 0)
        summary_layout.addWidget(self.failed_count, 2, 1)
        summary_layout.addWidget(QLabel("⚠️ Uyarı:"), 3, 0)
        summary_layout.addWidget(self.warning_count, 3, 1)
        
        summary_group.setLayout(summary_layout)
        layout.addWidget(summary_group)
        
        # Güvenlik durumu
        safety_group = QGroupBox("🛡️ GÜVENLİK DURUMU")
        safety_layout = QVBoxLayout()
        
        self.safety_status_label = QLabel("⏳ Kontroller bekleniyor...")
        self.safety_status_label.setStyleSheet("font-size: 12px; font-weight: bold; padding: 8px; border-radius: 4px;")
        
        self.safety_recommendation = QLabel("Basit MAVSDK telemetri kontrolleri yapılacak.")
        self.safety_recommendation.setWordWrap(True)
        self.safety_recommendation.setStyleSheet("color: #7f8c8d; font-style: italic; margin-top: 4px;")
        
        safety_layout.addWidget(self.safety_status_label)
        safety_layout.addWidget(self.safety_recommendation)
        
        safety_group.setLayout(safety_layout)
        layout.addWidget(safety_group)
        
        # Ayarlar
        settings_group = QGroupBox("⚙️ AYARLAR")
        settings_layout = QVBoxLayout()
        
        self.critical_only_check = QCheckBox("Sadece kritik kontroller")
        self.critical_only_check.setToolTip("Sadece kritik güvenlik kontrollerini yapar")
        
        timeout_layout = QHBoxLayout()
        timeout_layout.addWidget(QLabel("Timeout (sn):"))
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setMinimum(5)
        self.timeout_spin.setMaximum(30)
        self.timeout_spin.setValue(10)
        self.timeout_spin.setToolTip("Her kontrol için maksimum bekleme süresi")
        timeout_layout.addWidget(self.timeout_spin)
        
        settings_layout.addWidget(self.critical_only_check)
        settings_layout.addLayout(timeout_layout)
        
        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)
        
        # Log
        log_group = QGroupBox("📝 KONTROL LOGLARI")
        log_layout = QVBoxLayout()
        
        self.detail_log = QTextEdit()
        self.detail_log.setReadOnly(True)
        self.detail_log.setMaximumHeight(120)
        self.detail_log.setStyleSheet("""
            QTextEdit {
                background-color: #2c3e50;
                color: #ecf0f1;
                font-family: 'Courier New', monospace;
                font-size: 10px;
                border: 1px solid #34495e;
                border-radius: 3px;
            }
        """)
        
        log_layout.addWidget(self.detail_log)
        log_group.setLayout(log_layout)
        layout.addWidget(log_group)
        
        layout.addStretch()
        return panel
        
    def create_footer(self, layout):
        """Footer butonları"""
        footer_layout = QHBoxLayout()
        
        # Durum
        self.status_label = QLabel("⏳ Basit MAVSDK kontrolleri hazır...")
        self.status_label.setStyleSheet("color: #7f8c8d; font-style: italic;")
        footer_layout.addWidget(self.status_label)
        
        footer_layout.addStretch()
        
        # Butonlar
        self.start_button = QPushButton("🚀 KONTROLLERI BAŞLAT")
        self.start_button.clicked.connect(self.start_simple_preflight_check)
        self.start_button.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #219a52;
            }
            QPushButton:disabled {
                background-color: #95a5a6;
            }
        """)
        
        self.stop_button = QPushButton("⏹️ DURDUR")
        self.stop_button.clicked.connect(self.stop_preflight_check)
        self.stop_button.setEnabled(False)
        self.stop_button.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
            QPushButton:disabled {
                background-color: #95a5a6;
            }
        """)
        
        self.export_button = QPushButton("📄 RAPOR")
        self.export_button.clicked.connect(self.export_report)
        self.export_button.setEnabled(False)
        self.export_button.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:disabled {
                background-color: #95a5a6;
            }
        """)
        
        self.close_button = QPushButton("❌ KAPAT")
        self.close_button.clicked.connect(self.close)
        self.close_button.setStyleSheet("""
            QPushButton {
                background-color: #34495e;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2c3e50;
            }
        """)
        
        footer_layout.addWidget(self.start_button)
        footer_layout.addWidget(self.stop_button)
        footer_layout.addWidget(self.export_button)
        footer_layout.addWidget(self.close_button)
        
        layout.addLayout(footer_layout)
        
    def setup_styles(self):
        """Genel stiller"""
        self.setStyleSheet("""
            QDialog {
                background-color: #ecf0f1;
                color: #2c3e50;
            }
            QGroupBox {
                font-size: 11px;
                font-weight: bold;
                border: 2px solid #bdc3c7;
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 12px;
                background-color: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 8px 0 8px;
                color: #34495e;
            }
            QFrame {
                background-color: white;
                border-radius: 4px;
                margin: 1px;
            }
            QProgressBar {
                border: 2px solid #bdc3c7;
                border-radius: 4px;
                text-align: center;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background-color: #27ae60;
                border-radius: 2px;
            }
        """)
    
    def start_simple_preflight_check(self):
        """Basit preflight check başlat"""
        if self.is_checking:
            return
        
        if not MAVSDK_AVAILABLE:
            self.detail_log.append("❌ HATA: MAVSDK kütüphanesi yüklü değil!")
            self.status_label.setText("❌ MAVSDK gerekli")
            return
            
        self.is_checking = True
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.export_button.setEnabled(False)
        self.status_label.setText("🔄 Basit kontroller çalışıyor...")
        
        # Widget'ları reset et
        for widget in self.check_widgets:
            widget.status_icon.set_status("pending")
            widget.timestamp_label.setText("")
            widget.details_label.setText("")
        
        # Progress sıfırla
        self.overall_progress.setValue(0)
        self.detail_log.clear()
        self.detail_log.append(f"🚀 {datetime.now().strftime('%H:%M:%S')} - BASİT MAVSDK KONTROLLERI BAŞLADI")
        self.detail_log.append("⚡ UUID karmaşıklığı yok - Hızlı telemetri kontrolleri!")
        
        # Sadece kritik kontroller seçilmişse filtrele
        check_items = self.check_items
        if self.critical_only_check.isChecked():
            check_items = [item for item in self.check_items if item.critical]
            self.detail_log.append(f"⚠️ Sadece kritik kontroller ({len(check_items)}/{len(self.check_items)})")
        
        # Connection string al
        connection_string = self.get_connection_string()
        self.detail_log.append(f"🔗 Bağlantı: {connection_string}")
        
        # Timeout ayarı
        timeout = self.timeout_spin.value()
        self.detail_log.append(f"⏱️ Timeout: {timeout} saniye")
        
        # Güvenlik durumu
        self.safety_status_label.setText("🔄 Kontroller devam ediyor...")
        self.safety_status_label.setStyleSheet("background-color: #f39c12; color: white;")
        self.safety_recommendation.setText("Basit telemetri kontrolleri yapılıyor...")
        
        # Worker başlat
        self.worker = SimplePreflightWorker(check_items, connection_string, timeout)
        self.worker.item_started.connect(self.on_item_started)
        self.worker.item_completed.connect(self.on_item_completed)
        self.worker.all_completed.connect(self.on_all_completed)
        self.worker.log_message.connect(self.on_log_message)
        self.worker.start()
        
    def stop_preflight_check(self):
        """Preflight check durdur"""
        if self.worker:
            self.worker.stop()
            self.worker.wait()
            
        self.is_checking = False
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.status_label.setText("⏹️ Kontroller durduruldu")
        
        self.detail_log.append(f"⏹️ {datetime.now().strftime('%H:%M:%S')} - Kontroller manuel olarak durduruldu")
        
    def on_item_started(self, index):
        """Item kontrolü başladığında"""
        if index < len(self.check_widgets):
            widget = self.check_widgets[index]
            widget.status_icon.set_status("checking")
            
    def on_item_completed(self, index, status, details, timestamp):
        """Item kontrolü tamamlandığında"""
        if index < len(self.check_widgets):
            widget = self.check_widgets[index]
            widget.status_icon.set_status(status)
            widget.timestamp_label.setText(timestamp)
            widget.details_label.setText(details[:40] + "..." if len(details) > 40 else details)
            
            # Progress güncelle
            self.overall_progress.setValue(self.overall_progress.value() + 1)
            
            # Log ekle
            item = widget.item
            status_icons = {
                "passed": "✅",
                "failed": "❌", 
                "warning": "⚠️"
            }
            icon = status_icons.get(status, "❓")
            
            criticality = " [KRİTİK]" if item.critical else ""
            self.detail_log.append(f"{icon} {timestamp} - {item.name}{criticality}: {details}")
            
            # Sayıları güncelle
            self.update_counters()
            
    def on_log_message(self, message):
        """Log mesajı ekle"""
        self.detail_log.append(message)
        
    def on_all_completed(self):
        """Tüm kontroller tamamlandığında"""
        self.is_checking = False
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.export_button.setEnabled(True)
        
        # Final safety assessment
        self.calculate_final_safety_status()
        
        self.detail_log.append(f"✅ {datetime.now().strftime('%H:%M:%S')} - TÜM KONTROLLER TAMAMLANDI")
        self.status_label.setText("✅ Basit kontroller tamamlandı")
        
    def update_counters(self):
        """Sayaçları güncelle"""
        passed = sum(1 for w in self.check_widgets if w.status_icon.status == "passed")
        failed = sum(1 for w in self.check_widgets if w.status_icon.status == "failed")
        warning = sum(1 for w in self.check_widgets if w.status_icon.status == "warning")
        
        self.passed_count.setText(str(passed))
        self.failed_count.setText(str(failed))
        self.warning_count.setText(str(warning))
        
        # Renklendirme
        self.passed_count.setStyleSheet("color: #27ae60; font-weight: bold;")
        self.failed_count.setStyleSheet("color: #e74c3c; font-weight: bold;")
        self.warning_count.setStyleSheet("color: #f39c12; font-weight: bold;")
        
    def calculate_final_safety_status(self):
        """Final güvenlik durumu hesapla"""
        passed = sum(1 for w in self.check_widgets if w.status_icon.status == "passed")
        failed = sum(1 for w in self.check_widgets if w.status_icon.status == "failed")
        warning = sum(1 for w in self.check_widgets if w.status_icon.status == "warning")
        
        # Kritik başarısızlık sayısı
        critical_failed = sum(1 for w in self.check_widgets 
                            if w.status_icon.status == "failed" and w.item.critical)
        
        if critical_failed > 0:
            self.safety_status_label.setText("🚨 UÇUŞ GÜVENLİ DEĞİL")
            self.safety_status_label.setStyleSheet("background-color: #e74c3c; color: white; font-weight: bold; padding: 8px; border-radius: 4px;")
            self.safety_recommendation.setText(f"{critical_failed} kritik hata! Uçuş yapmayın!")
            self.safety_recommendation.setStyleSheet("color: #e74c3c; font-weight: bold;")
        elif failed > 0:
            self.safety_status_label.setText("⚠️ DİKKATLİ UÇUŞ")
            self.safety_status_label.setStyleSheet("background-color: #f39c12; color: white; font-weight: bold; padding: 8px; border-radius: 4px;")
            self.safety_recommendation.setText(f"{failed} sistem hatası var. Kontrol edin.")
            self.safety_recommendation.setStyleSheet("color: #f39c12; font-weight: bold;")
        elif warning > 0:
            self.safety_status_label.setText("✅ UÇUŞ GÜVENLİ (Uyarılarla)")
            self.safety_status_label.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold; padding: 8px; border-radius: 4px;")
            self.safety_recommendation.setText(f"Güvenli fakat {warning} uyarı var.")
            self.safety_recommendation.setStyleSheet("color: #27ae60; font-weight: bold;")
        else:
            self.safety_status_label.setText("🎉 MÜKEMMEL - UÇUŞ GÜVENLİ")
            self.safety_status_label.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold; padding: 8px; border-radius: 4px;")
            self.safety_recommendation.setText("Tüm sistemler normal! Güvenli uçuşlar.")
            self.safety_recommendation.setStyleSheet("color: #27ae60; font-weight: bold;")
    
    def export_report(self):
        """Rapor çıkart"""
        try:
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Basit Preflight Check Raporu Kaydet",
                f"simple_preflight_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                "Text Files (*.txt);;All Files (*)"
            )
            
            if file_path:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write("="*60 + "\n")
                    f.write("🚁 BASİT MAVSDK PREFLIGHT CHECK RAPORU\n")
                    f.write("="*60 + "\n")
                    f.write(f"Rapor Tarihi: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"Bağlantı: {self.get_connection_string()}\n")
                    f.write(f"MAVSDK: {'✅ Mevcut' if MAVSDK_AVAILABLE else '❌ Eksik'}\n")
                    f.write("Kontrol Tipi: Basit Telemetri Kontrolleri (UUID yok)\n")
                    f.write("\n")
                    
                    # Özet
                    f.write("📊 ÖZET\n")
                    f.write("-"*30 + "\n")
                    f.write(f"Toplam: {len(self.check_widgets)}\n")
                    f.write(f"✅ Başarılı: {self.passed_count.text()}\n")
                    f.write(f"❌ Başarısız: {self.failed_count.text()}\n")
                    f.write(f"⚠️ Uyarı: {self.warning_count.text()}\n")
                    f.write("\n")
                    
                    # Güvenlik
                    f.write("🛡️ GÜVENLİK\n")
                    f.write("-"*30 + "\n")
                    f.write(f"Durum: {self.safety_status_label.text()}\n")
                    f.write(f"Öneri: {self.safety_recommendation.text()}\n")
                    f.write("\n")
                    
                    # Detaylar
                    f.write("📝 DETAYLAR\n")
                    f.write("-"*30 + "\n")
                    
                    for widget in self.check_widgets:
                        item = widget.item
                        status = widget.status_icon.status
                        timestamp = widget.timestamp_label.text()
                        details = widget.details_label.text()
                        
                        status_text = {
                            "passed": "✅ BAŞARILI",
                            "failed": "❌ BAŞARISIZ", 
                            "warning": "⚠️ UYARI",
                            "pending": "⏳ BEKLENİYOR"
                        }.get(status, "❓ BİLİNMEYEN")
                        
                        criticality = " [KRİTİK]" if item.critical else ""
                        f.write(f"\n{item.name}{criticality}:\n")
                        f.write(f"  Durum: {status_text}\n")
                        f.write(f"  Check: {item.check_type}\n")
                        f.write(f"  Zaman: {timestamp}\n")
                        f.write(f"  Detay: {details}\n")
                    
                    # Log
                    f.write("\n" + "="*60 + "\n")
                    f.write("📋 LOG GEÇMİŞİ\n")
                    f.write("="*60 + "\n")
                    f.write(self.detail_log.toPlainText())
                
                self.detail_log.append(f"📄 Rapor kaydedildi: {file_path}")
                
        except Exception as e:
            self.detail_log.append(f"❌ Rapor hatası: {str(e)}")

# ==================== KOLAY KULLANIM ====================

def open_simple_preflight_check(connection_manager=None):
    """
    Ana arayüzden çağrılacak basit preflight check
    
    Args:
        connection_manager: MAVSDK connection manager
    
    Returns:
        SimplePreflightDialog: Dialog objesi
    """
    try:
        if not MAVSDK_AVAILABLE:
            print("⚠️ MAVSDK kütüphanesi bulunamadı!")
            
            try:
                from PyQt5.QtWidgets import QMessageBox
                reply = QMessageBox.question(
                    None, 
                    "MAVSDK Bulunamadı",
                    "MAVSDK kütüphanesi bulunamadı!\n\n"
                    "Basit kontroller çalışmayacak.\n"
                    "Devam etmek istiyor musunuz?\n\n"
                    "MAVSDK kurulumu:\n"
                    "pip install mavsdk",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                
                if reply == QMessageBox.No:
                    return None
            except:
                pass
        
        dialog = SimplePreflightDialog(
            parent=None, 
            connection_manager=connection_manager
        )
        
        print("🚁 Basit Preflight Check Dialog açılıyor...")
        return dialog
        
    except Exception as e:
        print(f"❌ Dialog hatası: {e}")
        traceback.print_exc()
        return None

# ==================== TEST ====================

def test_simple_preflight():
    """Test fonksiyonu"""
    
    import sys
    
    class MockConnectionManager:
        def __init__(self, connection_string="udp://:14540"):
            self.connection_string = connection_string
            self._connected = True
        
        def is_connected(self):
            return self._connected
        
        def get_connection_string(self):
            return self.connection_string
    
    app = QApplication(sys.argv)
    app.setApplicationName("Basit Preflight Check Test")
    
    print("="*50)
    print("🚁 BASİT MAVSDK PREFLIGHT CHECK TEST")
    print("="*50)
    print(f"📚 MAVSDK: {'✅ Mevcut' if MAVSDK_AVAILABLE else '❌ Eksik'}")
    print("⚡ Basit telemetri kontrolleri - UUID yok!")
    print("🔄 Subprocess tabanlı - Hızlı ve güvenilir")
    print("="*50)
    
    connection_string = sys.argv[1] if len(sys.argv) > 1 else "udp://:14540"
    print(f"🔗 Test bağlantı: {connection_string}")
    
    connection_manager = MockConnectionManager(connection_string)
    
    dialog = open_simple_preflight_check(connection_manager)
    
    if dialog:
        dialog.show()
        print("🖥️ Dialog gösteriliyor...")
        
        exit_code = app.exec_()
        print("✅ Test tamamlandı.")
        return exit_code
    else:
        print("❌ Dialog açılamadı!")
        return 1

# ==================== KULLANIM ====================

"""
# ANA ARAYÜZDE KULLANIM:

from simplified_mavsdk_preflight import open_simple_preflight_check

# Buton event:
def on_preflight_clicked(self):
    dialog = open_simple_preflight_check(self.connection_manager)
    if dialog:
        dialog.exec_()

# ÖZELLİKLER:
✅ Basit MAVSDK telemetri kontrolleri
✅ UUID karmaşıklığı YOK
✅ Subprocess tabanlı - güvenli
✅ Hızlı ve anlaşılır
✅ Aynı UI kalitesi
✅ Kolay entegrasyon
✅ Kritik güvenlik kontrolleri
✅ Rapor çıktısı

# KONTROL LİSTESİ:
🔗 MAVSDK Bağlantısı - Temel bağlantı
🛰️ GPS Durumu - Uydu sayısı ve fix
🔋 Batarya - Yüzde ve voltaj
📍 Pozisyon - GPS koordinatları
🔒 ARM Durumu - Motor güvenliği
✈️ Uçuş Modu - Aktif mod
🏃 Hız - Hareket kontrolü
📐 Açı - Roll/Pitch durumu
"""

if __name__ == "__main__":
    exit_code = test_simple_preflight()
    sys.exit(exit_code)
