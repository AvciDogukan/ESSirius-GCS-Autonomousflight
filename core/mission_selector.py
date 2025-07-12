# core/mission_selector.py
"""
Mission Selector Dialog - Final Version
=======================================

Güncellenmiş mission selector:
- EW VTOL missions entegrasyonu
- Standart MAVSDK missions
- Parametreli görev yapılandırması
- Modern UI tasarım
"""

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QListWidget, QTextEdit, QGroupBox,
                             QGridLayout, QSpinBox, QDoubleSpinBox, QCheckBox,
                             QTabWidget, QWidget, QScrollArea, QSlider,
                             QFrame, QComboBox, QListWidgetItem)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QPixmap, QPainter, QColor, QIcon

# EW VTOL missions import - güvenli versiyon
try:
    import sys
    import os
    
    # EW missions path ekle
    missions_path = os.path.join(os.path.dirname(__file__), '..', 'missions')
    if missions_path not in sys.path:
        sys.path.append(missions_path)
    
    from ew_vtol_missions import get_available_ew_missions, EW_VTOL_MISSIONS
    EW_MISSIONS_AVAILABLE = True
    print("✅ EW VTOL missions Mission Selector'a yüklendi")
    
except ImportError as e:
    print(f"⚠️ EW VTOL missions import hatası: {e}")
    EW_MISSIONS_AVAILABLE = False
    EW_VTOL_MISSIONS = {}


class MissionSelectorDialog(QDialog):
    """Gelişmiş Mission Selector - EW VTOL + Standart Görevler"""
    
    mission_selected = pyqtSignal(dict)  # Seçilen mission bilgilerini gönder
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_mission_data = None
        self.mission_preview_timer = QTimer()
        self.mission_preview_timer.timeout.connect(self.update_mission_preview)
        
        # Mission kategorileri
        self.standard_missions = {
            'normal_patrol': {
                'name': 'Normal Devriye',
                'description': 'Standart MAVSDK devriye görevi. Orta irtifada güvenli devriye.',
                'icon': '🚁',
                'difficulty': 'Kolay',
                'duration': '5-15 dakika',
                'default_params': {
                    'altitude': 20.0,
                    'duration': 10,
                    'speed': 5,
                    'auto_rtl': True
                }
            },
            'stealth_patrol': {
                'name': 'Alçak Sessiz Devriye',
                'description': 'Düşük irtifa gizli operasyon. Minimal gürültü ile devriye.',
                'icon': '🤫',
                'difficulty': 'Orta',
                'duration': '10-20 dakika',
                'default_params': {
                    'altitude': 12.0,
                    'duration': 15,
                    'speed': 3,
                    'auto_rtl': True
                }
            },
            'circular_patrol': {
                'name': 'Dairesel Devriye',
                'description': 'Belirlenen merkez etrafında dairesel devriye pattern.',
                'icon': '⭕',
                'difficulty': 'Kolay',
                'duration': '8-18 dakika',
                'default_params': {
                    'altitude': 25.0,
                    'duration': 12,
                    'radius': 100,
                    'auto_rtl': True
                }
            },
            'waypoint_mission': {
                'name': 'Waypoint Takip',
                'description': 'Önceden belirlenen waypoint\'leri takip eden görev.',
                'icon': '📍',
                'difficulty': 'Orta',
                'duration': '10-30 dakika',
                'default_params': {
                    'altitude': 30.0,
                    'duration': 20,
                    'speed': 8,
                    'auto_rtl': True
                }
            }
        }
        
        self.setupUI()
        self.load_missions()
    
    def setupUI(self):
        self.setWindowTitle("🎯 İHA GÖREV KOMUTA MERKEZİ")
        self.setFixedSize(1200, 900)
        self.setModal(True)
        
        main_layout = QVBoxLayout()
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # Header
        self.create_header(main_layout)
        
        # Main content area
        content_layout = QHBoxLayout()
        
        # Sol panel - Mission listesi ve kategoriler
        left_panel = self.create_left_panel()
        content_layout.addWidget(left_panel, 2)  # 2/5 oranında
        
        # Sağ panel - Parametreler ve preview
        right_panel = self.create_right_panel()
        content_layout.addWidget(right_panel, 3)  # 3/5 oranında
        
        main_layout.addLayout(content_layout)
        
        # Bottom buttons
        self.create_bottom_buttons(main_layout)
        
        self.setLayout(main_layout)
        self.apply_modern_styles()
    
    def create_header(self, layout):
        """Modern header oluştur"""
        header_frame = QFrame()
        header_frame.setFrameStyle(QFrame.NoFrame)
        header_layout = QHBoxLayout(header_frame)
        
        # Logo ve title
        title_layout = QVBoxLayout()
        
        main_title = QLabel("🎯 İHA GÖREV KOMUTA MERKEZİ")
        main_title.setAlignment(Qt.AlignLeft)
        main_title.setStyleSheet("""
            QLabel {
                font-size: 28px;
                font-weight: bold;
                color: #2c3e50;
                margin-bottom: 5px;
            }
        """)
        
        subtitle = QLabel("MAVSDK + EW VTOL Mission Control System")
        subtitle.setAlignment(Qt.AlignLeft)
        subtitle.setStyleSheet("""
            QLabel {
                font-size: 14px;
                color: #7f8c8d;
                font-style: italic;
            }
        """)
        
        title_layout.addWidget(main_title)
        title_layout.addWidget(subtitle)
        
        # Status indicators
        status_layout = QVBoxLayout()
        status_layout.setAlignment(Qt.AlignRight)
        
        # MAVSDK status
        self.mavsdk_status = QLabel("🟢 MAVSDK Ready")
        self.mavsdk_status.setStyleSheet("color: #27ae60; font-weight: bold;")
        status_layout.addWidget(self.mavsdk_status)
        
        # EW missions status
        ew_status_text = "🟢 EW VTOL Ready" if EW_MISSIONS_AVAILABLE else "🔴 EW VTOL Offline"
        ew_status_color = "#27ae60" if EW_MISSIONS_AVAILABLE else "#e74c3c"
        self.ew_status = QLabel(ew_status_text)
        self.ew_status.setStyleSheet(f"color: {ew_status_color}; font-weight: bold;")
        status_layout.addWidget(self.ew_status)
        
        header_layout.addLayout(title_layout)
        header_layout.addStretch()
        header_layout.addLayout(status_layout)
        
        layout.addWidget(header_frame)
    
    def create_left_panel(self):
        """Sol panel - Mission kategorileri ve listesi"""
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        # Category tabs
        self.category_tabs = QTabWidget()
        self.category_tabs.currentChanged.connect(self.on_category_changed)
        
        # Standart görevler tab
        standard_tab = self.create_standard_missions_tab()
        self.category_tabs.addTab(standard_tab, "🚁 Standart Görevler")
        
        # EW VTOL görevler tab
        if EW_MISSIONS_AVAILABLE:
            ew_tab = self.create_ew_missions_tab()
            self.category_tabs.addTab(ew_tab, "🚁✈️ EW VTOL")
        
        left_layout.addWidget(self.category_tabs)
        
        return left_widget
    
    def create_standard_missions_tab(self):
        """Standart görevler tab'ı"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Mission list
        self.standard_missions_list = QListWidget()
        self.standard_missions_list.setSelectionMode(QListWidget.SingleSelection)
        self.standard_missions_list.itemClicked.connect(self.on_standard_mission_selected)
        
        # Standart görevleri listele
        for mission_id, mission_info in self.standard_missions.items():
            item = QListWidgetItem()
            item.setText(f"{mission_info['icon']} {mission_info['name']}")
            item.setData(Qt.UserRole, mission_id)
            
            # Tooltip
            tooltip = f"Zorluk: {mission_info['difficulty']}\nSüre: {mission_info['duration']}\n\n{mission_info['description']}"
            item.setToolTip(tooltip)
            
            self.standard_missions_list.addItem(item)
        
        layout.addWidget(QLabel("📋 Mevcut Standart Görevler:"))
        layout.addWidget(self.standard_missions_list)
        
        return widget
    
    def create_ew_missions_tab(self):
        """EW VTOL görevler tab'ı"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # EW missions list
        self.ew_missions_list = QListWidget()
        self.ew_missions_list.setSelectionMode(QListWidget.SingleSelection)
        self.ew_missions_list.itemClicked.connect(self.on_ew_mission_selected)
        
        layout.addWidget(QLabel("🚁✈️ EW VTOL Görevleri:"))
        layout.addWidget(self.ew_missions_list)
        
        # EW özel bilgi paneli
        ew_info = QFrame()
        ew_info.setFrameStyle(QFrame.Box)
        ew_info_layout = QVBoxLayout(ew_info)
        
        ew_info_label = QLabel("⚡ EW VTOL Özellikleri:")
        ew_info_label.setStyleSheet("font-weight: bold; color: #e67e22;")
        
        ew_features = QLabel("""
• VTOL Transition (MC ↔ FW)
• Elektronik spektrum tarama
• Parametreli devriye pattern
• Güvenli iniş prosedürü
• Hedef tespit ve analiz
        """)
        ew_features.setStyleSheet("color: #34495e; font-size: 11px;")
        
        ew_info_layout.addWidget(ew_info_label)
        ew_info_layout.addWidget(ew_features)
        
        layout.addWidget(ew_info)
        
        return widget
    
    def create_right_panel(self):
        """Sağ panel - Parametreler ve preview"""
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        # Mission preview
        self.create_mission_preview(right_layout)
        
        # Parameters section
        self.create_parameters_section(right_layout)
        
        # Mission description
        self.create_description_section(right_layout)
        
        return right_widget
    
    def create_mission_preview(self, layout):
        """Mission preview paneli"""
        preview_group = QGroupBox("📊 Görev Önizleme")
        preview_layout = QVBoxLayout(preview_group)
        
        # Mission name ve icon
        self.preview_title = QLabel("Görev seçin...")
        self.preview_title.setAlignment(Qt.AlignCenter)
        self.preview_title.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: bold;
                color: #2c3e50;
                padding: 10px;
                background-color: #ecf0f1;
                border-radius: 8px;
                margin-bottom: 10px;
            }
        """)
        
        # Quick stats
        stats_layout = QGridLayout()
        
        self.stat_difficulty = QLabel("Zorluk: -")
        self.stat_duration = QLabel("Süre: -")
        self.stat_altitude = QLabel("İrtifa: -")
        self.stat_category = QLabel("Kategori: -")
        
        stats_layout.addWidget(QLabel("🎯"), 0, 0)
        stats_layout.addWidget(self.stat_difficulty, 0, 1)
        stats_layout.addWidget(QLabel("⏰"), 1, 0)
        stats_layout.addWidget(self.stat_duration, 1, 1)
        stats_layout.addWidget(QLabel("📏"), 0, 2)
        stats_layout.addWidget(self.stat_altitude, 0, 3)
        stats_layout.addWidget(QLabel("📂"), 1, 2)
        stats_layout.addWidget(self.stat_category, 1, 3)
        
        preview_layout.addWidget(self.preview_title)
        preview_layout.addLayout(stats_layout)
        
        layout.addWidget(preview_group)
    
    def create_parameters_section(self, layout):
        """Parametreler bölümü"""
        params_group = QGroupBox("⚙️ Görev Parametreleri")
        self.params_layout = QVBoxLayout(params_group)
        
        # Dynamic parameter widgets will be added here
        self.param_widgets = {}
        
        # Default empty state
        empty_label = QLabel("Parametre görmek için bir görev seçin...")
        empty_label.setAlignment(Qt.AlignCenter)
        empty_label.setStyleSheet("color: #7f8c8d; font-style: italic;")
        self.params_layout.addWidget(empty_label)
        
        layout.addWidget(params_group)
    
    def create_description_section(self, layout):
        """Açıklama bölümü"""
        desc_group = QGroupBox("📝 Görev Açıklaması")
        desc_layout = QVBoxLayout(desc_group)
        
        self.mission_description = QTextEdit()
        self.mission_description.setMaximumHeight(120)
        self.mission_description.setReadOnly(True)
        self.mission_description.setPlainText("Görev seçtiğinizde detaylı açıklama burada görünecek...")
        
        desc_layout.addWidget(self.mission_description)
        layout.addWidget(desc_group)
    
    def create_bottom_buttons(self, layout):
        """Alt butonlar"""
        button_layout = QHBoxLayout()
        
        # Sol taraf - bilgi butonları
        info_layout = QHBoxLayout()
        
        help_btn = QPushButton("❓ Yardım")
        help_btn.clicked.connect(self.show_help)
        
        settings_btn = QPushButton("⚙️ Ayarlar")
        settings_btn.clicked.connect(self.show_settings)
        
        info_layout.addWidget(help_btn)
        info_layout.addWidget(settings_btn)
        
        # Sağ taraf - ana butonlar
        main_buttons_layout = QHBoxLayout()
        
        # İptal butonu
        cancel_btn = QPushButton("❌ İptal")
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setMinimumSize(120, 45)
        
        # Önizleme butonu
        preview_btn = QPushButton("👁️ Önizleme")
        preview_btn.clicked.connect(self.preview_mission)
        preview_btn.setMinimumSize(120, 45)
        
        # Başlat butonu
        self.start_btn = QPushButton("🚀 Görevi Başlat")
        self.start_btn.clicked.connect(self.start_mission)
        self.start_btn.setEnabled(False)
        self.start_btn.setMinimumSize(150, 45)
        
        main_buttons_layout.addWidget(cancel_btn)
        main_buttons_layout.addWidget(preview_btn)
        main_buttons_layout.addWidget(self.start_btn)
        
        # Layout'a ekle
        button_layout.addLayout(info_layout)
        button_layout.addStretch()
        button_layout.addLayout(main_buttons_layout)
        
        layout.addLayout(button_layout)
    
    def load_missions(self):
        """EW missions'ları yükle"""
        if EW_MISSIONS_AVAILABLE:
            try:
                available_ew_missions = get_available_ew_missions()
                
                for mission_id, mission_info in available_ew_missions.items():
                    item = QListWidgetItem()
                    item.setText(f"✈️ {mission_info['name']}")
                    item.setData(Qt.UserRole, mission_id)
                    
                    # Tooltip
                    tooltip = f"EW VTOL Mission\n\n{mission_info['description']}"
                    item.setToolTip(tooltip)
                    
                    self.ew_missions_list.addItem(item)
                
                print(f"✅ {len(available_ew_missions)} EW mission yüklendi")
                
            except Exception as e:
                print(f"❌ EW missions yükleme hatası: {e}")
    
    def on_category_changed(self, index):
        """Kategori değiştiğinde"""
        # Seçimi temizle
        self.clear_selection()
    
    def on_standard_mission_selected(self, item):
        """Standart görev seçildi"""
        mission_id = item.data(Qt.UserRole)
        mission_info = self.standard_missions[mission_id]
        
        self.selected_mission_data = {
            'mission_type': mission_info['name'],
            'mission_id': mission_id,
            'category': 'standard',
            'icon': mission_info['icon'],
            'difficulty': mission_info['difficulty'],
            'duration_text': mission_info['duration'],
            'description': mission_info['description'],
            'default_params': mission_info['default_params'].copy()
        }
        
        # EW seçimini temizle
        self.ew_missions_list.clearSelection()
        
        # UI'yi güncelle
        self.update_mission_ui()
        self.start_btn.setEnabled(True)
        
        print(f"Standart görev seçildi: {mission_info['name']}")
    
    def on_ew_mission_selected(self, item):
        """EW VTOL görev seçildi"""
        if not EW_MISSIONS_AVAILABLE:
            return
        
        mission_id = item.data(Qt.UserRole)
        
        try:
            available_missions = get_available_ew_missions()
            mission_info = available_missions[mission_id]
            
            self.selected_mission_data = {
                'mission_type': mission_info['name'],
                'mission_id': mission_id,
                'category': 'ew_vtol',
                'icon': '🚁✈️',
                'difficulty': 'İleri',
                'duration_text': 'Parametreli',
                'description': mission_info['description'],
                'default_params': mission_info['default_params'].copy()
            }
            
            # Standart seçimi temizle
            self.standard_missions_list.clearSelection()
            
            # UI'yi güncelle
            self.update_mission_ui()
            self.start_btn.setEnabled(True)
            
            print(f"EW VTOL görev seçildi: {mission_info['name']}")
            
        except Exception as e:
            print(f"❌ EW mission seçim hatası: {e}")
    
    def update_mission_ui(self):
        """Seçilen görev için UI'yi güncelle"""
        if not self.selected_mission_data:
            return
        
        # Preview güncelle
        mission_name = self.selected_mission_data['mission_type']
        icon = self.selected_mission_data['icon']
        
        self.preview_title.setText(f"{icon} {mission_name}")
        
        # Stats güncelle
        self.stat_difficulty.setText(f"Zorluk: {self.selected_mission_data['difficulty']}")
        self.stat_duration.setText(f"Süre: {self.selected_mission_data['duration_text']}")
        self.stat_category.setText(f"Kategori: {self.selected_mission_data['category'].upper()}")
        
        # Altitude stat
        default_params = self.selected_mission_data['default_params']
        altitude = default_params.get('altitude', 'N/A')
        self.stat_altitude.setText(f"İrtifa: {altitude}m")
        
        # Description güncelle
        self.mission_description.setPlainText(self.selected_mission_data['description'])
        
        # Parametreleri güncelle
        self.update_parameters_ui()
    
    def update_parameters_ui(self):
        """Parametre UI'sını güncelle - FİXED VERSION"""
        # ÖNCE TÜM ESKİ WIDGET'LARI TEMİZLE
        self.clear_parameters_completely()
        
        if not self.selected_mission_data:
            # Boş state ekle
            empty_label = QLabel("Parametre görmek için bir görev seçin...")
            empty_label.setAlignment(Qt.AlignCenter)
            empty_label.setStyleSheet("color: #7f8c8d; font-style: italic;")
            self.params_layout.addWidget(empty_label)
            return
        
        # Yeni parametreleri ekle
        default_params = self.selected_mission_data['default_params']
        category = self.selected_mission_data['category']
        
        # Grid layout
        grid = QGridLayout()
        row = 0
        
        # Her parametre için widget oluştur
        for param_name, param_value in default_params.items():
            # Label
            label = QLabel(self.get_param_display_name(param_name))
            label.setStyleSheet("font-weight: bold; color: #2c3e50;")
            grid.addWidget(label, row, 0)
            
            # Widget
            widget = self.create_param_widget(param_name, param_value, category)
            grid.addWidget(widget, row, 1)
            
            # Unit label (eğer varsa)
            unit = self.get_param_unit(param_name)
            if unit:
                unit_label = QLabel(unit)
                unit_label.setStyleSheet("color: #7f8c8d; font-size: 11px;")
                grid.addWidget(unit_label, row, 2)
            
            self.param_widgets[param_name] = widget
            row += 1
        
        self.params_layout.addLayout(grid)
        
        # EW özel parametreler için ekstra bilgi
        if category == 'ew_vtol':
            info_frame = QFrame()
            info_frame.setFrameStyle(QFrame.Box)
            info_layout = QVBoxLayout(info_frame)
            
            ew_info = QLabel("⚡ EW VTOL Parametreleri:")
            ew_info.setStyleSheet("font-weight: bold; color: #e67e22;")
            
            ew_details = QLabel("• transition_attempts: FW geçiş deneme sayısı\n• scan_interval: Elektronik tarama aralığı\n• pattern_size: Devriye alanı boyutu\n• landing_timeout: İniş güvenlik süresi")
            ew_details.setStyleSheet("color: #34495e; font-size: 10px;")
            
            info_layout.addWidget(ew_info)
            info_layout.addWidget(ew_details)
            
            self.params_layout.addWidget(info_frame)
    
    def clear_parameters_completely(self):
        """Parametreleri tamamen temizle - YENİ FONKSİYON"""
        # Tüm widget'ları sil
        while self.params_layout.count():
            child = self.params_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
            elif child.layout():
                # Layout içindeki widget'ları da temizle
                while child.layout().count():
                    sub_child = child.layout().takeAt(0)
                    if sub_child.widget():
                        sub_child.widget().deleteLater()
                child.layout().deleteLater()
        
        # Widget dictionary'yi temizle
        self.param_widgets.clear()
    
    def create_param_widget(self, param_name, param_value, category):
        """Parametre widget'ı oluştur"""
        if isinstance(param_value, bool):
            # CheckBox for boolean
            widget = QCheckBox()
            widget.setChecked(param_value)
            return widget
        
        elif isinstance(param_value, int):
            # SpinBox for integer
            widget = QSpinBox()
            
            # Parametre özel range'leri
            if param_name == 'altitude':
                widget.setRange(5, 100)
                widget.setSuffix(' m')
            elif param_name == 'duration':
                widget.setRange(1, 120)
                widget.setSuffix(' dk' if category == 'standard' else ' s')
            elif param_name == 'speed':
                widget.setRange(1, 20)
                widget.setSuffix(' m/s')
            elif param_name == 'radius':
                widget.setRange(50, 1000)
                widget.setSuffix(' m')
            elif param_name == 'scan_interval':
                widget.setRange(3, 30)
                widget.setSuffix(' s')
            elif param_name == 'pattern_size':
                widget.setRange(100, 2000)
                widget.setSuffix(' m')
            elif param_name == 'transition_attempts':
                widget.setRange(3, 20)
            elif param_name == 'landing_timeout':
                widget.setRange(10, 60)
                widget.setSuffix(' s')
            else:
                widget.setRange(1, 1000)
            
            widget.setValue(param_value)
            return widget
        
        elif isinstance(param_value, float):
            # DoubleSpinBox for float
            widget = QDoubleSpinBox()
            
            if param_name == 'altitude':
                widget.setRange(3.0, 100.0)
                widget.setDecimals(1)
                widget.setSuffix(' m')
            else:
                widget.setRange(0.1, 1000.0)
                widget.setDecimals(1)
            
            widget.setValue(param_value)
            return widget
        
        else:
            # LineEdit for others
            from PyQt5.QtWidgets import QLineEdit
            widget = QLineEdit()
            widget.setText(str(param_value))
            return widget
    
    def get_param_display_name(self, param_name):
        """Parametre görüntü adı"""
        display_names = {
            'altitude': '📏 İrtifa',
            'duration': '⏰ Süre',
            'speed': '🚀 Hız',
            'radius': '⭕ Yarıçap',
            'auto_rtl': '🏠 Otomatik RTL',
            'scan_interval': '📡 Tarama Aralığı',
            'pattern_size': '📍 Devriye Alanı',
            'transition_attempts': '🔄 Transition Denemeleri',
            'landing_timeout': '🛬 İniş Timeout'
        }
        return display_names.get(param_name, param_name.title())
    
    def get_param_unit(self, param_name):
        """Parametre birimi"""
        units = {
            'altitude': 'm',
            'speed': 'm/s',
            'radius': 'm',
            'scan_interval': 'saniye',
            'pattern_size': 'metre',
            'landing_timeout': 'saniye'
        }
        return units.get(param_name, '')
    
    def get_current_params(self):
        """Mevcut parametre değerlerini al"""
        if not self.selected_mission_data:
            return {}
        
        params = {}
        
        for param_name, widget in self.param_widgets.items():
            if hasattr(widget, 'isChecked'):  # QCheckBox
                params[param_name] = widget.isChecked()
            elif hasattr(widget, 'value'):  # QSpinBox, QDoubleSpinBox
                params[param_name] = widget.value()
            elif hasattr(widget, 'text'):  # QLineEdit
                params[param_name] = widget.text()
        
        return params
    
    def clear_selection(self):
        """Seçimi temizle"""
        self.selected_mission_data = None
        self.start_btn.setEnabled(False)
        
        # Lists temizle
        self.standard_missions_list.clearSelection()
        if hasattr(self, 'ew_missions_list'):
            self.ew_missions_list.clearSelection()
        
        # Preview temizle
        self.preview_title.setText("Görev seçin...")
        self.stat_difficulty.setText("Zorluk: -")
        self.stat_duration.setText("Süre: -")
        self.stat_altitude.setText("İrtifa: -")
        self.stat_category.setText("Kategori: -")
        
        self.mission_description.setPlainText("Görev seçtiğinizde detaylı açıklama burada görünecek...")
    
    def update_mission_preview(self):
        """Mission preview güncelleme (timer callback)"""
        # Gelecekte animasyon vs eklenebilir
        pass
    
    def preview_mission(self):
        """Görev önizleme"""
        if not self.selected_mission_data:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Uyarı", "Önce bir görev seçin!")
            return
        
        # Önizleme dialog'u açılabilir
        params = self.get_current_params()
        
        from PyQt5.QtWidgets import QMessageBox
        
        preview_text = f"""
🎯 GÖREV ÖNİZLEME

📋 Görev: {self.selected_mission_data['mission_type']}
📂 Kategori: {self.selected_mission_data['category'].upper()}
🎯 Zorluk: {self.selected_mission_data['difficulty']}

⚙️ PARAMETRE AYARLARI:
"""
        
        for param_name, param_value in params.items():
            display_name = self.get_param_display_name(param_name)
            unit = self.get_param_unit(param_name)
            preview_text += f"   {display_name}: {param_value} {unit}\n"
        
        preview_text += f"""
📝 AÇIKLAMA:
{self.selected_mission_data['description']}

✅ Bu ayarlarla görev başlatmaya hazır!
"""
        
        QMessageBox.information(self, "Görev Önizleme", preview_text)
    
    def start_mission(self):
        """Görev başlatma"""
        if not self.selected_mission_data:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Uyarı", "Önce bir görev seçin!")
            return
        
        # Son onay
        from PyQt5.QtWidgets import QMessageBox
        
        mission_name = self.selected_mission_data['mission_type']
        category = self.selected_mission_data['category']
        
        reply = QMessageBox.question(
            self, 
            '🚀 GÖREV BAŞLATMA ONAYI',
            f'''⚠️ GÖREV BAŞLATILACAK!

🎯 Görev: {mission_name}
📂 Kategori: {category.upper()}

Bu görevi başlatmak istediğinizden emin misiniz?

⚠️ Görev başladıktan sonra manuel müdahale gerekebilir.''',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # Parametreleri topla ve mission data'yı hazırla
            current_params = self.get_current_params()
            
            # Final mission data
            final_mission_data = self.selected_mission_data.copy()
            final_mission_data.update(current_params)
            
            print(f"✅ Görev başlatma onaylandı: {mission_name}")
            print(f"📊 Parametreler: {current_params}")
            
            # Signal emit et
            self.mission_selected.emit(final_mission_data)
            self.accept()
        else:
            print("❌ Görev başlatma iptal edildi")
    
    def show_help(self):
        """Yardım dialog'u"""
        from PyQt5.QtWidgets import QMessageBox
        
        help_text = """
🎯 İHA GÖREV KOMUTA MERKEZİ - YARDIM

📋 GÖREV KATEGORİLERİ:

🚁 STANDART GÖREVLER:
• Normal Devriye: Temel MAVSDK devriye
• Alçak Sessiz Devriye: Düşük irtifa operasyonu
• Dairesel Devriye: Merkez etrafında dönel devriye
• Waypoint Takip: Belirlenen noktaları takip

🚁✈️ EW VTOL GÖREVLER:
• VTOL Transition özellikli
• Elektronik spektrum tarama
• Gelişmiş parametreler
• Güvenli iniş prosedürü

⚙️ PARAMETRE AYARLARI:
• İrtifa: Operasyon yüksekliği
• Süre: Görev süresi
• Hız: Hareket hızı
• Yarıçap: Devriye alanı boyutu

🚀 GÖREV BAŞLATMA:
1. Kategori seçin (Standart/EW VTOL)
2. Görev seçin
3. Parametreleri ayarlayın
4. Önizleme yapın
5. Görevi başlatın

⚠️ ÖNEMLİ NOTLAR:
• EW VTOL görevler daha karmaşıktır
• Parametreleri dikkatlice ayarlayın
• Güvenli operasyon alanında çalışın
• Acil durum prosedürlerini bilin
"""
        
        QMessageBox.information(self, "📖 Yardım", help_text)
    
    def show_settings(self):
        """Ayarlar dialog'u"""
        from PyQt5.QtWidgets import QMessageBox
        
        settings_text = """
⚙️ SİSTEM AYARLARI

🔧 MEVCUT DURUM:
• MAVSDK: Aktif
• EW VTOL: """ + ("Aktif" if EW_MISSIONS_AVAILABLE else "Pasif") + """
• Connection: UDP 14540

📡 BAĞLANTI AYARLARI:
• Default connection: udp://:14540
• Timeout: 30 saniye
• Max concurrent: 5 task

🎯 GÖREV AYARLARI:
• Default altitude: 20m
• Default duration: 10 dakika
• Auto RTL: Aktif

⚠️ GÜVENLİK AYARLARI:
• Minimum altitude: 5m
• Maximum altitude: 100m
• Emergency timeout: 60s

Bu ayarlar ui.py dosyasından değiştirilebilir.
"""
        
        QMessageBox.information(self, "⚙️ Ayarlar", settings_text)
    
    def apply_modern_styles(self):
        """Modern UI stilleri uygula - DARK PROFESSIONAL THEME"""
        self.setStyleSheet("""
            QDialog {
                background-color: #2c3e50;
                color: white;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            
            QTabWidget::pane {
                border: 2px solid #34495e;
                border-radius: 10px;
                background-color: #34495e;
                margin-top: 8px;
            }
            
            QTabBar::tab {
                background-color: #3498db;
                color: white;
                padding: 14px 24px;
                margin: 3px;
                border-radius: 8px;
                font-weight: bold;
                min-width: 130px;
                border: 1px solid #2980b9;
            }
            
            QTabBar::tab:selected {
                background-color: #e74c3c;
                color: white;
                border: 1px solid #c0392b;
            }
            
            QTabBar::tab:hover {
                background-color: #e67e22;
                color: white;
                border: 1px solid #d35400;
            }
            
            QGroupBox {
                font-size: 15px;
                font-weight: bold;
                border: 2px solid #34495e;
                border-radius: 12px;
                margin-top: 18px;
                padding-top: 25px;
                background-color: #2c3e50;
                color: white;
            }
            
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 20px;
                padding: 8px 20px;
                color: white;
                background-color: #2c3e50;
                border-radius: 6px;
                border: 1px solid #34495e;
                font-weight: bold;
            }
            
            QListWidget {
                background-color: #34495e;
                border: 2px solid #4a5f7a;
                border-radius: 10px;
                padding: 8px;
                selection-background-color: #e74c3c;
                alternate-background-color: #3d4f65;
                color: white;
            }
            
            QListWidget::item {
                padding: 15px;
                border-bottom: 1px solid #4a5f7a;
                border-radius: 8px;
                margin: 3px;
                color: white;
                font-weight: 500;
            }
            
            QListWidget::item:selected {
                background-color: #e74c3c;
                color: white;
                font-weight: bold;
                border: 1px solid #c0392b;
            }
            
            QListWidget::item:hover {
                background-color: #e67e22;
                color: white;
                border: 1px solid #d35400;
            }
            
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                padding: 14px 24px;
                border-radius: 10px;
                font-weight: bold;
                font-size: 14px;
            }
            
            QPushButton:hover {
                background-color: #c0392b;
                transform: translateY(-2px);
            }
            
            QPushButton:pressed {
                background-color: #a93226;
            }
            
            QPushButton:disabled {
                background-color: #566573;
                color: white;
            }
            
            QSpinBox, QDoubleSpinBox {
                background-color: #34495e;
                border: 2px solid #4a5f7a;
                border-radius: 8px;
                padding: 10px;
                font-size: 13px;
                min-width: 120px;
                color: white;
                font-weight: 500;
            }
            
            QSpinBox:focus, QDoubleSpinBox:focus {
                border: 2px solid #3498db;
                background-color: #3d4f65;
            }
            
            QTextEdit {
                background-color: #1c1c1c;
                border: 2px solid #e74c3c;
                border-radius: 10px;
                padding: 15px;
                font-size: 13px;
                line-height: 1.6;
                color: #00ff00;
                font-family: 'Consolas', 'Monaco', monospace;
            }
            
            QTextEdit:focus {
                border: 2px solid #3498db;
                background-color: #1a1a1a;
            }
            
            QCheckBox {
                spacing: 12px;
                font-weight: bold;
                color: white;
                font-size: 13px;
            }
            
            QCheckBox::indicator {
                width: 20px;
                height: 20px;
            }
            
            QCheckBox::indicator:unchecked {
                border: 2px solid #4a5f7a;
                background-color: #34495e;
                border-radius: 5px;
            }
            
            QCheckBox::indicator:checked {
                border: 2px solid #27ae60;
                background-color: #27ae60;
                border-radius: 5px;
            }
            
            QCheckBox::indicator:checked::after {
                content: "✓";
                color: white;
                font-weight: bold;
                font-size: 14px;
            }
            
            QFrame[frameShape="4"] { /* QFrame::Box */
                border: 1px solid #4a5f7a;
                border-radius: 8px;
                background-color: #34495e;
                padding: 12px;
            }
            
            QLabel {
                color: white;
            }
            
            /* Özel buton stilleri - DARK THEME */
            QPushButton[objectName="start_btn"] {
                background-color: #27ae60;
                font-size: 15px;
                padding: 18px 30px;
                border-radius: 12px;
            }
            
            QPushButton[objectName="start_btn"]:hover {
                background-color: #229954;
                transform: translateY(-2px);
            }
            
            QPushButton[objectName="cancel_btn"] {
                background-color: #e74c3c;
                font-size: 14px;
                padding: 14px 24px;
            }
            
            QPushButton[objectName="cancel_btn"]:hover {
                background-color: #c0392b;
            }
            
            QPushButton[objectName="preview_btn"] {
                background-color: #f39c12;
                color: white;
                font-size: 14px;
                padding: 14px 24px;
            }
            
            QPushButton[objectName="preview_btn"]:hover {
                background-color: #e67e22;
                color: white;
            }
            
            /* Mission Preview Özel Stilleri - DARK */
            QLabel[objectName="preview_title"] {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #2c3e50, stop:1 #34495e);
                color: white;
                font-size: 18px;
                font-weight: bold;
                padding: 15px;
                border-radius: 10px;
                margin-bottom: 10px;
                border: 1px solid #4a5f7a;
            }
            
            /* Stats Labels - DARK */
            QLabel[objectName="stat_label"] {
                background-color: #34495e;
                color: white;
                padding: 8px 12px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 12px;
                border: 1px solid #4a5f7a;
            }
            
            /* Parameter Labels - DARK */
            QLabel[objectName="param_label"] {
                color: white;
                font-weight: bold;
                font-size: 13px;
            }
            
            /* Unit Labels - DARK */
            QLabel[objectName="unit_label"] {
                color: white;
                font-size: 11px;
                font-style: italic;
            }
            
            /* EW Info Panel - DARK */
            QFrame[objectName="ew_info"] {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #8e44ad, stop:1 #9b59b6);
                border-radius: 10px;
                padding: 15px;
                border: 1px solid #7d3c98;
            }
            
            QLabel[objectName="ew_info_label"] {
                color: white;
                font-weight: bold;
                font-size: 14px;
            }
            
            QLabel[objectName="ew_features"] {
                color: white;
                font-size: 12px;
                line-height: 1.4;
            }
            
            /* Konsol Özel Stilleri */
            QTextEdit[objectName="console"] {
                background-color: #1c1c1c;
                border: 2px solid #e74c3c;
                color: #00ff00;
                font-family: 'Consolas', 'Monaco', monospace;
            }
            
            /* Gauge ve Indicator Stilleri */
            QProgressBar {
                border: 2px solid #34495e;
                border-radius: 8px;
                background-color: #2c3e50;
                text-align: center;
                color: white;
                font-weight: bold;
            }
            
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #27ae60, stop:0.5 #f39c12, stop:1 #e74c3c);
                border-radius: 6px;
            }
            
            /* Slider Stilleri */
            QSlider::groove:horizontal {
                border: 1px solid #4a5f7a;
                height: 8px;
                background: #34495e;
                border-radius: 4px;
            }
            
            QSlider::handle:horizontal {
                background: #3498db;
                border: 1px solid #2980b9;
                width: 18px;
                margin: -5px 0;
                border-radius: 9px;
            }
            
            QSlider::handle:horizontal:hover {
                background: #5dade2;
            }
            
            /* Scrollbar Stilleri */
            QScrollBar:vertical {
                background: #34495e;
                width: 15px;
                border-radius: 7px;
            }
            
            QScrollBar::handle:vertical {
                background: #e74c3c;
                border-radius: 7px;
                min-height: 20px;
            }
            
            QScrollBar::handle:vertical:hover {
                background: #c0392b;
            }
            
            /* Sol taraftaki simge/icon yazıları için FORCED WHITE */
            * {
                color: white !important;
            }
            
            /* Konsol metni hariç (yeşil kalmalı) */
            QTextEdit[objectName="console"] {
                color: #00ff00 !important;
            }
        """)
        # Object name'leri ayarla - FINAL DARK THEME
        # Object name'leri ayarla - DARK THEME ENHANCED
    
        
        
        # Buton objelerini ayarla
        self.start_btn.setObjectName("start_btn")
        
        # Header'ı özelleştir
        self.setWindowFlags(Qt.Dialog | Qt.WindowTitleHint | Qt.WindowCloseButtonHint)


# Mission Selector entegrasyonu için helper fonksiyonlar

def create_mission_selector(parent=None):
    """Mission Selector oluştur"""
    return MissionSelectorDialog(parent)


def test_mission_selector():
    """Mission Selector test fonksiyonu"""
    import sys
    from PyQt5.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    # Test dialog
    dialog = MissionSelectorDialog()
    
    def on_mission_selected(mission_data):
        print("🎯 Test - Seçilen görev:")
        print(f"   Görev: {mission_data.get('mission_type')}")
        print(f"   Kategori: {mission_data.get('category')}")
        print(f"   Parametreler: {mission_data}")
    
    dialog.mission_selected.connect(on_mission_selected)
    
    # Dialog göster
    result = dialog.exec_()
    
    if result == QDialog.Accepted:
        print("✅ Dialog başarıyla tamamlandı")
    else:
        print("❌ Dialog iptal edildi")
    
    app.quit()


if __name__ == "__main__":
    print("🎯 Mission Selector Test")
    print("=" * 40)
    print("Features:")
    print("✅ Standart MAVSDK görevler")
    print("✅ EW VTOL görevler (eğer mevcut)")
    print("✅ Parametreli konfigürasyon")
    print("✅ Modern UI tasarım")
    print("✅ Görev önizleme")
    print("✅ Yardım ve ayarlar")
    print("=" * 40)
    
    test_mission_selector()
