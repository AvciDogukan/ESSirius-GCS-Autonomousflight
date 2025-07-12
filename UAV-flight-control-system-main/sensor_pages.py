from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                            QPushButton, QGroupBox, QProgressBar, QSpinBox, QTableWidget, QSlider)
from PyQt5.QtCore import Qt
import pyqtgraph as pg

class LidarPage(QWidget):
    def __init__(self, parent=None):
        super(LidarPage, self).__init__(parent)
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
                padding: 5px;
            }
        """)

        # LiDAR Görüntüleme Paneli
        visualization_group = QGroupBox("LiDAR Görüntüleme")
        viz_layout = QVBoxLayout()
        
        # LiDAR nokta bulutu için plot widget
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground('#2c2c2c')
        self.plot_widget.setLabel('left', 'Y (m)', color='#ffffff')
        self.plot_widget.setLabel('bottom', 'X (m)', color='#ffffff')
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        
        viz_layout.addWidget(self.plot_widget)
        visualization_group.setLayout(viz_layout)
        
        # LiDAR Kontrol Paneli
        control_group = QGroupBox("LiDAR Kontrolleri")
        control_layout = QHBoxLayout()
        
        self.start_button = QPushButton("Taramayı Başlat")
        self.stop_button = QPushButton("Taramayı Durdur")
        self.save_button = QPushButton("Veriyi Kaydet")
        
        for button in [self.start_button, self.stop_button, self.save_button]:
            button.setStyleSheet("""
                QPushButton {
                    background-color: #e74c3c;
                    color: white;
                    border: none;
                    padding: 10px;
                    border-radius: 5px;
                    font-weight: bold;
                    min-width: 120px;
                }
                QPushButton:hover {
                    background-color: #c0392b;
                }
            """)
            control_layout.addWidget(button)
        
        control_group.setLayout(control_layout)
        
        main_layout.addWidget(visualization_group)
        main_layout.addWidget(control_group)
        self.setLayout(main_layout)

class GPSSpoofingPage(QWidget):
    def __init__(self, parent=None):
        super(GPSSpoofingPage, self).__init__(parent)
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
                padding: 5px;
            }
        """)

        # GPS Spoofing Kontrol Paneli
        control_group = QGroupBox("GPS Spoofing Kontrolleri")
        control_layout = QVBoxLayout()
        
        # Sinyal Gücü
        signal_layout = QHBoxLayout()
        signal_label = QLabel("Sinyal Gücü:")
        self.signal_bar = QProgressBar()
        self.signal_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #c0392b;
                border-radius: 5px;
                text-align: center;
                background-color: #2c2c2c;
            }
            QProgressBar::chunk {
                background-color: #e74c3c;
            }
        """)
        signal_layout.addWidget(signal_label)
        signal_layout.addWidget(self.signal_bar)
        
        # Frekans Ayarı
        freq_layout = QHBoxLayout()
        freq_label = QLabel("Frekans (MHz):")
        self.freq_spinbox = QSpinBox()
        self.freq_spinbox.setRange(1000, 2000)
        self.freq_spinbox.setValue(1575)  # L1 frekansı
        self.freq_spinbox.setStyleSheet("""
            QSpinBox {
                background-color: #2c2c2c;
                border: 2px solid #c0392b;
                border-radius: 5px;
                padding: 5px;
                min-width: 100px;
            }
        """)
        freq_layout.addWidget(freq_label)
        freq_layout.addWidget(self.freq_spinbox)
        
        # Butonlar
        button_layout = QHBoxLayout()
        self.start_spoof = QPushButton("Spoofing Başlat")
        self.stop_spoof = QPushButton("Spoofing Durdur")
        
        for button in [self.start_spoof, self.stop_spoof]:
            button.setStyleSheet("""
                QPushButton {
                    background-color: #e74c3c;
                    color: white;
                    border: none;
                    padding: 10px;
                    border-radius: 5px;
                    font-weight: bold;
                    min-width: 120px;
                }
                QPushButton:hover {
                    background-color: #c0392b;
                }
            """)
            button_layout.addWidget(button)
        
        control_layout.addLayout(signal_layout)
        control_layout.addLayout(freq_layout)
        control_layout.addLayout(button_layout)
        control_group.setLayout(control_layout)
        
        main_layout.addWidget(control_group)
        self.setLayout(main_layout)

class ElectronicWarfarePage(QWidget):
    def __init__(self, parent=None):
        super(ElectronicWarfarePage, self).__init__(parent)
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
                padding: 5px;
            }
        """)

        # Sinyal Analiz Paneli
        analysis_group = QGroupBox("Sinyal Analizi")
        analysis_layout = QVBoxLayout()
        
        # Spektrum Görüntüleme
        self.spectrum_widget = pg.PlotWidget()
        self.spectrum_widget.setBackground('#2c2c2c')
        self.spectrum_widget.setLabel('left', 'Güç (dBm)', color='#ffffff')
        self.spectrum_widget.setLabel('bottom', 'Frekans (MHz)', color='#ffffff')
        self.spectrum_widget.showGrid(x=True, y=True, alpha=0.3)
        
        analysis_layout.addWidget(self.spectrum_widget)
        analysis_group.setLayout(analysis_layout)
        
        # Tespit Edilen Sinyaller Paneli
        signals_group = QGroupBox("Tespit Edilen Sinyaller")
        signals_layout = QVBoxLayout()
        
        self.signals_table = QTableWidget()
        self.signals_table.setColumnCount(4)
        self.signals_table.setHorizontalHeaderLabels(['Frekans (MHz)', 'Güç (dBm)', 'Bant Genişliği', 'Tehdit Seviyesi'])
        self.signals_table.setStyleSheet("""
            QTableWidget {
                background-color: #2c2c2c;
                border: 2px solid #c0392b;
                border-radius: 5px;
                gridline-color: #e74c3c;
            }
            QHeaderView::section {
                background-color: #c0392b;
                color: white;
                padding: 5px;
                border: 1px solid #e74c3c;
            }
        """)
        
        signals_layout.addWidget(self.signals_table)
        signals_group.setLayout(signals_layout)
        
        # Kontrol Paneli
        control_group = QGroupBox("Karıştırma Kontrolleri")
        control_layout = QVBoxLayout()
        
        # Frekans Seçimi
        freq_layout = QHBoxLayout()
        freq_label = QLabel("Hedef Frekans (MHz):")
        self.freq_input = QSpinBox()
        self.freq_input.setRange(100, 6000)
        self.freq_input.setValue(1000)
        self.freq_input.setStyleSheet("""
            QSpinBox {
                background-color: #2c2c2c;
                border: 2px solid #c0392b;
                border-radius: 5px;
                padding: 5px;
                min-width: 100px;
            }
        """)
        freq_layout.addWidget(freq_label)
        freq_layout.addWidget(self.freq_input)
        
        # Güç Ayarı
        power_layout = QHBoxLayout()
        power_label = QLabel("Karıştırma Gücü (W):")
        self.power_slider = QSlider(Qt.Horizontal)
        self.power_slider.setRange(0, 100)
        self.power_slider.setStyleSheet("""
            QSlider::handle:horizontal {
                background: #e74c3c;
                border: 2px solid #c0392b;
                width: 18px;
                margin: -2px 0;
                border-radius: 9px;
            }
            QSlider::groove:horizontal {
                border: 1px solid #c0392b;
                height: 8px;
                background: #2c2c2c;
                margin: 2px 0;
                border-radius: 4px;
            }
        """)
        power_layout.addWidget(power_label)
        power_layout.addWidget(self.power_slider)
        
        # Butonlar
        button_layout = QHBoxLayout()
        self.start_jamming = QPushButton("Karıştırmayı Başlat")
        self.stop_jamming = QPushButton("Karıştırmayı Durdur")
        
        for button in [self.start_jamming, self.stop_jamming]:
            button.setStyleSheet("""
                QPushButton {
                    background-color: #e74c3c;
                    color: white;
                    border: none;
                    padding: 10px;
                    border-radius: 5px;
                    font-weight: bold;
                    min-width: 150px;
                }
                QPushButton:hover {
                    background-color: #c0392b;
                }
            """)
            button_layout.addWidget(button)
        
        control_layout.addLayout(freq_layout)
        control_layout.addLayout(power_layout)
        control_layout.addLayout(button_layout)
        control_group.setLayout(control_layout)
        
        # Ana layout'a panelleri ekle
        main_layout.addWidget(analysis_group)
        main_layout.addWidget(signals_group)
        main_layout.addWidget(control_group)
        
        self.setLayout(main_layout) 