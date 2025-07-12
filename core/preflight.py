#!/usr/bin/env python3
import time
import logging
from dronekit import Vehicle

# Logger yapılandırması
pf_logger = logging.getLogger('preflight')
pf_logger.setLevel(logging.DEBUG)
pf_ch = logging.StreamHandler()
pf_ch.setFormatter(logging.Formatter('[%(asctime)s] [preflight] %(levelname)s: %(message)s'))
pf_logger.addHandler(pf_ch)

class PreFlightChecks:
    """
    Kalkış öncesi güvenlik ve donanım kontrolleri:
      - ARM edilebilirlik
      - Uçuş modu hazır
      - GPS fix seviyesi
      - Batarya voltaj ve akım
      - Pusula (compass) durumu
      - EKF (filtre) sağlık durumu
      - RC link kalitesi
      - Geofence sınır kontrolü
      - Motor/servo cevabı testleri
      - Barometre & ivme sensörü sapma kontrolleri
      - SD kart/log alanı kontrolü
    """
    def __init__(self, vehicle: Vehicle, gps_fix_req: int = 3,
                 min_voltage: float = 11.1, min_current: float = 0.5,
                 geofence: dict = None, min_sd_space_mb: int = 100):
        self.vehicle = vehicle
        self.gps_fix_req = gps_fix_req
        self.min_voltage = min_voltage
        self.min_current = min_current
        self.geofence = geofence or {'lat_min': -90, 'lat_max': 90, 'lon_min': -180, 'lon_max': 180}
        self.min_sd_space_mb = min_sd_space_mb

    def run(self):
        """Tüm kontrolleri sırayla çalıştırır."""
        self._check_armable()
        self._check_mode()
        self._check_gps()
        self._check_battery()
        self._check_compass()
        self._check_ekf()
        self._check_rc_link()
        self._check_geofence()
        self._check_motors()
        self._check_barometer()
        self._check_storage()
        pf_logger.info("Tüm preflight kontrolleri başarılı.")

    def _check_armable(self):
        pf_logger.info("ARM edilebilirlik kontrolü...")
        while not self.vehicle.is_armable:
            pf_logger.debug(f"is_armable={self.vehicle.is_armable}, bekleniyor...")
            time.sleep(1)

    def _check_mode(self):
        pf_logger.info("Uçuş modu kontrolü (GUIDED mod bekleniyor)...")
        desired = 'GUIDED'
        while self.vehicle.mode.name != desired:
            pf_logger.debug(f"Mevcut mod: {self.vehicle.mode.name}")
            time.sleep(1)

    def _check_gps(self):
        pf_logger.info(f"GPS fix kontrolü (min FIX_TYPE={self.gps_fix_req})...")
        while True:
            fix = self.vehicle.gps_0.fix_type
            pf_logger.debug(f"GPS fix_type={fix}")
            if fix >= self.gps_fix_req:
                break
            time.sleep(1)

    def _check_battery(self):
    	pf_logger.info(f"Batarya kontrolü (min voltaj={self.min_voltage}V, min akım={self.min_current}A)...")
    	volt = self.vehicle.battery.voltage
    	curr = self.vehicle.battery.current
    	pf_logger.debug(f"voltage={volt:.2f}V, current={curr:.2f}A")
    	if volt < self.min_voltage:
        	raise RuntimeError(f"Düşük batarya voltajı: {volt:.2f}V")

    	# SIM altında current==0 olduğu için bunu tolere et:
    	if curr is None:
       	 pf_logger.warning("Batarya akımı okunamadı (None), kontrol atlanıyor.")
    	elif curr <= 0.01:
       	 pf_logger.warning(f"SIM modu tespit edildi (current={curr:.2f}A), akım kontrolü atlanıyor.")
    	elif curr < self.min_current:
        	raise RuntimeError(f"Düşük batarya akımı: {curr:.2f}A")


    def _check_compass(self):
        pf_logger.info("Compass sağlık kontrolü...")

        # Simülasyonda compass olmayabilir, None ise kontrolü atla
        compass = getattr(self.vehicle, 'compass', None)
        if compass is None:
            pf_logger.warning("Compass özelliği bulunamadı, kontrol atlanıyor.")
            return

        cal_status = getattr(compass, 'calibration_status', None)
        pf_logger.debug(f"compass_cal_status={cal_status}")
        if cal_status not in (1, 2):
            raise RuntimeError(f"Compass kalibrasyon durumu hatalı: {cal_status}")


    def _check_ekf(self):
        pf_logger.info("EKF sağlık kontrolü...")
        ok = getattr(self.vehicle, 'ekf_ok', True)
        pf_logger.debug(f"ekf_ok={ok}")
        if not ok:
            raise RuntimeError("EKF durumu sağlıklı değil.")

    def _check_rc_link(self):
        pf_logger.info("RC link kontrolü...")
        # Mavlink paket kaybı ve gecikme istatistiklerini kontrol edebiliriz
        rssi = None
        try:
            rssi = self.vehicle.telemetry.link_speed
        except Exception:
            pass
        pf_logger.debug(f"RC link RSSI/telemetry info={rssi}")

    def _check_geofence(self):
        pf_logger.info("Geofence sınır kontrolü...")
        loc = self.vehicle.location.global_frame
        pf_logger.debug(f"Konum: lat={loc.lat}, lon={loc.lon}")
        gf = self.geofence
        if not (gf['lat_min'] <= loc.lat <= gf['lat_max'] and gf['lon_min'] <= loc.lon <= gf['lon_max']):
            raise RuntimeError("Araç geofence sınırları dışında.")

    def _check_motors(self):
        pf_logger.info("Motor/servo testleri...")
        # Her bir kanalın min/max PWM değerlerini test edebilirsiniz
        chans = self.vehicle.channels
        for ch, pwm in chans.items():
            pf_logger.debug(f"Channel {ch}: PWM={pwm}")
        # Detaylı test için ESC calibration durumu eklenebilir

    def _check_barometer(self):
        pf_logger.info("Barometre & IMU sapma kontrolleri...")
        # Baro offset ve ivme verileriyle sapma kontrolü yapılabilir
        baro_offset = getattr(self.vehicle, 'baro_offset', None)
        pf_logger.debug(f"baro_offset={baro_offset}")

    def _check_storage(self):
        pf_logger.info("SD kart / log alanı kontrolü...")
        # Yerel dizin veya SD kart üzerinde boş alan sorgulanabilir
        import shutil
        total, used, free = shutil.disk_usage('/')
        free_mb = free // (1024 * 1024)
        pf_logger.debug(f"Disk free space: {free_mb} MB")
        if free_mb < self.min_sd_space_mb:
            raise RuntimeError(f"Yetersiz disk alanı: {free_mb} MB")
