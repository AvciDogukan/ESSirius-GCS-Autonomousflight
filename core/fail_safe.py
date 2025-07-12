import time
import threading
import logging
from dronekit import VehicleMode
# core.lock import edilmeli - eğer yoksa aşağıdaki satırı kullanın
try:
    from core.lock import vehicle_lock
except ImportError:
    from threading import Lock
    vehicle_lock = Lock()

# Logger yapılandırması
fs_logger = logging.getLogger("fail_safe")
fs_logger.setLevel(logging.DEBUG)

# Konsola loglama (istenirse dosyaya da eklenebilir)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('[%(asctime)s] [%(name)s] %(levelname)s: %(message)s')
console_handler.setFormatter(formatter)
fs_logger.addHandler(console_handler)


class FailSafeMonitor(threading.Thread):
    """
    Thread-safe İHA fail-safe monitörü.
    Segmentation fault problemini çözmek için:
    1. Vehicle erişimi her zaman lock altında
    2. Güvenli attribute erişimi
    3. Exception handling her adımda
    4. Clean shutdown mekanizması
    """

    def __init__(self, vehicle, battery_threshold=10.5, gps_fix_min=3, link_loss_timeout=10):
        super().__init__()
        self.vehicle = vehicle
        self.low_battery_threshold = battery_threshold
        self.min_gps_fix = gps_fix_min
        self.link_loss_timeout = link_loss_timeout
        self._running = False
        self._stop_event = threading.Event()
        self.daemon = True  # Daemon thread olarak ayarla

    def stop(self):
        """Fail-safe izlemesini güvenli şekilde durdurur."""
        fs_logger.info("Fail-safe monitörü durduruluyor...")
        self._running = False
        self._stop_event.set()

    def run(self):
        """Thread-safe fail-safe izleme."""
        self._running = True
        fs_logger.info("Fail-safe monitörü başlatılıyor...")

        while self._running and not self._stop_event.is_set():
            try:
                # Vehicle null kontrolü
                if self.vehicle is None:
                    fs_logger.error("❌ Vehicle nesnesi None! İzleme iptal.")
                    break

                # Tüm vehicle erişimlerini güvenli şekilde yap
                self._check_vehicle_status()

            except Exception as e:
                fs_logger.error(f"❌ Fail-safe izleme hatası: {e}")
                # Kritik hata durumunda kısa süre bekle ve devam et
                time.sleep(1)

            # Stop event ile birlikte timeout kullan
            if self._stop_event.wait(timeout=1.0):
                break

        fs_logger.info("Fail-safe monitörü durduruldu.")

    def _check_vehicle_status(self):
        """Vehicle durumunu thread-safe şekilde kontrol et."""
        try:
            with vehicle_lock:
                # Vehicle hala geçerli mi?
                if self.vehicle is None:
                    fs_logger.warning("Vehicle nesnesi artık None.")
                    return

                # Heartbeat kontrolü
                self._check_heartbeat()
                
                # Batarya kontrolü
                self._check_battery_safe()
                
                # GPS kontrolü
                self._check_gps_safe()

        except Exception as e:
            fs_logger.error(f"Vehicle durum kontrolü hatası: {e}")

    def _check_heartbeat(self):
        """Güvenli heartbeat kontrolü."""
        try:
            last_heartbeat = getattr(self.vehicle, 'last_heartbeat', None)
            if last_heartbeat is None:
                fs_logger.debug("last_heartbeat verisi alınamadı.")
                return

            # Heartbeat değeri kontrolü
            if isinstance(last_heartbeat, (int, float)):
                if last_heartbeat > 1e9:  # Unix timestamp
                    hb_interval = time.time() - last_heartbeat
                else:  # Relative time
                    hb_interval = last_heartbeat

                if hb_interval > self.link_loss_timeout:
                    fs_logger.warning(f"🔗 Link kaybı tespit edildi ({hb_interval:.1f}s). RTL moduna geçiliyor.")
                    self._safe_mode_change('RTL')
                    return False  # Monitor'u durdur

        except (AttributeError, TypeError) as e:
            fs_logger.debug(f"Heartbeat kontrolü atlandı: {e}")
        except Exception as e:
            fs_logger.error(f"Heartbeat kontrolü hatası: {e}")

        return True

    def _check_battery_safe(self):
        """Güvenli batarya kontrolü."""
        try:
            battery = getattr(self.vehicle, 'battery', None)
            if battery is None:
                fs_logger.debug("Battery verisi yok.")
                return True

            voltage = getattr(battery, 'voltage', None)
            if voltage is None:
                fs_logger.debug("Battery voltage verisi yok.")
                return True

            if isinstance(voltage, (int, float)) and voltage > 0:
                if voltage < self.low_battery_threshold:
                    fs_logger.warning(f"🔋 Düşük batarya ({voltage:.2f}V)! İniş başlatılıyor.")
                    self._safe_mode_change('LAND')
                    return False  # Monitor'u durdur

        except (AttributeError, TypeError) as e:
            fs_logger.debug(f"Batarya kontrolü atlandı: {e}")
        except Exception as e:
            fs_logger.error(f"Batarya kontrolü hatası: {e}")

        return True

    def _check_gps_safe(self):
        """Güvenli GPS kontrolü."""
        try:
            gps_0 = getattr(self.vehicle, 'gps_0', None)
            if gps_0 is None:
                fs_logger.debug("GPS verisi yok.")
                return True

            fix_type = getattr(gps_0, 'fix_type', None)
            if fix_type is None:
                fs_logger.debug("GPS fix_type verisi yok.")
                return True

            if isinstance(fix_type, int) and fix_type < self.min_gps_fix:
                fs_logger.warning(f"📡 Zayıf GPS sinyali (fix={fix_type})! RTL moduna geçiliyor.")
                self._safe_mode_change('RTL')
                return False  # Monitor'u durdur

        except (AttributeError, TypeError) as e:
            fs_logger.debug(f"GPS kontrolü atlandı: {e}")
        except Exception as e:
            fs_logger.error(f"GPS kontrolü hatası: {e}")

        return True

    def _safe_mode_change(self, mode_name):
        """Güvenli mod değişikliği."""
        try:
            if self.vehicle is None:
                fs_logger.error("Vehicle None, mod değişikliği yapılamadı.")
                return

            # Mode değişikliğini dene
            current_mode = getattr(self.vehicle, 'mode', None)
            if current_mode is None:
                fs_logger.error("Vehicle mode erişilemedi.")
                return

            fs_logger.info(f"Mod değişikliği: {current_mode.name} -> {mode_name}")
            self.vehicle.mode = VehicleMode(mode_name)

            # Kısa bekleme - mod değişikliği için
            time.sleep(1)

        except Exception as e:
            fs_logger.error(f"Mod değişikliği hatası ({mode_name}): {e}")


# Ana arayüz dosyasında kullanım örneği:
def start_failsafe_safe(self):
    """Güvenli fail-safe başlatma."""
    try:
        vehicle = getattr(self.connection_manager, 'vehicle', None)
        if not vehicle:
            self.log_message("⚠ Fail-safe başlatılamadı: Vehicle yok.")
            return

        # Önceki fail-safe varsa durdur
        if hasattr(self, 'fail_safe_monitor') and self.fail_safe_monitor:
            if self.fail_safe_monitor.is_alive():
                self.fail_safe_monitor.stop()
                self.fail_safe_monitor.join(timeout=2)

        # Yeni fail-safe başlat
        self.fail_safe_monitor = FailSafeMonitor(vehicle)
        self.fail_safe_monitor.start()
        self.log_message("🛡️ Fail-safe izleyici başlatıldı.")

    except Exception as e:
        self.log_message(f"⚠ Fail-safe başlatma hatası: {e}")

def stop_failsafe_safe(self):
    """Güvenli fail-safe durdurma."""
    try:
        if hasattr(self, 'fail_safe_monitor') and self.fail_safe_monitor:
            if self.fail_safe_monitor.is_alive():
                self.fail_safe_monitor.stop()
                self.fail_safe_monitor.join(timeout=3)
                self.log_message("🛑 Fail-safe izleyici durduruldu.")
            else:
                self.log_message("🛑 Fail-safe zaten durmuş.")
        else:
            self.log_message("🛑 Fail-safe monitor bulunamadı.")
    except Exception as e:
        self.log_message(f"⚠ Fail-safe durdurma hatası: {e}")