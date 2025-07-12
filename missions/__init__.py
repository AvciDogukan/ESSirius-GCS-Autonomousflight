# missions/__init__.py
"""
Mission package for MAVSDK UI
Contains EW VTOL missions and standard mission templates.
"""

# EW VTOL missions import
try:
    from .ew_vtol_missions import (
        get_available_ew_missions,
        EW_VTOL_MISSIONS,
        generate_ew_vtol_mission_script,
        EWVTOLElectronicPatrolMission
    )
    
    EW_MISSIONS_AVAILABLE = True
    print("✅ EW VTOL missions loaded")
    
    # Available missions export
    AVAILABLE_MISSIONS = get_available_ew_missions()
    
except ImportError as e:
    print(f"⚠️ EW VTOL missions import error: {e}")
    EW_MISSIONS_AVAILABLE = False
    AVAILABLE_MISSIONS = {}
    
    # Fallback functions
    def get_available_ew_missions():
        return {}
    
    EW_VTOL_MISSIONS = {}
    
    def generate_ew_vtol_mission_script(mission_type, params, connection_string):
        return ""
    
    class EWVTOLElectronicPatrolMission:
        def __init__(self, connection_string="udp://:14540"):
            pass

__all__ = [
    'get_available_ew_missions',
    'EW_VTOL_MISSIONS', 
    'generate_ew_vtol_mission_script',
    'EWVTOLElectronicPatrolMission',
    'EW_MISSIONS_AVAILABLE',
    'AVAILABLE_MISSIONS'
]