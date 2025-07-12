#!/usr/bin/env python3
"""
Test Script: Tüm Modüllerin Entegrasyonu

Aşağıdaki kod, connection, preflight, navigation, fail_safe ve utils modüllerini
yükleyerek SITL üzerinde temel bir otonom uçuş akışını test eder.
"""
import time
from connection import ConnectionManager
from preflight import PreFlightChecks
from navigation import MissionPlanner
from fail_safe import FailSafeMonitor
from utils import get_location_metres, estimate_remaining_flight_time


def main():
    # 1) Bağlantı kurulumu
    connection_string = 'udp:127.0.0.1:14550'
    conn_mgr = ConnectionManager(connection_string)
    vehicle = conn_mgr.connect()

    # 2) PreFlight kontrolleri
    preflight = PreFlightChecks(vehicle)
    preflight.run()

    # 3) Fail-safe monitörü başlat
    fs_monitor = FailSafeMonitor(vehicle)
    fs_monitor.start()

    # 4) Navigation: Kalkış ve waypoint navigasyonu
    planner = MissionPlanner(vehicle)
    planner.arm_and_takeoff(5)  # 5 metre irtifa
    home = vehicle.location.global_frame
    waypoints = [
        get_location_metres(home, 5, 0),
        get_location_metres(home, 5, 5),
        get_location_metres(home, 0, 5),
        home
    ]
    planner.goto_waypoints(waypoints, smooth=False, timeout=30)

    # 5) İniş
    planner.land()
    time.sleep(2)

    # 6) Kalan uçuş süresi tahmini
    current_draw = vehicle.battery.current
    remaining = estimate_remaining_flight_time(current_draw, 5000)
    print(f"Kalan tahmini uçuş süresi: {remaining:.1f} dakika")

    # 7) Temizlik
    fs_monitor.stop()
    conn_mgr.disconnect()
    print("Tüm modüller başarıyla test edildi.")


if __name__ == '__main__':
    main()

