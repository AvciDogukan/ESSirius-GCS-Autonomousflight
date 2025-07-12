#!/usr/bin/env python3
"""
Otonom uçuş için DroneKit, ArduPilot SITL ve Gazebo kullanımı.
"""
from dronekit import connect, VehicleMode, LocationGlobalRelative
import time
import math

# Bağlantı adresi (MAVProxy tarafından yayınlanan UDP portu)
connection_string = 'udp:127.0.0.1:14550'
print(f"Aracla bağlantı kuruluyor: {connection_string}")
vehicle = connect(connection_string, wait_ready=True, timeout=60)

def arm_and_takeoff(target_altitude):
    """
    Drone motorlarını aktif eder ve hedef irtifaya kalkış yapar.
    """
    print("Ön kontroller yapılıyor (is_armable kontrol ediliyor)...")
    while not vehicle.is_armable:
        print("   Uçak başlatılıyor, lütfen bekleyin...")
        time.sleep(1)

    print("Motorlar aktif ediliyor (ARM)...")
    vehicle.mode = VehicleMode("GUIDED")
    vehicle.armed = True
    while not vehicle.armed:
        print("   Motor aktivasyonu bekleniyor...")
        time.sleep(1)

    print("Kalkış yapılıyor!")
    vehicle.simple_takeoff(target_altitude)
    # Hedef irtifaya ulaşana kadar bekle
    while True:
        alt = vehicle.location.global_relative_frame.alt
        print(f"   Mevcut irtifa: {alt:.1f} m")
        if alt >= target_altitude * 0.95:
            print("Hedef irtifaya ulaşıldı")
            break
        time.sleep(1)


def get_location_metres(original_location, dNorth, dEast):
    """
    Metre cinsinden verilen kuzey/güney ve doğu/batı offset'leri
    coğrafi koordinatlara çevirir.
    """
    earth_radius = 6378137.0
    dLat = dNorth / earth_radius
    dLon = dEast / (earth_radius * math.cos(math.radians(original_location.lat)))
    newlat = original_location.lat + math.degrees(dLat)
    newlon = original_location.lon + math.degrees(dLon)
    return LocationGlobalRelative(newlat, newlon, original_location.alt)


if __name__ == "__main__":
    try:
        # Kalkış ve irtifa kontrolü
        arm_and_takeoff(10)

        print("Yer hızı (groundspeed) 5 m/s olarak ayarlanıyor")
        vehicle.groundspeed = 5

        home = vehicle.location.global_frame
        print(f"Eve dönüş konumu (home): {home}")

        # Rota için nokta listesi (metre cinsinden offset)
        waypoints = [
            get_location_metres(home, 20, 0),
            get_location_metres(home, 20, 20),
            get_location_metres(home, 0, 20),
            home
        ]

        # Her bir noktaya git ve kontrol et
        for idx, point in enumerate(waypoints):
            print(f"{idx+1}. noktaya gidiliyor: {point}")
            vehicle.simple_goto(point)
            while True:
                current = vehicle.location.global_relative_frame
                # Hedefe uzaklık tahmini (metre)
                dist = math.hypot(point.lat - current.lat, point.lon - current.lon) * 1.113195e5
                print(f"   Hedefe uzaklık: {dist:.1f} m")
                if dist < 1.0:
                    print("   Noktaya ulaşıldı")
                    break
                time.sleep(2)

        # İniş işlemi
        print("İniş moduna geçiliyor (LAND)")
        vehicle.mode = VehicleMode("LAND")
        while vehicle.armed:
            print("   İniş ve disarm bekleniyor...")
            time.sleep(1)

        print("İniş tamamlandı ve motorlar kapandı")
    except Exception as e:
        print(f"Hata oluştu: {e}")
    finally:
        vehicle.close()
        print("Bağlantı kapatıldı")

