# core/__init__.py
"""
Core package for autonomous flight logic.
Provides modules for connection management, preflight checks,
mission planning, fail-safe monitoring, autonomous flight operations,
and utility functions.
"""
from .connection import MAVSDKConnectionManager
from .preflight import PreFlightChecks
from core.navigation import ThreadSafeVTOLNavigation, ThreadSafeMissionPlanner
from .fail_safe import FailSafeMonitor
from . import utils
from .mavsdk_subprocess import MAVSDKSubprocessManager
from .mission_selector import MissionSelectorDialog
from threading import Lock
from .mission_selector import MissionSelectorDialog, create_mission_selector
from .weather_ai_module import WeatherAI, WeatherAIDialog, create_weather_ai_dialog

# 🛡️ YENİ EKLEME: Real Preflight Check sistemi
try:
    from .real_preflight_check import RealPreflightCheckDialog
    REAL_PREFLIGHT_AVAILABLE = True
    print("✅ Real Preflight Check modülü yüklendi")
except ImportError as e:
    print(f"⚠️ Real Preflight Check import hatası: {e}")
    REAL_PREFLIGHT_AVAILABLE = False
    
    # Fallback sınıflar
    class RealPreflightCheckDialog:
        def __init__(self, *args, **kwargs):
            pass
    
    class RealPreflightChecks:
        def __init__(self, *args, **kwargs):
            pass
    
    def add_preflight_button_to_main_ui(*args, **kwargs):
        print("⚠️ Real Preflight Check mevcut değil")
    
    def show_preflight_dialog(*args, **kwargs):
        print("⚠️ Real Preflight Check mevcut değil")

vehicle_lock = Lock()

# EW VTOL missions integration
try:
    import sys
    import os
    missions_path = os.path.join(os.path.dirname(__file__), '..', 'missions')
    if missions_path not in sys.path:
        sys.path.append(missions_path)
    
    from ew_vtol_missions import get_available_ew_missions, EW_VTOL_MISSIONS
    EW_MISSIONS_AVAILABLE = True
    print("✅ EW VTOL missions yüklendi")
    
except ImportError as e:
    print(f"⚠️ EW VTOL missions: {e}")
    EW_MISSIONS_AVAILABLE = False
    def get_available_ew_missions():
        return {}
    EW_VTOL_MISSIONS = {}

__all__ = [
    # Mission ve Dialog sistemleri
    'MissionSelectorDialog',
    'create_mission_selector', 
    
    # Weather AI sistemi
    'WeatherAI',
    'WeatherAIDialog', 
    'create_weather_ai_dialog',
    
    # 🛡️ YENİ: Real Preflight Check sistemi
    'RealPreflightCheckDialog',
    'RealPreflightCheck',
    'PreflightCheckItem',
    'add_preflight_button_to_main_ui',
    'show_preflight_dialog',
    'REAL_PREFLIGHT_AVAILABLE',
    
    # Core MAVSDK sistemleri
    "MAVSDKConnectionManager",
    "MAVSDKSubprocessManager", 
    "PreFlightChecks",
    
    # Navigation sistemleri
    "ThreadSafeVTOLNavigation",
    "ThreadSafeMissionPlanner",
    
    # Güvenlik sistemleri
    "FailSafeMonitor",
    
    # Utility ve EW missions
    "utils",
    "get_available_ew_missions",
    "EW_VTOL_MISSIONS", 
    "EW_MISSIONS_AVAILABLE",
    "vehicle_lock"
]
