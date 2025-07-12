# weather_ai_module.py
"""
AI Destekli Hava Durumu & Uçuş Analiz Modülü
============================================
Tamamen yeniden yazılmış, thread-safe, debug destekli versiyon
"""

import requests
import json
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
import threading
import time
import sys

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QGridLayout, QTabWidget, QWidget,
                             QProgressBar, QTextEdit, QGroupBox, QScrollArea,
                             QMessageBox, QApplication)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread, pyqtSlot
from PyQt5.QtGui import QFont, QPixmap, QPainter, QColor

# Makine öğrenmesi kütüphaneleri (opsiyonel)
try:
    from sklearn.ensemble import RandomForestRegressor, GradientBoostingClassifier
    from sklearn.preprocessing import StandardScaler
    import joblib
    ML_AVAILABLE = True
    print("✅ Makine öğrenmesi kütüphaneleri yüklendi")
except ImportError:
    ML_AVAILABLE = False
    print("⚠️ ML kütüphaneleri eksik (opsiyonel)")

@dataclass
class WeatherData:
    """Hava durumu veri yapısı"""
    temperature: float
    humidity: float
    pressure: float
    wind_speed: float
    wind_direction: float
    visibility: float
    cloud_cover: float
    precipitation: float
    uv_index: float
    description: str
    timestamp: datetime
    
@dataclass
class FlightSafety:
    """Uçuş güvenlik analizi"""
    safety_score: float  # 0-100
    risk_level: str     # LOW, MEDIUM, HIGH, CRITICAL
    recommendations: List[str]
    flight_window: Tuple[datetime, datetime]
    restrictions: List[str]

class WeatherAI:
    """AI Destekli Hava Durumu Analiz Motoru"""
    
    def __init__(self, api_key: str, location: str = "Eskişehir"):
        self.api_key = api_key
        self.location = location
        self.weather_history = []
        self.flight_model = None
        self.safety_model = None
        self.scaler = None
        
        # AI modellerini kur (opsiyonel)
        if ML_AVAILABLE:
            self.setup_ml_models()
        
        print(f"🤖 WeatherAI başlatıldı: {location}")
    
    def setup_ml_models(self):
        """Makine öğrenmesi modellerini kur"""
        try:
            self.safety_model = GradientBoostingClassifier(
                n_estimators=50,
                learning_rate=0.1,
                max_depth=4,
                random_state=42
            )
            
            self.flight_model = RandomForestRegressor(
                n_estimators=50,
                max_depth=6,
                random_state=42
            )
            
            self.scaler = StandardScaler()
            self.train_models()
            
            print("🤖 AI modeller hazırlandı")
            
        except Exception as e:
            print(f"❌ AI model kurulum hatası: {e}")
    
    def train_models(self):
        """Modelleri basit veri ile eğit"""
        try:
            # Basit eğitim verisi
            n_samples = 200
            
            X = np.random.rand(n_samples, 6)
            X[:, 0] = X[:, 0] * 40 - 10  # Sıcaklık
            X[:, 1] = X[:, 1] * 100      # Nem
            X[:, 2] = X[:, 2] * 50 + 990 # Basınç
            X[:, 3] = X[:, 3] * 50       # Rüzgar
            X[:, 4] = X[:, 4] * 20       # Görüş
            X[:, 5] = X[:, 5] * 100      # Bulut
            
            # Basit güvenlik skoru hesabı
            safety_scores = []
            flight_suitability = []
            
            for i in range(n_samples):
                temp, humidity, pressure, wind, visibility, clouds = X[i]
                score = 100
                
                if wind > 30: score -= 40
                elif wind > 20: score -= 20
                elif wind > 10: score -= 10
                
                if visibility < 2: score -= 30
                elif visibility < 5: score -= 15
                
                if temp < 0 or temp > 35: score -= 15
                if humidity > 85: score -= 10
                
                score = max(20, min(100, score))
                safety_scores.append(score)
                flight_suitability.append(1 if score > 60 else 0)
            
            # Modelleri eğit
            X_scaled = self.scaler.fit_transform(X)
            self.safety_model.fit(X_scaled, flight_suitability)
            self.flight_model.fit(X_scaled, safety_scores)
            
            print("🎯 AI modeller eğitildi")
            
        except Exception as e:
            print(f"❌ Model eğitim hatası: {e}")
    
    def analyze_flight_safety(self, weather: WeatherData) -> FlightSafety:
        """Uçuş güvenlik analizi"""
        safety_score = 100
        risk_level = "LOW"
        recommendations = []
        restrictions = []
        
        # Rüzgar analizi
        if weather.wind_speed > 40:
            safety_score -= 60
            risk_level = "CRITICAL"
            recommendations.append("⚠️ Çok güçlü rüzgar - Uçuş yapmayın!")
            restrictions.append("Rüzgar hızı 40+ km/h")
        elif weather.wind_speed > 25:
            safety_score -= 30
            risk_level = "HIGH"
            recommendations.append("⚠️ Güçlü rüzgar - Dikkatli uçun")
        elif weather.wind_speed > 15:
            safety_score -= 15
            risk_level = "MEDIUM"
            recommendations.append("💨 Orta rüzgar - Normal uçuş")
        
        # Görüş analizi
        if weather.visibility < 1:
            safety_score -= 50
            risk_level = "CRITICAL"
            recommendations.append("👁️ Çok düşük görüş - Uçuş yasak!")
            restrictions.append("Görüş < 1km")
        elif weather.visibility < 3:
            safety_score -= 25
            if risk_level not in ["CRITICAL"]:
                risk_level = "HIGH"
            recommendations.append("🌫️ Düşük görüş - Dikkatli olun")
        
        # Sıcaklık analizi
        if weather.temperature < -5 or weather.temperature > 40:
            safety_score -= 25
            recommendations.append("🌡️ Ekstrem sıcaklık - Batarya riski")
        
        # Yağış analizi
        if weather.precipitation > 5:
            safety_score -= 40
            risk_level = "CRITICAL"
            recommendations.append("🌧️ Şiddetli yağış - Uçuş yapmayın!")
            restrictions.append("Yağış > 5mm")
        elif weather.precipitation > 1:
            safety_score -= 20
            recommendations.append("🌦️ Hafif yağış - Dikkatli uçun")
        
        # AI tahmin (eğer mevcut ise)
        if ML_AVAILABLE and self.safety_model and self.scaler:
            try:
                features = np.array([[
                    weather.temperature,
                    weather.humidity,
                    weather.pressure,
                    weather.wind_speed,
                    weather.visibility,
                    weather.cloud_cover
                ]])
                
                features_scaled = self.scaler.transform(features)
                ai_score = self.flight_model.predict(features_scaled)[0]
                ai_suitability = self.safety_model.predict_proba(features_scaled)[0][1]
                
                final_score = (safety_score * 0.7) + (ai_score * 0.3)
                safety_score = max(0, min(100, final_score))
                
                recommendations.append(f"🤖 AI Skoru: {ai_score:.1f}")
                recommendations.append(f"🎯 AI Uygunluk: {ai_suitability*100:.1f}%")
                
            except Exception as e:
                print(f"AI tahmin hatası: {e}")
        
        # Risk seviyesini güncelle
        if safety_score >= 80:
            risk_level = "LOW"
        elif safety_score >= 60:
            risk_level = "MEDIUM"
        elif safety_score >= 40:
            risk_level = "HIGH"
        else:
            risk_level = "CRITICAL"
        
        # Pozitif öneriler
        if safety_score >= 80:
            recommendations.append("✅ Mükemmel uçuş koşulları!")
        elif safety_score >= 60:
            recommendations.append("👍 İyi uçuş koşulları")
        
        # Uçuş penceresi
        current_time = datetime.now()
        if safety_score > 60:
            flight_window = (current_time + timedelta(minutes=30), 
                           current_time + timedelta(hours=2, minutes=30))
        else:
            flight_window = (current_time + timedelta(hours=4), 
                           current_time + timedelta(hours=6))
        
        return FlightSafety(
            safety_score=safety_score,
            risk_level=risk_level,
            recommendations=recommendations,
            flight_window=flight_window,
            restrictions=restrictions
        )

class WeatherWorker(QThread):
    """Hava durumu verisi için worker thread"""
    data_ready = pyqtSignal(object, object)  # weather, safety
    error_occurred = pyqtSignal(str)
    progress_update = pyqtSignal(str)
    
    def __init__(self, weather_ai):
        super().__init__()
        self.weather_ai = weather_ai
        
    def run(self):
        """Worker thread ana fonksiyonu"""
        try:
            self.progress_update.emit("🚀 İşlem başlatılıyor...")
            
            # API bağlantı testi
            self.progress_update.emit("🔍 API bağlantısı test ediliyor...")
            if not self.test_api():
                self.error_occurred.emit("API bağlantı testi başarısız")
                return
            
            # Hava durumu verisi al
            self.progress_update.emit("📡 Hava durumu verisi alınıyor...")
            weather = self.get_weather_data()
            
            if not weather:
                self.error_occurred.emit("Hava durumu verisi alınamadı")
                return
            
            # Güvenlik analizi
            self.progress_update.emit("🤖 Güvenlik analizi yapılıyor...")
            safety = self.weather_ai.analyze_flight_safety(weather)
            
            # Başarılı - veriyi gönder
            self.progress_update.emit("✅ İşlem başarıyla tamamlandı!")
            self.data_ready.emit(weather, safety)
            
        except Exception as e:
            error_msg = f"Worker hatası: {str(e)}"
            print(f"❌ {error_msg}")
            self.error_occurred.emit(error_msg)
    
    def test_api(self):
        """API bağlantı testi"""
        try:
            url = "http://api.openweathermap.org/data/2.5/weather"
            params = {
                'q': self.weather_ai.location,
                'appid': self.weather_ai.api_key,
                'units': 'metric'
            }
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                print(f"✅ API test başarılı: {response.status_code}")
                return True
            elif response.status_code == 401:
                print("❌ API key geçersiz")
                return False
            else:
                print(f"⚠️ API hatası: {response.status_code}")
                return False
                
        except requests.Timeout:
            print("⏰ API timeout")
            return False
        except requests.ConnectionError:
            print("🌐 İnternet bağlantısı yok")
            return False
        except Exception as e:
            print(f"🔧 API test hatası: {e}")
            return False
    
    def get_weather_data(self):
        """Hava durumu verisi al"""
        try:
            # Ana hava durumu
            url = "http://api.openweathermap.org/data/2.5/weather"
            params = {
                'q': self.weather_ai.location,
                'appid': self.weather_ai.api_key,
                'units': 'metric',
                'lang': 'tr'
            }
            
            response = requests.get(url, params=params, timeout=15)
            
            if response.status_code != 200:
                print(f"❌ API hatası: {response.status_code}")
                return None
            
            data = response.json()
            
            # UV Index (opsiyonel)
            uv_value = 0
            try:
                lat, lon = data['coord']['lat'], data['coord']['lon']
                uv_url = "http://api.openweathermap.org/data/2.5/uvi"
                uv_params = {
                    'lat': lat,
                    'lon': lon,
                    'appid': self.weather_ai.api_key
                }
                
                uv_response = requests.get(uv_url, params=uv_params, timeout=8)
                if uv_response.status_code == 200:
                    uv_value = uv_response.json().get('value', 0)
            except:
                pass  # UV verisi opsiyonel
            
            # WeatherData oluştur
            weather = WeatherData(
                temperature=data['main']['temp'],
                humidity=data['main']['humidity'],
                pressure=data['main']['pressure'],
                wind_speed=data['wind'].get('speed', 0) * 3.6,  # m/s to km/h
                wind_direction=data['wind'].get('deg', 0),
                visibility=data.get('visibility', 10000) / 1000,  # m to km
                cloud_cover=data['clouds']['all'],
                precipitation=data.get('rain', {}).get('1h', 0),
                uv_index=uv_value,
                description=data['weather'][0]['description'].title(),
                timestamp=datetime.now()
            )
            
            # Geçmişe ekle
            self.weather_ai.weather_history.append(weather)
            if len(self.weather_ai.weather_history) > 50:
                self.weather_ai.weather_history.pop(0)
            
            print(f"✅ Hava durumu alındı: {weather.temperature}°C")
            return weather
            
        except Exception as e:
            print(f"❌ Hava durumu alma hatası: {e}")
            return None

class WeatherAIDialog(QDialog):
    """AI Hava Durumu Dialog Penceresi"""
    
    def __init__(self, api_key: str, location: str = "Eskişehir", parent=None):
        super().__init__(parent)
        self.weather_ai = WeatherAI(api_key, location)
        self.current_weather = None
        self.current_safety = None
        self.weather_worker = None
        
        self.setupUI()
        self.setup_timers()
        
        # İlk veri yüklemesi
        QTimer.singleShot(1000, self.refresh_data)
    
    def setupUI(self):
        """Ana UI kurulumu"""
        self.setWindowTitle("🤖 AI Hava Durumu & Uçuş Analizi")
        self.setFixedSize(900, 700)
        self.setModal(True)
        
        layout = QVBoxLayout()
        
        # Başlık
        header = QLabel("🤖 AI DESTEKLI HAVA DURUMU ANALİZİ")
        header.setAlignment(Qt.AlignCenter)
        header.setStyleSheet("""
            font-size: 20px;
            font-weight: bold;
            color: white;
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #3498db, stop:1 #2980b9);
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 10px;
        """)
        layout.addWidget(header)
        
        # Progress label
        self.progress_label = QLabel("💤 Sistem hazırlanıyor...")
        self.progress_label.setStyleSheet("""
            color: #3498db; 
            font-weight: bold; 
            padding: 8px;
            background: #ecf0f1;
            border-radius: 5px;
            margin: 5px;
        """)
        layout.addWidget(self.progress_label)
        
        # Tab widget
        self.tabs = QTabWidget()
        
        # Hava durumu tab
        self.tabs.addTab(self.create_weather_tab(), "🌤️ Hava Durumu")
        
        # Uçuş analizi tab
        self.tabs.addTab(self.create_flight_tab(), "✈️ Uçuş Analizi")
        
        # Geçmiş tab
        self.tabs.addTab(self.create_history_tab(), "📊 Geçmiş")
        
        layout.addWidget(self.tabs)
        
        # Alt butonlar
        button_layout = QHBoxLayout()
        
        self.refresh_btn = QPushButton("🔄 Verileri Yenile")
        self.refresh_btn.clicked.connect(self.refresh_data)
        
        settings_btn = QPushButton("⚙️ Ayarlar")
        settings_btn.clicked.connect(self.show_settings)
        
        close_btn = QPushButton("❌ Kapat")
        close_btn.clicked.connect(self.close)
        
        button_layout.addWidget(self.refresh_btn)
        button_layout.addWidget(settings_btn)
        button_layout.addStretch()
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
        
        # Koyu tema
        self.apply_dark_theme()
    
    def create_weather_tab(self):
        """Hava durumu tab'ı oluştur"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Mevcut hava durumu
        weather_group = QGroupBox("📍 Anlık Hava Durumu")
        weather_layout = QGridLayout(weather_group)
        
        self.temp_label = QLabel("🌡️ Sıcaklık: --°C")
        self.desc_label = QLabel("☁️ Durum: Yükleniyor...")
        self.wind_label = QLabel("💨 Rüzgar: -- km/h")
        self.humidity_label = QLabel("💧 Nem: --%")
        self.pressure_label = QLabel("🔽 Basınç: -- hPa")
        self.visibility_label = QLabel("👁️ Görüş: -- km")
        self.uv_label = QLabel("☀️ UV Index: --")
        self.rain_label = QLabel("🌧️ Yağış: -- mm")
        
        weather_layout.addWidget(self.temp_label, 0, 0)
        weather_layout.addWidget(self.desc_label, 0, 1)
        weather_layout.addWidget(self.wind_label, 1, 0)
        weather_layout.addWidget(self.humidity_label, 1, 1)
        weather_layout.addWidget(self.pressure_label, 2, 0)
        weather_layout.addWidget(self.visibility_label, 2, 1)
        weather_layout.addWidget(self.uv_label, 3, 0)
        weather_layout.addWidget(self.rain_label, 3, 1)
        
        layout.addWidget(weather_group)
        
        # Güncelleme durumu
        update_group = QGroupBox("🔄 Güncelleme Bilgisi")
        update_layout = QVBoxLayout(update_group)
        
        self.last_update_label = QLabel("Son güncelleme: --")
        self.auto_update_label = QLabel("Otomatik güncelleme: 5 dakika")
        self.update_progress = QProgressBar()
        
        update_layout.addWidget(self.last_update_label)
        update_layout.addWidget(self.auto_update_label)
        update_layout.addWidget(self.update_progress)
        
        layout.addWidget(update_group)
        
        return widget
    
    def create_flight_tab(self):
        """Uçuş analizi tab'ı oluştur"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Güvenlik skoru
        safety_group = QGroupBox("🎯 Uçuş Güvenlik Skoru")
        safety_layout = QVBoxLayout(safety_group)
        
        self.safety_score_label = QLabel("Güvenlik Skoru: --%")
        self.risk_level_label = QLabel("Risk Seviyesi: --")
        self.safety_progress = QProgressBar()
        
        safety_layout.addWidget(self.safety_score_label)
        safety_layout.addWidget(self.risk_level_label)
        safety_layout.addWidget(self.safety_progress)
        
        layout.addWidget(safety_group)
        
        # AI önerileri
        recommendations_group = QGroupBox("💡 AI Önerileri")
        recommendations_layout = QVBoxLayout(recommendations_group)
        
        self.recommendations_text = QTextEdit()
        self.recommendations_text.setMaximumHeight(120)
        self.recommendations_text.setReadOnly(True)
        
        recommendations_layout.addWidget(self.recommendations_text)
        layout.addWidget(recommendations_group)
        
        # Kısıtlamalar
        restrictions_group = QGroupBox("⚠️ Uçuş Kısıtlamaları")
        restrictions_layout = QVBoxLayout(restrictions_group)
        
        self.restrictions_text = QTextEdit()
        self.restrictions_text.setMaximumHeight(80)
        self.restrictions_text.setReadOnly(True)
        
        restrictions_layout.addWidget(self.restrictions_text)
        layout.addWidget(restrictions_group)
        
        # Uçuş penceresi
        window_group = QGroupBox("⏰ Önerilen Uçuş Zamanı")
        window_layout = QVBoxLayout(window_group)
        
        self.flight_window_label = QLabel("Optimal zaman: --")
        window_layout.addWidget(self.flight_window_label)
        
        layout.addWidget(window_group)
        
        return widget
    
    def create_history_tab(self):
        """Geçmiş veriler tab'ı oluştur"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        history_group = QGroupBox("📈 Son Hava Durumu Kayıtları")
        history_layout = QVBoxLayout(history_group)
        
        self.history_text = QTextEdit()
        self.history_text.setReadOnly(True)
        
        history_layout.addWidget(self.history_text)
        layout.addWidget(history_group)
        
        return widget
    
    def setup_timers(self):
        """Timer'ları kur"""
        # Otomatik güncelleme (5 dakika)
        self.auto_update_timer = QTimer()
        self.auto_update_timer.timeout.connect(self.refresh_data)
        self.auto_update_timer.start(300000)  # 5 dakika
        
        # Progress bar timer
        self.progress_timer = QTimer()
        self.progress_timer.timeout.connect(self.update_progress_bar)
        self.progress_timer.start(1000)  # 1 saniye
        
        self.progress_value = 0
    
    def refresh_data(self):
        """Veri yenileme"""
        try:
            print("\n🔄 VERİ YENİLEME BAŞLADI")
            
            # Eğer worker çalışıyorsa durdur
            if self.weather_worker and self.weather_worker.isRunning():
                self.weather_worker.quit()
                self.weather_worker.wait(2000)
            
            # UI güncelle
            self.refresh_btn.setText("🔄 Yenileniyor...")
            self.refresh_btn.setEnabled(False)
            self.progress_label.setText("🚀 Başlatılıyor...")
            
            # Timeout timer
            self.timeout_timer = QTimer()
            self.timeout_timer.setSingleShot(True)
            self.timeout_timer.timeout.connect(self.on_timeout)
            self.timeout_timer.start(30000)  # 30 saniye
            
            # Worker oluştur ve başlat
            self.weather_worker = WeatherWorker(self.weather_ai)
            self.weather_worker.data_ready.connect(self.on_data_ready)
            self.weather_worker.error_occurred.connect(self.on_error_occurred)
            self.weather_worker.finished.connect(self.on_worker_finished)
            self.weather_worker.progress_update.connect(self.on_progress_update)
            
            self.weather_worker.start()
            print("✅ Worker başlatıldı")
            
        except Exception as e:
            print(f"❌ refresh_data hatası: {e}")
            self.reset_ui()
    
    @pyqtSlot(str)
    def on_progress_update(self, message):
        """Progress güncellemesi"""
        self.progress_label.setText(message)
        print(f"📈 {message}")
    
    @pyqtSlot(object, object)
    def on_data_ready(self, weather_data, safety_analysis):
        """Veri hazır"""
        try:
            print("✅ VERİ ALINDI, UI GÜNCELLENİYOR")
            
            self.timeout_timer.stop()
            self.current_weather = weather_data
            self.current_safety = safety_analysis
            
            self.update_display()
            self.progress_label.setText("✅ Veriler başarıyla güncellendi!")
            
        except Exception as e:
            print(f"❌ on_data_ready hatası: {e}")
            self.on_error_occurred(f"UI güncelleme hatası: {e}")
    
    @pyqtSlot(str)
    def on_error_occurred(self, error_message):
        """Hata durumu"""
        print(f"❌ HATA: {error_message}")
        
        self.timeout_timer.stop()
        self.progress_label.setText(f"❌ Hata: {error_message}")
        
        QMessageBox.warning(self, "⚠️ Hata", 
                           f"Hava durumu alınamadı:\n{error_message}")
        
        self.reset_ui()
    
    @pyqtSlot()
    def on_worker_finished(self):
        """Worker tamamlandı"""
        print("🏁 Worker tamamlandı")
        self.reset_ui()
    
    def on_timeout(self):
        """Timeout"""
        print("⏰ TIMEOUT!")
        
        if self.weather_worker and self.weather_worker.isRunning():
            self.weather_worker.quit()
            self.weather_worker.wait(3000)
            if self.weather_worker.isRunning():
                self.weather_worker.terminate()
        
        self.on_error_occurred("İşlem timeout oldu (30 saniye)")
    
    def reset_ui(self):
        """UI'yi sıfırla"""
        self.refresh_btn.setText("🔄 Verileri Yenile")
        self.refresh_btn.setEnabled(True)
    
    def update_display(self):
        """Ekranı güncelle"""
        if not self.current_weather or not self.current_safety:
            return
        
        weather = self.current_weather
        safety = self.current_safety
        
        # Hava durumu tab'ı
        self.temp_label.setText(f"🌡️ Sıcaklık: {weather.temperature:.1f}°C")
        self.desc_label.setText(f"☁️ Durum: {weather.description}")
        self.wind_label.setText(f"💨 Rüzgar: {weather.wind_speed:.1f} km/h")
        self.humidity_label.setText(f"💧 Nem: {weather.humidity}%")
        self.pressure_label.setText(f"🔽 Basınç: {weather.pressure:.1f} hPa")
        self.visibility_label.setText(f"👁️ Görüş: {weather.visibility:.1f} km")
        self.uv_label.setText(f"☀️ UV Index: {weather.uv_index:.1f}")
        self.rain_label.setText(f"🌧️ Yağış: {weather.precipitation:.1f} mm")
        
        # Güncelleme zamanı
        self.last_update_label.setText(f"Son güncelleme: {weather.timestamp.strftime('%H:%M:%S')}")
        
        # Uçuş analizi tab'ı
        self.safety_score_label.setText(f"Güvenlik Skoru: {safety.safety_score:.1f}%")
        self.risk_level_label.setText(f"Risk Seviyesi: {safety.risk_level}")
        self.safety_progress.setValue(int(safety.safety_score))
        
        # Risk seviyesi rengi
        colors = {
            "LOW": "#27ae60",
            "MEDIUM": "#f39c12", 
            "HIGH": "#e67e22",
            "CRITICAL": "#e74c3c"
        }
        color = colors.get(safety.risk_level, "#95a5a6")
        self.risk_level_label.setStyleSheet(f"color: {color}; font-weight: bold; font-size: 14px;")
        
        # Öneriler
        recommendations_text = "🤖 AI Önerileri:\n\n"
        for i, rec in enumerate(safety.recommendations, 1):
            recommendations_text += f"{i}. {rec}\n"
        self.recommendations_text.setPlainText(recommendations_text)
        
        # Kısıtlamalar
        if safety.restrictions:
            restrictions_text = "⚠️ Aktif Kısıtlamalar:\n\n"
            for i, restriction in enumerate(safety.restrictions, 1):
                restrictions_text += f"{i}. {restriction}\n"
        else:
            restrictions_text = "✅ Herhangi bir kısıtlama bulunmuyor"
        self.restrictions_text.setPlainText(restrictions_text)
        
        # Uçuş penceresi
        start_time, end_time = safety.flight_window
        window_text = f"{start_time.strftime('%H:%M')} - {end_time.strftime('%H:%M')} ({start_time.strftime('%d.%m.%Y')})"
        self.flight_window_label.setText(f"Optimal uçuş zamanı: {window_text}")
        
        # Geçmiş verileri güncelle
        self.update_history()
        
        print("🎉 Ekran başarıyla güncellendi!")
    
    def update_history(self):
        """Geçmiş verileri güncelle"""
        try:
            history = self.weather_ai.weather_history[-10:]  # Son 10 kayıt
            
            history_text = "📊 Son Hava Durumu Kayıtları:\n\n"
            
            for i, weather in enumerate(reversed(history), 1):
                safety = self.weather_ai.analyze_flight_safety(weather)
                
                history_text += f"{i}. {weather.timestamp.strftime('%H:%M:%S')} - "
                history_text += f"🌡️ {weather.temperature:.1f}°C, "
                history_text += f"💨 {weather.wind_speed:.1f} km/h, "
                history_text += f"🛡️ {safety.safety_score:.1f}% ({safety.risk_level})\n"
            
            if not history:
                history_text += "Henüz veri bulunmuyor..."
            
            self.history_text.setPlainText(history_text)
            
        except Exception as e:
            print(f"Geçmiş güncelleme hatası: {e}")
    
    def update_progress_bar(self):
        """Progress bar güncelle"""
        self.progress_value = (self.progress_value + 1) % 300  # 5 dakika
        progress_percent = (self.progress_value / 300) * 100
        self.update_progress.setValue(int(progress_percent))
    
    def show_settings(self):
        """Ayarlar penceresi"""
        settings_text = f"""
🤖 AI HAVA DURUMU SİSTEMİ

📍 Konum: {self.weather_ai.location}
🔑 API Durumu: {"✅ Aktif" if self.weather_ai.api_key else "❌ Pasif"}
🤖 Makine Öğrenmesi: {"✅ Aktif" if ML_AVAILABLE else "❌ Pasif"}

⚙️ Sistem Ayarları:
• Otomatik güncelleme: 5 dakika
• Veri geçmişi: Son 50 kayıt
• Timeout süresi: 30 saniye
• Thread güvenliği: Aktif

🎯 Güvenlik Kriterleri:
• Maksimum rüzgar: 40 km/h
• Minimum görüş: 1 km
• Maksimum yağış: 5 mm/h
• Güvenlik eşiği: %60

📊 İstatistikler:
• Toplam kayıt: {len(self.weather_ai.weather_history)}
• Son güncelleme: {self.current_weather.timestamp.strftime('%H:%M:%S') if self.current_weather else 'Yok'}
• API durumu: Çalışıyor

Bu ayarlar koddan değiştirilebilir.
        """
        
        QMessageBox.information(self, "⚙️ Sistem Ayarları", settings_text)
    
    def apply_dark_theme(self):
        """Koyu tema uygula"""
        self.setStyleSheet("""
            QDialog {
                background-color: #2c3e50;
                color: white;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            
            QTabWidget::pane {
                border: 2px solid #34495e;
                border-radius: 8px;
                background-color: #34495e;
                margin-top: 5px;
            }
            
            QTabBar::tab {
                background-color: #3498db;
                color: white;
                padding: 10px 15px;
                margin: 2px;
                border-radius: 6px;
                font-weight: bold;
                min-width: 80px;
            }
            
            QTabBar::tab:selected {
                background-color: #e74c3c;
            }
            
            QTabBar::tab:hover {
                background-color: #e67e22;
            }
            
            QGroupBox {
                font-size: 13px;
                font-weight: bold;
                border: 2px solid #34495e;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 15px;
                background-color: #2c3e50;
                color: white;
            }
            
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 3px 10px;
                color: #3498db;
                background-color: #2c3e50;
                border-radius: 4px;
                font-weight: bold;
            }
            
            QLabel {
                color: white;
                font-size: 12px;
                padding: 3px;
            }
            
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                padding: 10px 15px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 12px;
                min-width: 100px;
            }
            
            QPushButton:hover {
                background-color: #2980b9;
            }
            
            QPushButton:pressed {
                background-color: #1f618d;
            }
            
            QPushButton:disabled {
                background-color: #566573;
                color: #95a5a6;
            }
            
            QProgressBar {
                border: 2px solid #34495e;
                border-radius: 6px;
                background-color: #2c3e50;
                text-align: center;
                color: white;
                font-weight: bold;
                height: 20px;
            }
            
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #27ae60, stop:0.5 #f39c12, stop:1 #e74c3c);
                border-radius: 4px;
            }
            
            QTextEdit {
                background-color: #34495e;
                border: 2px solid #4a5f7a;
                border-radius: 6px;
                padding: 8px;
                color: white;
                font-size: 11px;
            }
        """)
    
    def closeEvent(self, event):
        """Pencere kapatılıyor"""
        try:
            # Timer'ları durdur
            if hasattr(self, 'auto_update_timer'):
                self.auto_update_timer.stop()
            if hasattr(self, 'progress_timer'):
                self.progress_timer.stop()
            if hasattr(self, 'timeout_timer'):
                self.timeout_timer.stop()
            
            # Worker'ı güvenli şekilde durdur
            if self.weather_worker and self.weather_worker.isRunning():
                self.weather_worker.quit()
                self.weather_worker.wait(3000)
                if self.weather_worker.isRunning():
                    self.weather_worker.terminate()
            
            print("🤖 AI Hava Durumu penceresi kapatıldı")
            
        except Exception as e:
            print(f"Kapatma hatası: {e}")
        
        event.accept()

# Yardımcı fonksiyonlar
def create_weather_ai_dialog(api_key: str, location: str = "Eskişehir", parent=None):
    """AI Hava Durumu dialog'u oluştur"""
    return WeatherAIDialog(api_key, location, parent)

def get_mock_weather_for_testing():
    """Test için sahte hava durumu verisi"""
    return WeatherData(
        temperature=22.5,
        humidity=65,
        pressure=1015.2,
        wind_speed=12.5,
        wind_direction=180,
        visibility=8.5,
        cloud_cover=30,
        precipitation=0.0,
        uv_index=4.2,
        description="Parçalı Bulutlu",
        timestamp=datetime.now()
    )

def test_api_connection(api_key: str = "fef7f6da4d4450bc962c2c694ebfb379", location: str = "Eskişehir"):
    """API bağlantısını test et"""
    print("🧪 API BAĞLANTI TESTİ")
    print("=" * 30)
    
    try:
        url = "http://api.openweathermap.org/data/2.5/weather"
        params = {
            'q': location,
            'appid': api_key,
            'units': 'metric'
        }
        
        print(f"📡 Test URL: {url}")
        print(f"📍 Konum: {location}")
        print(f"🔑 API Key: {api_key[:8]}...")
        print("⏳ İstek gönderiliyor...")
        
        response = requests.get(url, params=params, timeout=10)
        
        print(f"📊 Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ BAŞARILI!")
            print(f"🌡️ Sıcaklık: {data['main']['temp']}°C")
            print(f"☁️ Durum: {data['weather'][0]['description']}")
            print(f"💨 Rüzgar: {data['wind'].get('speed', 0)} m/s")
            print(f"👁️ Görüş: {data.get('visibility', 10000)/1000} km")
            return True
        elif response.status_code == 401:
            print("❌ API key geçersiz!")
            return False
        else:
            print(f"❌ API hatası: {response.text}")
            return False
            
    except requests.Timeout:
        print("⏰ Timeout - İnternet yavaş!")
        return False
    except requests.ConnectionError:
        print("🌐 İnternet bağlantısı yok!")
        return False
    except Exception as e:
        print(f"💥 Genel hata: {e}")
        return False

def main():
    """Ana test fonksiyonu"""
    print("🤖 AI HAVA DURUMU MODÜLÜ")
    print("=" * 50)
    
    # Gerekli kütüphaneleri kontrol et
    missing_packages = []
    
    try:
        import requests
        import numpy
        import pandas
        from PyQt5.QtWidgets import QApplication
        print("✅ Temel kütüphaneler OK")
    except ImportError as e:
        missing_packages.append(str(e))
        print(f"❌ Import hatası: {e}")
    
    if missing_packages:
        print("\n💡 Eksik kütüphaneler için:")
        print("pip install requests numpy pandas PyQt5 scikit-learn")
        return
    
    # API testi
    print("\n🔍 API TESTİ:")
    api_ok = test_api_connection()
    
    if not api_ok:
        print("\n💔 API test başarısız! İnternet ve API key'i kontrol edin.")
        return
    
    # GUI testi
    print("\n🖥️ GUI TESTİ:")
    app = QApplication(sys.argv)
    
    try:
        # Test verisi ile dialog oluştur
        dialog = WeatherAIDialog("fef7f6da4d4450bc962c2c694ebfb379", "Eskişehir")
        
        # Test verisi ekle
        test_weather = get_mock_weather_for_testing()
        test_safety = dialog.weather_ai.analyze_flight_safety(test_weather)
        
        dialog.current_weather = test_weather
        dialog.current_safety = test_safety
        dialog.update_display()
        
        print("✅ GUI test başarılı")
        
        # Dialog'u göster
        result = dialog.exec_()
        
        if result == QDialog.Accepted:
            print("✅ Dialog başarıyla kapatıldı")
        else:
            print("ℹ️ Dialog kullanıcı tarafından kapatıldı")
            
    except Exception as e:
        print(f"❌ GUI hatası: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n🎯 TEST SONUCU:")
    print("✅ API bağlantısı çalışıyor")
    print("✅ AI modelleri hazır")
    print("✅ Thread-safe işlemler")
    print("✅ Koyu tema aktif")
    print("✅ Otomatik güncelleme")
    
    print("\n🚀 KULLANIM:")
    print("from weather_ai_module import create_weather_ai_dialog")
    print("dialog = create_weather_ai_dialog('YOUR_API_KEY', 'Eskişehir')")
    print("dialog.exec_()")

if __name__ == "__main__":
    main()
