#!/usr/bin/env python3
"""
MAVSDK Connection Manager - Thread Safe & Segfault Free
PX4 VTOL için MAVSDK tabanlı bağlantı yönetimi
"""
import asyncio
import logging
import threading
import time
from typing import Optional, Callable
from mavsdk import System
import concurrent.futures
import signal

# MAVSDK exception'ları - versiyon uyumlu import
try:
    from mavsdk.core import ConnectionError as MAVSDKConnectionError
except ImportError:
    try:
        from mavsdk import ConnectionError as MAVSDKConnectionError
    except ImportError:
        MAVSDKConnectionError = Exception

try:
    from mavsdk.core import ConnectionResult
except ImportError:
    ConnectionResult = None

# Thread-safe lock
try:
    from core.lock import vehicle_lock
except ImportError:
    from threading import Lock
    vehicle_lock = Lock

# Thread-safe signal sistemi
class ThreadSafeSignal:
    """Thread-safe signal/callback sistemi"""
    def __init__(self):
        self._callbacks = []
        self._lock = threading.Lock()
    
    def connect(self, callback):
        with self._lock:
            if callback not in self._callbacks:
                self._callbacks.append(callback)
    
    def disconnect(self, callback):
        with self._lock:
            if callback in self._callbacks:
                self._callbacks.remove(callback)
    
    def emit(self, *args, **kwargs):
        with self._lock:
            callbacks = self._callbacks.copy()
        
        # Callback'leri ayrı thread'de çalıştır
        for callback in callbacks:
            try:
                threading.Thread(
                    target=callback,
                    args=args,
                    kwargs=kwargs,
                    daemon=True
                ).start()
            except Exception as e:
                logging.warning(f"Signal emit hatası: {e}")

# Logger yapılandırması
logger = logging.getLogger('mavsdk_connection')
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
formatter = logging.Formatter('[%(asctime)s] [MAVSDK-CONN] %(levelname)s: %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

class MAVSDKConnectionManager:
    """
    Thread-safe MAVSDK bağlantı yöneticisi - Segfault Free
    
    Özellikler:
    - PX4 uyumlu bağlantı yönetimi
    - Thread-safe System erişimi
    - Signal-based callbacks (Qt uyumlu)
    - Manuel bağlantı kontrolü
    - Güvenli shutdown (Segfault önleyici)
    - Health monitoring
    """
    
    def __init__(self, connection_string: str = "udp://:14540", timeout: int = 60, auto_connect: bool = False):
        self.connection_string = connection_string
        self.timeout = timeout
        self.auto_connect = auto_connect
        self.system: Optional[System] = None
        
        # Thread management
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._connected_event = threading.Event()
        self._connection_lock = threading.Lock()
        
        # Health monitoring
        self._monitoring = False
        self._monitor_task: Optional[asyncio.Task] = None
        self._last_heartbeat = 0
        self._connection_stable = False
        
        # Segfault prevention flags
        self._shutdown_in_progress = False
        self._force_stop = False
        
        # Thread-safe signal sistemi
        self.connected_signal = ThreadSafeSignal()
        self.disconnected_signal = ThreadSafeSignal()
        
        logger.info(f"MAVSDK Connection Manager oluşturuldu: {connection_string}")
        logger.info(f"Auto-connect: {'Aktif' if auto_connect else 'Pasif'}")
        
        # ✅ SADECE auto_connect=True ise otomatik başlat
        if self.auto_connect:
            logger.info("🔄 Otomatik bağlantı başlatılıyor...")
            self.start_connection()
        else:
            logger.info("⏸️ Manuel bağlantı modu - Kullanıcı bağlantıyı manuel başlatacak")
    
    def set_callbacks(self, on_connect: Optional[Callable] = None, 
                     on_disconnect: Optional[Callable] = None):
        """Thread-safe callback bağlama"""
        if on_connect:
            self.connected_signal.connect(on_connect)
        if on_disconnect:
            self.disconnected_signal.connect(on_disconnect)
    
    def start_connection(self) -> bool:
        """Bağlantıyı async thread'de başlat"""
        if self._thread and self._thread.is_alive():
            logger.warning("Bağlantı zaten aktif!")
            return True
        
        try:
            self._stop_event.clear()
            self._connected_event.clear()
            self._shutdown_in_progress = False
            self._force_stop = False
            
            # Async event loop'unu ayrı thread'de çalıştır
            self._thread = threading.Thread(
                target=self._run_async_loop, 
                daemon=True,
                name="MAVSDKConnection"
            )
            self._thread.start()
            
            # Bağlantı kurulana kadar bekle (timeout ile)
            connection_established = self._connected_event.wait(timeout=self.timeout)
            
            if connection_established:
                logger.info("✅ MAVSDK bağlantısı başarıyla kuruldu!")
                return True
            else:
                logger.error("❌ MAVSDK bağlantı timeout!")
                self.stop_connection()
                return False
                
        except Exception as e:
            logger.error(f"❌ Bağlantı başlatma hatası: {e}")
            return False
    
    def _run_async_loop(self):
        """Async event loop'unu çalıştır - Segfault-safe versiyon"""
        try:
            # Yeni event loop oluştur
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            
            # Ana async görevleri çalıştır
            self._loop.run_until_complete(self._async_main())
            
        except Exception as e:
            logger.error(f"❌ Async loop hatası: {e}")
        finally:
            # KRITIK: Loop'u güvenli şekilde kapat
            try:
                if self._loop and not self._loop.is_closed():
                    # Pending task'ları iptal et
                    pending = asyncio.all_tasks(self._loop)
                    for task in pending:
                        if not task.done():
                            task.cancel()
                    
                    # Cancelled task'ların bitmesini bekle
                    if pending:
                        self._loop.run_until_complete(
                            asyncio.gather(*pending, return_exceptions=True)
                        )
                    
                    # Loop'u kapat
                    self._loop.close()
                    
            except Exception as close_error:
                logger.warning(f"⚠ Loop kapatma hatası: {close_error}")
            finally:
                self._loop = None
                logger.info("🔌 MAVSDK async loop güvenli şekilde kapatıldı")
    
    async def _async_main(self):
        """Ana async loop - Segfault-safe versiyon"""
        try:
            # System objesi oluştur
            with self._connection_lock:
                self.system = System()
            
            # Bağlantıyı kur
            success = await self._establish_connection()
            if not success:
                return
            
            # Bağlantı başarılı sinyali gönder
            self._connected_event.set()
            self.connected_signal.emit()
            
            # Health monitoring başlat
            await self._start_health_monitoring()
            
            # Ana loop - stop signal'a kadar çalış
            while not self._stop_event.is_set() and not self._shutdown_in_progress:
                await asyncio.sleep(0.1)  # Daha kısa döngü
                
                # System kontrolü
                if not self.system or self._force_stop:
                    break
            
            logger.info("🔄 Ana async loop durduruluyor...")
            
        except Exception as e:
            logger.error(f"❌ Async main loop hatası: {e}")
        finally:
            # Güvenli async cleanup
            await self._safe_async_cleanup()
    
    async def _establish_connection(self) -> bool:
        """MAVSDK bağlantısını kur"""
        try:
            logger.info(f"🔗 MAVSDK bağlantısı kuruluyor: {self.connection_string}")
            
            with self._connection_lock:
                if not self.system:
                    return False
                
                # Bağlantıyı kur
                await self.system.connect(system_address=self.connection_string)
            
            logger.info("⏳ System bağlantısı bekleniyor...")
            
            # System hazır olana kadar bekle
            timeout_counter = 0
            while timeout_counter < self.timeout and not self._stop_event.is_set():
                try:
                    with self._connection_lock:
                        if not self.system:
                            return False
                            
                        async for state in self.system.core.connection_state():
                            if state.is_connected:
                                logger.info("✅ System bağlantısı kuruldu!")
                                self._connection_stable = True
                                return True
                            break  # Sadece bir kez kontrol et
                    
                    await asyncio.sleep(1)
                    timeout_counter += 1
                    
                    if timeout_counter % 10 == 0:  # Her 10 saniyede log
                        logger.info(f"⏳ Bağlantı bekleniyor... ({timeout_counter}/{self.timeout}s)")
                
                except Exception as check_error:
                    logger.warning(f"⚠ Bağlantı kontrolü hatası: {check_error}")
                    await asyncio.sleep(2)
                    timeout_counter += 2
            
            logger.error("❌ System bağlantı timeout!")
            return False
            
        except MAVSDKConnectionError as e:
            logger.error(f"❌ MAVSDK bağlantı hatası: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Genel bağlantı hatası: {e}")
            return False
    
    async def _start_health_monitoring(self):
        """System health monitoring başlat"""
        try:
            self._monitoring = True
            self._monitor_task = asyncio.create_task(self._health_monitor_loop())
            logger.info("📊 MAVSDK health monitoring başlatıldı")
            
        except Exception as e:
            logger.error(f"❌ Health monitoring başlatma hatası: {e}")
    
    async def _health_monitor_loop(self):
        """Basitleştirilmiş health monitoring döngüsü"""
        last_heartbeat_check = time.time()
        
        while self._monitoring and not self._stop_event.is_set() and not self._shutdown_in_progress:
            try:
                current_time = time.time()
                
                # Shutdown kontrolü
                if self._shutdown_in_progress or self._force_stop:
                    break
                
                # Basit bağlantı kontrolü
                if current_time - last_heartbeat_check > 10:  # Her 10 saniyede kontrol
                    try:
                        with self._connection_lock:
                            if self.system and not self._shutdown_in_progress:
                                self._last_heartbeat = current_time
                                
                        last_heartbeat_check = current_time
                        
                        # Heartbeat yaşı kontrolü
                        heartbeat_age = current_time - self._last_heartbeat
                        if heartbeat_age > 30:  # 30 saniye heartbeat yok
                            logger.warning(f"⚠ Heartbeat kaybı: {heartbeat_age:.1f}s")
                            
                            if heartbeat_age > 60:  # 60 saniye critical
                                logger.error("🚨 Kritik heartbeat kaybı")
                        
                    except Exception as heartbeat_error:
                        logger.warning(f"⚠ Heartbeat kontrolü hatası: {heartbeat_error}")
                
                # Daha uzun bekleme
                await asyncio.sleep(5)
                
            except asyncio.CancelledError:
                logger.info("📊 Health monitor iptal edildi")
                break
            except Exception as monitor_error:
                logger.error(f"❌ Health monitor hatası: {monitor_error}")
                await asyncio.sleep(10)
    
    def get_system(self) -> Optional[System]:
        """Thread-safe System objesi erişimi"""
        with self._connection_lock:
            return self.system if self._connection_stable and not self._shutdown_in_progress else None
    
    def is_connected(self) -> bool:
        """Bağlantı durumu kontrolü"""
        return (self._connection_stable and 
                self.system is not None and 
                not self._shutdown_in_progress)
    
    def stop_connection(self):
        """KESIN ÇÖZÜM: Segfault-safe bağlantı durdurma"""
        try:
            logger.info("🛑 KESIN ÇÖZÜM: Segfault-safe stop başlatılıyor...")
            
            # 1. Shutdown flag'ini hemen set et
            self._shutdown_in_progress = True
            self._monitoring = False
            self._connection_stable = False
            
            # 2. Stop event'ini set et
            self._stop_event.set()
            
            # 3. System'i hemen None yap (yeni erişimleri önler)
            with self._connection_lock:
                self.system = None
            
            # 4. Thread'i kısa süre bekle
            if self._thread and self._thread.is_alive():
                logger.info("🔄 Thread güvenli durdurma başlatılıyor...")
                
                # Loop'u thread içinden güvenli şekilde durdur
                if self._loop and not self._loop.is_closed():
                    try:
                        self._loop.call_soon_threadsafe(self._safe_loop_stop)
                    except RuntimeError:
                        pass  # Loop zaten kapanmış olabilir
                
                # Thread'in durması için KISA süre bekle
                self._thread.join(timeout=0.5)  # Sadece 0.5 saniye bekle
                
                if self._thread.is_alive():
                    logger.warning("⚠ Thread hala aktif - zorla devam")
                    self._force_stop = True
                    self._thread = None
                else:
                    logger.info("✅ Thread güvenli şekilde durdu")
            
            # 5. Loop referansını temizle
            self._loop = None
            
            # 6. Connected event'i temizle
            self._connected_event.clear()
            
            # 7. Disconnect signal gönder
            try:
                self.disconnected_signal.emit()
            except Exception as signal_error:
                logger.warning(f"⚠ Disconnect signal hatası: {signal_error}")
            
            logger.info("✅ KESIN ÇÖZÜM: Segfault-safe stop tamamlandı")
            
        except Exception as e:
            logger.error(f"❌ Segfault-safe stop hatası: {e}")
        finally:
            # Her durumda force cleanup
            self._monitoring = False
            self._connection_stable = False
            self._shutdown_in_progress = True
            self._loop = None
            with self._connection_lock:
                self.system = None
    
    def _safe_loop_stop(self):
        """Async loop'u thread içinden güvenli durdurma"""
        try:
            if self._loop and self._loop.is_running():
                logger.info("🔄 Async loop güvenli durduruluyor...")
                
                # Tüm pending task'ları iptal et
                for task in asyncio.all_tasks(self._loop):
                    if not task.done():
                        task.cancel()
                
                # Loop'u durdur
                self._loop.stop()
                
        except Exception as e:
            logger.warning(f"⚠ Safe loop stop hatası: {e}")
    
    async def _safe_async_cleanup(self):
        """Güvenli async temizleme - Segfault önleyici"""
        try:
            logger.info("🧹 Güvenli async cleanup başlatılıyor...")
            
            # 1. Monitoring'i durdur
            self._monitoring = False
            
            # 2. Monitor task'ını iptal et
            if self._monitor_task and not self._monitor_task.done():
                self._monitor_task.cancel()
                try:
                    await asyncio.wait_for(self._monitor_task, timeout=0.5)
                except (asyncio.CancelledError, asyncio.TimeoutError):
                    pass
            
            # 3. System'i güvenli temizle
            with self._connection_lock:
                if self.system:
                    # System'i hemen None yap
                    self.system = None
            
            # 4. Kısa bekle
            await asyncio.sleep(0.1)
            
            logger.info("✅ Güvenli async cleanup tamamlandı")
            
        except Exception as e:
            logger.error(f"❌ Güvenli async cleanup hatası: {e}")
        finally:
            # Her durumda temizle
            self._connection_stable = False
            with self._connection_lock:
                self.system = None
    
    def get_status(self) -> dict:
        """Bağlantı durumu bilgileri"""
        try:
            return {
                'connected': self.is_connected(),
                'connection_string': self.connection_string,
                'stable': self._connection_stable,
                'last_heartbeat_age': time.time() - self._last_heartbeat if self._last_heartbeat > 0 else None,
                'thread_alive': self._thread.is_alive() if self._thread else False,
                'monitoring': self._monitoring,
                'shutdown_in_progress': self._shutdown_in_progress
            }
        except Exception as e:
            logger.error(f"Status bilgisi alma hatası: {e}")
            return {'error': str(e)}
    
    # Context manager desteği
    def __enter__(self):
        self.start_connection()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop_connection()

# Kullanım örneği ve test fonksiyonları
async def test_mavsdk_connection():
    """MAVSDK bağlantı testi"""
    logger.info("🧪 MAVSDK bağlantı testi başlıyor...")
    
    def on_connect():
        logger.info("📡 Bağlantı callback - System hazır!")
    
    def on_disconnect():
        logger.info("📡 Bağlantı kesildi callback")
    
    # Connection manager oluştur
    conn = MAVSDKConnectionManager("udp://:14540")
    conn.set_callbacks(on_connect, on_disconnect)
    
    try:
        # Bağlantıyı başlat
        success = conn.start_connection()
        
        if success:
            logger.info("✅ Test bağlantısı başarılı!")
            
            # System'i kullan
            system = conn.get_system()
            if system:
                logger.info("🎯 System objesi alındı, temel kontroller...")
                
                # Basit telemetry okuma testi
                try:
                    async for health in system.telemetry.health():
                        logger.info(f"📊 System health: GPS OK: {health.is_global_position_ok}")
                        break
                except Exception as tel_error:
                    logger.warning(f"⚠ Telemetry test hatası: {tel_error}")
            
            # 30 saniye test süresi
            logger.info("⏳ 30 saniye test süresi...")
            time.sleep(30)
            
        else:
            logger.error("❌ Test bağlantısı başarısız!")
    
    finally:
        # Temizleme
        conn.stop_connection()
        logger.info("🏁 MAVSDK bağlantı testi tamamlandı")

if __name__ == "__main__":
    # Test çalıştır
    asyncio.run(test_mavsdk_connection())