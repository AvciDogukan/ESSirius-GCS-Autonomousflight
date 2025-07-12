# utils.py dosyasını şu şekilde düzeltin:

#!/usr/bin/env python3
"""
Yardımcı konum ve matematik fonksiyonları.
"""
import math
from dronekit import LocationGlobalRelative


def get_location_metres(original_location, dNorth, dEast):
    """
    Verilen GPS noktasından metre cinsinden kuzey/doğu offset ile yeni LocationGlobalRelative döner.
    """
    earth_radius = 6378137.0  # metre
    dLat = dNorth / earth_radius
    dLon = dEast / (earth_radius * math.cos(math.radians(original_location.lat)))
    newlat = original_location.lat + math.degrees(dLat)
    newlon = original_location.lon + math.degrees(dLon)
    
    # Altitude'yi original_location'dan al
    alt = original_location.alt if original_location.alt is not None else 10.0

    return LocationGlobalRelative(newlat, newlon, alt)


def offset_location(original_location, dNorth, dEast, altitude=None):
    """
    Verilen GPS noktasından offset ile yeni konum döner.
    Args:
        original_location: Başlangıç konumu
        dNorth: Kuzey offset (derece)
        dEast: Doğu offset (derece) 
        altitude: Yeni altitude (metre) - None ise original kullanılır
    """
    # Derece offset'ini metre'ye çevir (yaklaşık)
    dNorth_m = dNorth * 111319.9  # 1 derece ≈ 111.32 km
    dEast_m = dEast * 111319.9 * math.cos(math.radians(original_location.lat))
    
    # get_location_metres kullan (sadece 3 parametre)
    new_location = get_location_metres(original_location, dNorth_m, dEast_m)
    
    # Altitude'yi ayarla
    if altitude is not None:
        new_location.alt = altitude
    
    return new_location


def distance_meters(a: LocationGlobalRelative, b: LocationGlobalRelative) -> float:
    """
    İki GPS noktası arasındaki mesafeyi metre cinsinden hesaplar.
    """
    dlat = (b.lat - a.lat) * 1.113195e5
    dlon = (b.lon - a.lon) * 1.113195e5
    return math.hypot(dlat, dlon)


def calculate_bearing(a: LocationGlobalRelative, b: LocationGlobalRelative) -> float:
    """
    A noktasından B noktasına doğru pusula yönü (derece) hesaplar.
    """
    lat1 = math.radians(a.lat)
    lat2 = math.radians(b.lat)
    dLon = math.radians(b.lon - a.lon)
    y = math.sin(dLon) * math.cos(lat2)
    x = math.cos(lat1)*math.sin(lat2) - math.sin(lat1)*math.cos(lat2)*math.cos(dLon)
    bearing = math.degrees(math.atan2(y, x))
    return (bearing + 360) % 360


def destination_point(start: LocationGlobalRelative, bearing_deg: float, distance_m: float) -> LocationGlobalRelative:
    """
    Başlangıç noktasından belirli bir mesafe ve yöne göre yeni GPS koordinatı hesaplar.
    """
    R = 6378137.0  # Dünya yarıçapı (m)
    lat1 = math.radians(start.lat)
    lon1 = math.radians(start.lon)
    bearing = math.radians(bearing_deg)
    d_div_R = distance_m / R
    lat2 = math.asin(math.sin(lat1) * math.cos(d_div_R) + math.cos(lat1) * math.sin(d_div_R) * math.cos(bearing))
    lon2 = lon1 + math.atan2(math.sin(bearing) * math.sin(d_div_R) * math.cos(lat1),
                               math.cos(d_div_R) - math.sin(lat1) * math.sin(lat2))
    
    # Altitude güvenli kontrol
    alt = start.alt if start.alt is not None else 10.0

    return LocationGlobalRelative(math.degrees(lat2), math.degrees(lon2), alt)


def generate_circle_waypoints(center: LocationGlobalRelative, radius: float = 10, count: int = 8, altitude: float = None) -> list:
    """
    Merkez nokta etrafında dairesel waypoint listesi oluşturur.
    Args:
        center (LocationGlobalRelative): Merkez konum
        radius (float): Yarıçap (metre)
        count (int): Nokta sayısı
        altitude (float): Altitude (metre) - None ise center'dan alınır
    Returns:
        list of LocationGlobalRelative
    """
    if altitude is None:
        altitude = center.alt if center.alt is not None else 10.0
        
    waypoints = []
    for i in range(count):
        bearing_deg = i * (360 / count)
        waypoint = destination_point(center, bearing_deg, radius)
        waypoint.alt = altitude  # Altitude'yi manuel ayarla
        waypoints.append(waypoint)
    
    return waypoints

