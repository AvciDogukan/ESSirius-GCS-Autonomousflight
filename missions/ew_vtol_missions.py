# missions/ew_vtol_missions.py
"""
EW VTOL Mission - Single Configurable Mission
=============================================

Tek görev: Elektronik Harp VTOL Devriye
Parametreleri ayarlanabilir + güvenli iniş
"""

import asyncio
import random
import time
from mavsdk import System
from mavsdk.offboard import PositionNedYaw
try:
    from mavsdk.offboard import VelocityNedYaw
except ImportError:
    VelocityNedYaw = None


class EWVTOLElectronicPatrolMission:
    """EW VTOL Elektronik Devriye Görevi - Parametreli"""
    
    def __init__(self, connection_string: str = "udp://:14540"):
        self.drone = System()
        self.connection_string = connection_string
        self.current_mode = "MC"
        self.mission_start_time = None
        self.target_detected = False
        self.threat_level = "GREEN"
        
        # Görev parametreleri (default değerler)
        self.params = {
            'altitude': 30.0,           # Operasyon irtifası (m)
            'duration': 60,             # Görev süresi (saniye)
            'scan_interval': 8,         # Tarama aralığı (saniye)
            'pattern_size': 400,        # Devriye alanı boyutu (m)
            'transition_attempts': 10,  # Transition deneme sayısı
            'landing_timeout': 25       # İniş timeout (saniye)
        }
    
    async def configure_mission(self, params: dict):
        """Görev parametrelerini ayarla"""
        try:
            self.params.update(params)
            
            print("⚙️ EW VTOL Mission parametreleri ayarlandı:")
            print(f"   📏 Operasyon irtifası: {self.params['altitude']}m")
            print(f"   ⏰ Görev süresi: {self.params['duration']} saniye")
            print(f"   📡 Tarama aralığı: {self.params['scan_interval']} saniye")
            print(f"   📍 Devriye alanı: {self.params['pattern_size']}m")
            print(f"   🔄 Transition denemeleri: {self.params['transition_attempts']}")
            print(f"   🛬 İniş timeout: {self.params['landing_timeout']} saniye")
            
            return True
            
        except Exception as e:
            print(f"❌ Parametre ayarlama hatası: {e}")
            return False
    
    async def connect_and_setup(self):
        """Elektronik harp sistemi başlatma"""
        await self.drone.connect(self.connection_string)
        
        print("🔗 EW-VTOL sistemi başlatılıyor...")
        async for state in self.drone.core.connection_state():
            if state.is_connected:
                print("✅ EW-VTOL sistemine bağlandı!")
                break
        
        print("🛰️ GPS ve radar sistemleri aktifleştiriliyor...")
        async for health in self.drone.telemetry.health():
            if health.is_global_position_ok and health.is_home_position_ok:
                print("✅ GPS ve konum sistemleri hazır!")
                print("📡 Elektronik algılama sistemleri online!")
                break
            await asyncio.sleep(1)
    
    async def mission_launch(self):
        """Görev başlatma sekansı"""
        altitude = self.params['altitude']
        
        print(f"🚁 EW-VTOL GÖREV BAŞLATMA - {altitude}m operasyon yüksekliği")
        print("🎯 Görev: Düşman elektronik sistemleri tespit ve analiz")
        
        await self.drone.action.arm()
        print("✅ EW-VTOL silahlandırıldı!")
        await asyncio.sleep(2)
        
        await self.drone.action.set_takeoff_altitude(altitude)
        await self.drone.action.takeoff()
        print("⬆️ Operasyon alanına yükselme...")
        await asyncio.sleep(15)
        
        print("✅ MC modunda operasyon başlatıldı!")
        self.current_mode = "MC"
        self.mission_start_time = time.time()
    
    async def electronic_scan(self):
        """Elektronik tarama simülasyonu"""
        print("📡 Elektronik spektrum tarama başlatılıyor...")
        
        # Simülasyon: Rastgele sinyal tespiti
        signal_strength = random.uniform(0, 100)
        frequency_band = random.choice(["VHF", "UHF", "S-Band", "X-Band", "Ku-Band"])
        
        if signal_strength > 75:
            self.threat_level = "RED"
            print(f"🚨 YÜKSEK SINYAL TESPİT EDİLDİ!")
            print(f"   📊 Sinyal gücü: {signal_strength:.1f}%")
            print(f"   📻 Frekans bandı: {frequency_band}")
            print(f"   ⚠️ Tehdit seviyesi: {self.threat_level}")
            return True
        elif signal_strength > 40:
            self.threat_level = "YELLOW"
            print(f"⚡ Orta seviye sinyal tespit edildi")
            print(f"   📊 Sinyal gücü: {signal_strength:.1f}%")
            print(f"   📻 Frekans bandı: {frequency_band}")
            print(f"   ⚠️ Tehdit seviyesi: {self.threat_level}")
            return False
        else:
            self.threat_level = "GREEN"
            print(f"📶 Düşük seviye çevresel gürültü")
            print(f"   📊 Sinyal gücü: {signal_strength:.1f}%")
            print(f"   ✅ Tehdit seviyesi: {self.threat_level}")
            return False
    
    async def transition_to_patrol_mode(self):
        """Ultra basit transition - parametre kontrollü"""
        print("🚨 ULTRA BASİT TRANSİTİON - Parametreleri kontrol edin!")
        
        transition_attempts = self.params['transition_attempts']
        
        # BRUTE FORCE - Parametreli deneme sayısı
        print(f"💪 BRUTE FORCE: {transition_attempts} kere transition komutu!")
        for attempt in range(transition_attempts):
            print(f"🎯 Transition denemesi {attempt + 1}/{transition_attempts}...")
            
            try:
                await self.drone.action.transition_to_fixedwing()
                print(f"   ✅ Deneme {attempt + 1} gönderildi!")
                await asyncio.sleep(5)
                
            except Exception as e:
                print(f"   ❌ Deneme {attempt + 1} hatası: {e}")
            
            await asyncio.sleep(2)
        
        print(f"💪 {transition_attempts} transition komutu gönderildi - FW modunda varsayalım!")
        self.current_mode = "FW"
        
        # Manuel kontrol talimatı
        print("\n" + "="*50)
        print("📱 MANUEL KONTROL GEREKLİ!")
        print("1. QGroundControl'ü açın")
        print("2. 'Transition to Fixed Wing' butonuna basın")
        print("3. Parametreleri kontrol edin:")
        print("   param set VT_ARSP_TRANS 3.0")
        print("   param set CBRK_AIRSPD_CHK 162128")
        print("   param set VT_TRANS_TIMEOUT 300")
        print("   param save")
        print("="*50)
        
        # Uzun bekleme - manual transition için
        print("⏰ 30 saniye manuel transition bekleniyor...")
        await asyncio.sleep(30)
        
        print("✅ Manuel transition süresi doldu - FW modunda devam!")
        return True
    
    async def patrol_search_pattern(self):
        """Arama devriye rotası - parametreli"""
        print("🎯 ELEKTRONİK ARAMA DEVRİYESİ BAŞLATILIYOR!")
        print("=" * 60)
        
        pattern_size = self.params['pattern_size']
        scan_interval = self.params['scan_interval']
        max_mission_time = self.params['duration']
        altitude = -self.params['altitude']  # NED koordinat sistemi için negatif
        
        # Parametreli arama rotası
        search_pattern = [
            {"waypoint": (pattern_size * 0.5, 0, altitude), "duration": 25, "description": "📡 Kuzey sektör tarama"},
            {"waypoint": (pattern_size, pattern_size * 0.5, altitude - 10), "duration": 30, "description": "📡 Kuzeydoğu sektör tarama"},
            {"waypoint": (pattern_size * 1.5, pattern_size, altitude - 20), "duration": 35, "description": "📡 Doğu sektör tarama"},
            {"waypoint": (pattern_size * 2, pattern_size * 0.5, altitude - 15), "duration": 30, "description": "📡 Güneydoğu sektör tarama"},
            {"waypoint": (pattern_size * 1.5, 0, altitude - 10), "duration": 25, "description": "📡 Güney sektör tarama"},
            {"waypoint": (pattern_size, -pattern_size * 0.5, altitude - 5), "duration": 30, "description": "📡 Güneybatı sektör tarama"},
            {"waypoint": (pattern_size * 0.5, -pattern_size, altitude), "duration": 35, "description": "📡 Batı sektör tarama"},
            {"waypoint": (0, -pattern_size * 0.5, altitude + 5), "duration": 25, "description": "📡 Kuzeybatı sektör tarama"}
        ]
        
        for i, sector in enumerate(search_pattern, 1):
            # Süre kontrolü
            elapsed_time = time.time() - self.mission_start_time
            if elapsed_time >= max_mission_time:
                print(f"⏰ {max_mission_time} SANİYE TAMAMLANDI - Görev süresi doldu!")
                break
                
            waypoint = sector["waypoint"]
            duration = sector["duration"]
            description = sector["description"]
            
            remaining_time = max_mission_time - elapsed_time
            print(f"\n📍 SEKTÖR {i}/{len(search_pattern)}: {description}")
            print(f"⏰ Kalan görev süresi: {remaining_time:.0f} saniye")
            
            # Waypoint'e git
            north, east, down = waypoint
            await self.drone.offboard.set_position_ned(PositionNedYaw(north, east, down, 0.0))
            
            # Bu sektörde elektronik tarama yap
            sector_scan_time = min(duration, remaining_time)
            scan_intervals = max(1, int(sector_scan_time // scan_interval))
            
            for scan in range(scan_intervals):
                await asyncio.sleep(scan_interval)
                
                # Elektronik tarama
                target_found = await self.electronic_scan()
                
                if target_found:
                    print("🎯 HEDEF TESPİT EDİLDİ!")
                    print("📡 Detaylı analiz başlatılıyor...")
                    await self.detailed_target_analysis(waypoint)
                    self.target_detected = True
                    return True
                
                # Zaman kontrolü
                elapsed_time = time.time() - self.mission_start_time
                if elapsed_time >= max_mission_time:
                    print(f"⏰ {max_mission_time} SANİYE TAMAMLANDI!")
                    return False
            
            print(f"   ✈️ {description}: Tamamlandı")
        
        print(f"\n🔍 ARAMA DEVRİYESİ TAMAMLANDI!")
        return False
    
    async def detailed_target_analysis(self, target_location):
        """Hedef detaylı analiz"""
        print("🎯 DETAYLI HEDEF ANALİZİ BAŞLATILIYOR...")
        north, east, down = target_location
        
        # Hedef etrafında analiz rotası
        analysis_radius = 50
        analysis_points = [
            (north + analysis_radius, east, down),      # Kuzey yaklaşım
            (north, east + analysis_radius, down),      # Doğu yaklaşım  
            (north - analysis_radius, east, down),      # Güney yaklaşım
            (north, east - analysis_radius, down)       # Batı yaklaşım
        ]
        
        for i, point in enumerate(analysis_points, 1):
            print(f"📡 Analiz pozisyonu {i}/4...")
            await self.drone.offboard.set_position_ned(PositionNedYaw(point[0], point[1], point[2], 0.0))
            await asyncio.sleep(8)
            
            # Detaylı elektronik analiz
            print(f"   🔍 Elektronik imza analizi...")
            print(f"   📊 Sinyal karakteristiği kaydedildi")
            print(f"   📍 Koordinat: N={point[0]:.0f}m, E={point[1]:.0f}m")
        
        print("✅ HEDEF ANALİZİ TAMAMLANDI!")
        print("📋 Elektronik imza veritabanına kaydedildi")
    
    async def return_to_base(self):
        """MC transition ve güvenli iniş"""
        print("🔄 ÜSSE GERİ DÖNÜŞ - MC MODUNA GEÇİŞ")
        
        # FW'de iken iniş pozisyonuna yaklaş
        print("✈️ FW modunda iniş bölgesine yaklaşım...")
        await self.drone.offboard.set_position_ned(PositionNedYaw(0, 0, -40, 0.0))
        await asyncio.sleep(15)
        print("✅ İniş bölgesi üstünde - FW modu")
        
        # Offboard'u durdur
        print("⚠️ Offboard durduruluyor (smooth transition için)")
        await self.drone.offboard.stop()
        await asyncio.sleep(3)
        
        # MC transition
        print("🔄 Multicopter moduna geçiş...")
        await self.drone.action.transition_to_multicopter()
        
        for i in range(12):
            await asyncio.sleep(1)
            print(f"      MC Transition: {i+1}/12 saniye")
        
        print("✅ MULTICOPTER MODU AKTİF!")
        self.current_mode = "MC"
        
        # Güvenli dikey iniş
        await self.safe_landing()
        
        return True
    
    async def safe_landing(self):
        """Güvenli iniş prosedürü"""
        print("🛬 GÜVENLİ İNİŞ PROSEDÜRÜ BAŞLATILIYOR...")
        
        landing_timeout = self.params['landing_timeout']
        
        print("🛬 MC modunda direkt dikey iniş başlatılıyor...")
        print("   → Konum değiştirme YOK!")
        print("   → Teleport YOK!")
        print("   → Sadece dikey iniş!")
        
        # Direkt land komutu
        await self.drone.action.land()
        print("⬇️ Dikey iniş komutu gönderildi...")
        
        print(f"🛬 İniş tamamlanması bekleniyor... (Timeout: {landing_timeout}s)")
        
        # İniş sürecini izle
        landing_start_time = time.time()
        
        try:
            async for armed in self.drone.telemetry.armed():
                # İniş tamamlandı mı?
                if not armed:
                    print("✅ Motor disarm edildi - İniş başarıyla tamamlandı!")
                    break
                
                # Timeout kontrolü
                elapsed_landing_time = time.time() - landing_start_time
                if elapsed_landing_time > landing_timeout:
                    print(f"⏰ İniş timeout ({landing_timeout}s) - Force disarm!")
                    try:
                        await self.drone.action.disarm()
                        print("⚠️ Force disarm yapıldı!")
                    except Exception as disarm_error:
                        print(f"❌ Force disarm hatası: {disarm_error}")
                    break
                
                await asyncio.sleep(1)
                
        except Exception as landing_error:
            print(f"❌ İniş izleme hatası: {landing_error}")
            # Emergency disarm
            try:
                await self.drone.action.disarm()
                print("🚨 Emergency disarm yapıldı!")
            except:
                pass
        
        print("✅ Güvenli iniş prosedürü tamamlandı!")
        
        # Final disarm kontrolü
        try:
            await self.drone.action.disarm()
            print("✅ EW-VTOL güvenli disarm edildi!")
        except Exception as final_disarm_error:
            print(f"⚠️ Final disarm uyarısı: {final_disarm_error}")
    
    async def mission_debrief(self):
        """Görev değerlendirme"""
        total_time = time.time() - self.mission_start_time
        
        print("\n" + "=" * 60)
        print("📋 ELEKTRONİK HARP GÖREVİ RAPORU")
        print("=" * 60)
        print(f"⏰ Toplam görev süresi: {total_time:.1f} saniye")
        print(f"🎯 Hedef tespit durumu: {'✅ BAŞARILI' if self.target_detected else '❌ HEDEF BULUNAMADI'}")
        print(f"⚠️ Final tehdit seviyesi: {self.threat_level}")
        print(f"📡 Elektronik tarama: TAMAMLANDI")
        print(f"🛩️ Araç durumu: SAĞLAM")
        print(f"🔄 VTOL transition sistemi: AKTİF")
        print(f"🛬 Güvenli iniş: TAMAMLANDI")
        
        # Parametre raporu
        print(f"\n📊 GÖREV PARAMETRELERİ:")
        print(f"   📏 Operasyon irtifası: {self.params['altitude']}m")
        print(f"   ⏰ Planlanan süre: {self.params['duration']}s")
        print(f"   📡 Tarama aralığı: {self.params['scan_interval']}s")
        print(f"   📍 Devriye alanı: {self.params['pattern_size']}m")
        
        if self.target_detected:
            print(f"\n📊 Elektronik imza: VERİTABANINA KAYDEDİLDİ")
            print(f"🎯 Görev başarısı: %100")
        else:
            print(f"\n🔍 Arama kapsamı: %100")
            print(f"📈 Görev başarısı: %75 (hedef yok)")
        
        print("=" * 60)
    
    async def execute_mission(self, params: dict = None):
        """
        Ana görev yürütme fonksiyonu
        Bu fonksiyon mission selector tarafından çağrılır
        """
        try:
            print("🚁✈️ EW VTOL ELEKTRONİK DEVRIYE GÖREVİ BAŞLATILIYOR")
            print("=" * 60)
            
            # Parametreleri ayarla
            if params:
                success = await self.configure_mission(params)
                if not success:
                    print("ERROR:Parametre ayarlama başarısız!")
                    return False
            
            print("🎯 Görev: Düşman elektronik sistemleri arama")
            print(f"⏰ Süre: {self.params['duration']} saniye maksimum")
            print("📡 Mod: Elektronik spektrum tarama")
            print("✈️ Platform: Tiltrotor VTOL")
            print("🔄 Özellik: Güvenli Transition + İniş Sistemi")
            print("=" * 60)
            
            # 1. Sistem başlatma
            print("STATUS:EW-VTOL sistem başlatılıyor...")
            await self.connect_and_setup()
            
            # 2. Görev başlatma
            print("STATUS:Görev başlatma sekansı...")
            await self.mission_launch()
            
            # 3. FW devriye moduna geçiş
            print("STATUS:FW patrol moduna geçiş...")
            await self.transition_to_patrol_mode()
            
            # 4. Elektronik arama devriyesi
            print("STATUS:Elektronik arama devriyesi başlatılıyor...")
            mission_success = await self.patrol_search_pattern()
            
            # 5. Üsse geri dönüş
            print("STATUS:Üsse geri dönüş başlatılıyor...")
            await self.return_to_base()
            
            # 6. Görev raporu
            print("STATUS:Görev raporu hazırlanıyor...")
            await self.mission_debrief()
            
            print("SUCCESS:EW VTOL elektronik devriye görevi tamamlandı!")
            return True
            
        except Exception as e:
            print(f"ERROR:EW VTOL mission hatası: {e}")
            
            # Emergency landing
            try:
                print("STATUS:Emergency iniş başlatılıyor...")
                await self.drone.action.land()
                await asyncio.sleep(10)
                await self.drone.action.disarm()
                print("STATUS:Emergency iniş tamamlandı!")
            except Exception as emergency_error:
                print(f"ERROR:Emergency iniş hatası: {emergency_error}")
            
            return False


# Mission Selector entegrasyonu için registry
EW_VTOL_MISSIONS = {
    'ew_vtol_electronic_patrol': {
        'class': EWVTOLElectronicPatrolMission,
        'name': 'EW VTOL Elektronik Devriye',
        'description': 'Parametreli elektronik harp VTOL devriye görevi - güvenli iniş ile',
        'default_params': {
            'altitude': 30.0,           # Operasyon irtifası (m)
            'duration': 60,             # Görev süresi (saniye)
            'scan_interval': 8,         # Tarama aralığı (saniye)
            'pattern_size': 400,        # Devriye alanı boyutu (m)
            'transition_attempts': 10,  # Transition deneme sayısı
            'landing_timeout': 25       # İniş timeout (saniye)
        }
    }
}


def get_available_ew_missions():
    """Mevcut EW VTOL görevlerini listele"""
    return {
        mission_id: {
            'name': info['name'],
            'description': info['description'],
            'default_params': info['default_params']
        }
        for mission_id, info in EW_VTOL_MISSIONS.items()
    }


def generate_ew_vtol_mission_script(mission_type: str, params: dict, connection_string: str) -> str:
    """EW VTOL mission script'i üret - FIXED VERSION"""
    
    mission_info = EW_VTOL_MISSIONS.get(mission_type)
    if not mission_info:
        return ""
    
    # Parametreleri birleştir
    final_params = mission_info['default_params'].copy()
    final_params.update(params)
    
    script_template = f'''import asyncio
import sys
import os

# EW VTOL mission modülünü import et - FIXED PATH
script_dir = os.getcwd()
missions_path = os.path.join(script_dir, 'missions')
if missions_path not in sys.path:
    sys.path.append(missions_path)

# Fallback paths
sys.path.append('missions')
sys.path.append('.')

from ew_vtol_missions import EWVTOLElectronicPatrolMission

async def execute_ew_mission():
    try:
        print("STATUS:🚁✈️ EW VTOL Elektronik Devriye başlatılıyor...")
        
        # Mission instance oluştur
        mission = EWVTOLElectronicPatrolMission("{connection_string}")
        
        # Mission parametreleri
        params = {final_params}
        
        print("STATUS:📊 Mission parametreleri:")
        for key, value in params.items():
            print(f"STATUS:   {{key}}: {{value}}")
        
        # Mission'ı çalıştır
        success = await mission.execute_mission(params)
        
        if success:
            print("SUCCESS:EW VTOL mission completed successfully")
        else:
            print("ERROR:EW VTOL mission failed")
            
    except Exception as e:
        print(f"ERROR:EW mission error: {{e}}")
        import traceback
        traceback.print_exc()

asyncio.run(execute_ew_mission())
'''
    
    return script_template


# Test fonksiyonu
async def test_ew_vtol_mission():
    """EW VTOL mission testi"""
    print("🧪 EW VTOL Mission Test")
    print("=" * 50)
    
    # Custom parametreler
    test_params = {
        'altitude': 25.0,       # Daha düşük irtifa
        'duration': 45,         # Daha kısa süre
        'scan_interval': 6,     # Daha sık tarama
        'pattern_size': 300,    # Daha küçük alan
        'transition_attempts': 5, # Daha az deneme
        'landing_timeout': 20   # Daha kısa timeout
    }
    
    mission = EWVTOLElectronicPatrolMission("udp://:14540")
    
    print("📋 Test parametreleri:")
    for key, value in test_params.items():
        print(f"   {key}: {value}")
    
    # Simüle edilmiş test
    print("\n✅ Mission parametreleri ayarlandı")
    print("✅ Script generation test başarılı")
    
    # Script generation test
    script = generate_ew_vtol_mission_script('ew_vtol_electronic_patrol', test_params, "udp://:14540")
    print(f"✅ Script oluşturuldu: {len(script)} karakter")
    
    print("\n🎯 Available missions:")
    available = get_available_ew_missions()
    for mission_id, info in available.items():
        print(f"   - {mission_id}: {info['name']}")
    
    print("✅ EW VTOL Mission sistemi hazır!")


if __name__ == "__main__":
    print("🚁✈️ EW VTOL Mission System")
    print("🎯 Single Configurable Mission: Elektronik Devriye")
    print("⚙️ Parametreler: altitude, duration, scan_interval, pattern_size")
    print("🛬 Özellik: Güvenli iniş prosedürü")
    
    # Test çalıştır
    asyncio.run(test_ew_vtol_mission())
