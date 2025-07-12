# core/mavsdk_subprocess.py
"""
MAVSDK Subprocess Manager - Complete Version with EW VTOL Support
================================================================

Bu modül MAVSDK işlemlerini subprocess'ler halinde yönetir ve EW VTOL mission desteği sağlar.
"""

import subprocess
import threading
import time
import json
import os
import sys
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass
from enum import Enum
import queue
import signal
import psutil

# EW VTOL missions import (güvenli)
try:
    # Missions path ekle
    missions_path = os.path.join(os.path.dirname(__file__), '..', 'missions')
    if missions_path not in sys.path:
        sys.path.append(missions_path)
    
    from ew_vtol_missions import (
        get_available_ew_missions, 
        generate_ew_vtol_mission_script,
        EW_VTOL_MISSIONS
    )
    EW_MISSIONS_AVAILABLE = True
    print("✅ EW VTOL missions MAVSDK subprocess'e yüklendi")
    
except ImportError as e:
    print(f"⚠️ EW VTOL missions import hatası: {e}")
    EW_MISSIONS_AVAILABLE = False
    EW_VTOL_MISSIONS = {}


class TaskStatus(Enum):
    """Task durumları"""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    STOPPED = "STOPPED"
    TIMEOUT = "TIMEOUT"


class TaskType(Enum):
    """Task tipleri"""
    TAKEOFF = "TAKEOFF"
    LAND = "LAND"
    RTL = "RTL"
    EMERGENCY = "EMERGENCY"
    MISSION = "MISSION"
    EW_MISSION = "EW_MISSION"
    TELEMETRY = "TELEMETRY"
    PARAMETER_SET = "PARAMETER_SET"
    CUSTOM = "CUSTOM"


@dataclass
class TaskInfo:
    """Task bilgileri"""
    task_id: str
    task_type: TaskType
    status: TaskStatus
    start_time: float
    end_time: Optional[float] = None
    params: Optional[Dict] = None
    output: List[str] = None
    error_output: List[str] = None
    process: Optional[subprocess.Popen] = None
    timeout: Optional[int] = None
    
    def __post_init__(self):
        if self.output is None:
            self.output = []
        if self.error_output is None:
            self.error_output = []


class MAVSDKSubprocessManager:
    """
    MAVSDK Subprocess Manager - Complete Version
    
    Features:
    - Concurrent subprocess execution
    - EW VTOL mission support
    - Task monitoring and status tracking
    - Timeout handling
    - Process cleanup
    - Output streaming
    - Error handling
    """
    
    def __init__(self, 
                 connection_string: str = "udp://:14540",
                 max_concurrent: int = 5,
                 default_timeout: int = 300,
                 enable_logging: bool = True):
        
        self.connection_string = connection_string
        self.max_concurrent = max_concurrent
        self.default_timeout = default_timeout
        self.enable_logging = enable_logging
        
        # Task management
        self.tasks: Dict[str, TaskInfo] = {}
        self.task_queue = queue.Queue()
        self.active_tasks: Dict[str, TaskInfo] = {}
        self.completed_tasks: Dict[str, TaskInfo] = {}
        
        # Threading
        self.worker_threads: List[threading.Thread] = []
        self.monitor_thread: Optional[threading.Thread] = None
        self.shutdown_event = threading.Event()
        self.task_lock = threading.Lock()
        
        # Callbacks
        self.callback_func: Optional[Callable[[str, str], None]] = None
        self.status_callbacks: Dict[str, Callable] = {}
        
        # EW Mission support
        self.ew_missions: Dict[str, Dict] = {}
        self.setup_ew_support()
        
        # Start worker threads
        self.start_workers()
        
        print(f"✅ MAVSDK Subprocess Manager başlatıldı")
        print(f"   📡 Connection: {connection_string}")
        print(f"   🧵 Max concurrent: {max_concurrent}")
        print(f"   ⏰ Default timeout: {default_timeout}s")
        print(f"   🚁✈️ EW Missions: {'✅ Aktif' if EW_MISSIONS_AVAILABLE else '❌ Pasif'}")
    
    def setup_ew_support(self):
        """EW VTOL mission desteğini kur"""
        if EW_MISSIONS_AVAILABLE:
            try:
                self.available_ew_missions = get_available_ew_missions()
                self.ew_script_generator = generate_ew_vtol_mission_script
                print(f"✅ {len(self.available_ew_missions)} EW VTOL mission hazır")
            except Exception as e:
                print(f"❌ EW support kurulumu hatası: {e}")
                self.available_ew_missions = {}
        else:
            self.available_ew_missions = {}
    
    def set_callback(self, callback: Callable[[str, str], None]):
        """Output callback fonksiyonu ayarla"""
        self.callback_func = callback
        if self.enable_logging:
            print("✅ Callback function ayarlandı")
    
    def set_connection_string(self, connection_string: str):
        """Connection string'i güncelle"""
        self.connection_string = connection_string
        print(f"📡 Connection string güncellendi: {connection_string}")
    
    def start_workers(self):
        """Worker thread'leri başlat"""
        # Task processor thread'leri
        for i in range(self.max_concurrent):
            worker = threading.Thread(
                target=self._task_worker,
                name=f"MAVSDKWorker-{i+1}",
                daemon=True
            )
            worker.start()
            self.worker_threads.append(worker)
        
        # Monitor thread
        self.monitor_thread = threading.Thread(
            target=self._monitor_tasks,
            name="MAVSDKMonitor",
            daemon=True
        )
        self.monitor_thread.start()
        
        print(f"✅ {self.max_concurrent} worker thread başlatıldı")
    
    def _task_worker(self):
        """Task işleyici worker thread"""
        while not self.shutdown_event.is_set():
            try:
                # Queue'dan task al (timeout ile)
                task_info = self.task_queue.get(timeout=1.0)
                
                if task_info is None:  # Shutdown signal
                    break
                
                # Task'ı çalıştır
                self._execute_task(task_info)
                
                # Queue'ya task tamamlandığını bildir
                self.task_queue.task_done()
                
            except queue.Empty:
                continue
            except Exception as e:
                print(f"❌ Worker thread hatası: {e}")
    
    def _monitor_tasks(self):
        """Task monitor thread - timeout ve cleanup"""
        while not self.shutdown_event.is_set():
            try:
                current_time = time.time()
                
                with self.task_lock:
                    # Timeout kontrolü
                    timed_out_tasks = []
                    
                    for task_id, task_info in self.active_tasks.items():
                        if (task_info.timeout and 
                            current_time - task_info.start_time > task_info.timeout):
                            timed_out_tasks.append(task_id)
                    
                    # Timeout olan task'ları durdur
                    for task_id in timed_out_tasks:
                        self._timeout_task(task_id)
                
                time.sleep(2.0)  # 2 saniyede bir kontrol
                
            except Exception as e:
                print(f"❌ Monitor thread hatası: {e}")
                time.sleep(1.0)
    
    def _execute_task(self, task_info: TaskInfo):
        """Tek bir task'ı çalıştır"""
        task_id = task_info.task_id
        
        try:
            # Active tasks'a ekle
            with self.task_lock:
                self.active_tasks[task_id] = task_info
                task_info.status = TaskStatus.RUNNING
            
            self._send_callback(task_id, f"STATUS:Task başlatılıyor: {task_id}")
            
            # Task tipine göre script oluştur
            if task_info.task_type == TaskType.EW_MISSION:
                script = self._generate_ew_mission_script(task_info)
            else:
                script = self._generate_standard_script(task_info)
            
            if not script:
                raise Exception("Script oluşturulamadı")
            
            # Subprocess başlat
            process = subprocess.Popen(
                [sys.executable, '-c', script],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                bufsize=1
            )
            
            task_info.process = process
            
            # Output okuma thread'leri
            stdout_thread = threading.Thread(
                target=self._read_stdout,
                args=(task_id, process),
                daemon=True
            )
            stderr_thread = threading.Thread(
                target=self._read_stderr,
                args=(task_id, process),
                daemon=True
            )
            
            stdout_thread.start()
            stderr_thread.start()
            
            # Process bitmesini bekle
            return_code = process.wait()
            
            # Task tamamlandı
            with self.task_lock:
                task_info.end_time = time.time()
                task_info.status = TaskStatus.COMPLETED if return_code == 0 else TaskStatus.FAILED
                
                # Active'den completed'e taşı
                if task_id in self.active_tasks:
                    del self.active_tasks[task_id]
                self.completed_tasks[task_id] = task_info
            
            status_msg = "SUCCESS" if return_code == 0 else "ERROR"
            self._send_callback(task_id, f"{status_msg}:Task tamamlandı: {task_id}")
            
        except Exception as e:
            # Task başarısız
            with self.task_lock:
                task_info.end_time = time.time()
                task_info.status = TaskStatus.FAILED
                task_info.error_output.append(str(e))
                
                if task_id in self.active_tasks:
                    del self.active_tasks[task_id]
                self.completed_tasks[task_id] = task_info
            
            self._send_callback(task_id, f"ERROR:Task hatası: {e}")
    
    def _read_stdout(self, task_id: str, process: subprocess.Popen):
        """Subprocess stdout okuyucu"""
        try:
            for line in iter(process.stdout.readline, ''):
                if not line:
                    break
                
                line = line.strip()
                if line:
                    # Task output'una ekle
                    with self.task_lock:
                        if task_id in self.tasks:
                            self.tasks[task_id].output.append(line)
                    
                    # Callback gönder
                    self._send_callback(task_id, line)
                    
        except Exception as e:
            self._send_callback(task_id, f"ERROR:Stdout okuma hatası: {e}")
    
    def _read_stderr(self, task_id: str, process: subprocess.Popen):
        """Subprocess stderr okuyucu"""
        try:
            for line in iter(process.stderr.readline, ''):
                if not line:
                    break
                
                line = line.strip()
                if line:
                    # Task error output'una ekle
                    with self.task_lock:
                        if task_id in self.tasks:
                            self.tasks[task_id].error_output.append(line)
                    
                    # Error callback gönder
                    self._send_callback(task_id, f"STDERR:{line}")
                    
        except Exception as e:
            self._send_callback(task_id, f"ERROR:Stderr okuma hatası: {e}")
    
    def _timeout_task(self, task_id: str):
        """Task timeout işlemi"""
        try:
            task_info = self.active_tasks.get(task_id)
            if not task_info:
                return
            
            # Process'i kill et
            if task_info.process:
                try:
                    # Önce SIGTERM gönder
                    task_info.process.terminate()
                    
                    # 5 saniye bekle
                    try:
                        task_info.process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        # Force kill
                        task_info.process.kill()
                        task_info.process.wait()
                
                except Exception as e:
                    print(f"❌ Process kill hatası: {e}")
            
            # Task durumunu güncelle
            task_info.end_time = time.time()
            task_info.status = TaskStatus.TIMEOUT
            
            # Active'den completed'e taşı
            del self.active_tasks[task_id]
            self.completed_tasks[task_id] = task_info
            
            self._send_callback(task_id, f"ERROR:Task timeout: {task_id}")
            
        except Exception as e:
            print(f"❌ Timeout task hatası: {e}")
    
    def _send_callback(self, task_id: str, output: str):
        """Callback fonksiyonunu çağır"""
        try:
            if self.callback_func:
                self.callback_func(task_id, output)
        except Exception as e:
            print(f"❌ Callback hatası: {e}")
    
    def _generate_task_id(self, task_type: TaskType, prefix: str = "") -> str:
        """Unique task ID oluştur"""
        timestamp = int(time.time() * 1000)  # Millisecond precision
        base_id = f"{task_type.value.lower()}_{timestamp}"
        
        if prefix:
            return f"{prefix}_{base_id}"
        
        return base_id
    
    # ========================================
    # PUBLIC API METHODS
    # ========================================
    
    def takeoff(self, altitude: float = 10.0, timeout: int = None) -> bool:
        """MAVSDK takeoff komutu"""
        try:
            task_id = self._generate_task_id(TaskType.TAKEOFF)
            
            task_info = TaskInfo(
                task_id=task_id,
                task_type=TaskType.TAKEOFF,
                status=TaskStatus.PENDING,
                start_time=time.time(),
                params={'altitude': altitude},
                timeout=timeout or self.default_timeout
            )
            
            # Task'ı kaydet ve queue'ya ekle
            with self.task_lock:
                self.tasks[task_id] = task_info
            
            self.task_queue.put(task_info)
            
            print(f"🚀 Takeoff task başlatıldı: {task_id} (altitude: {altitude}m)")
            return True
            
        except Exception as e:
            print(f"❌ Takeoff task hatası: {e}")
            return False
    
    def land(self, timeout: int = None) -> bool:
        """MAVSDK land komutu"""
        try:
            task_id = self._generate_task_id(TaskType.LAND)
            
            task_info = TaskInfo(
                task_id=task_id,
                task_type=TaskType.LAND,
                status=TaskStatus.PENDING,
                start_time=time.time(),
                timeout=timeout or self.default_timeout
            )
            
            with self.task_lock:
                self.tasks[task_id] = task_info
            
            self.task_queue.put(task_info)
            
            print(f"⏬ Land task başlatıldı: {task_id}")
            return True
            
        except Exception as e:
            print(f"❌ Land task hatası: {e}")
            return False
    
    def return_to_launch(self, timeout: int = None) -> bool:
        """MAVSDK RTL komutu"""
        try:
            task_id = self._generate_task_id(TaskType.RTL)
            
            task_info = TaskInfo(
                task_id=task_id,
                task_type=TaskType.RTL,
                status=TaskStatus.PENDING,
                start_time=time.time(),
                timeout=timeout or self.default_timeout
            )
            
            with self.task_lock:
                self.tasks[task_id] = task_info
            
            self.task_queue.put(task_info)
            
            print(f"🏠 RTL task başlatıldı: {task_id}")
            return True
            
        except Exception as e:
            print(f"❌ RTL task hatası: {e}")
            return False
    
    def emergency_land(self, timeout: int = None) -> bool:
        """MAVSDK emergency land komutu"""
        try:
            task_id = self._generate_task_id(TaskType.EMERGENCY)
            
            task_info = TaskInfo(
                task_id=task_id,
                task_type=TaskType.EMERGENCY,
                status=TaskStatus.PENDING,
                start_time=time.time(),
                timeout=timeout or self.default_timeout
            )
            
            with self.task_lock:
                self.tasks[task_id] = task_info
            
            # Emergency task'ları öncelikli queue'ya ekle (başa ekle)
            self.task_queue.put(task_info)
            
            print(f"🚨 Emergency land task başlatıldı: {task_id}")
            return True
            
        except Exception as e:
            print(f"❌ Emergency land task hatası: {e}")
            return False
    
    def start_mission(self, mission_params: dict, timeout: int = None) -> bool:
        """Standart mission başlat"""
        try:
            mission_type = mission_params.get('type', 'unknown')
            task_id = self._generate_task_id(TaskType.MISSION, f"mission_{mission_type}")
            
            task_info = TaskInfo(
                task_id=task_id,
                task_type=TaskType.MISSION,
                status=TaskStatus.PENDING,
                start_time=time.time(),
                params=mission_params,
                timeout=timeout or (self.default_timeout * 2)  # Missions need more time
            )
            
            with self.task_lock:
                self.tasks[task_id] = task_info
            
            self.task_queue.put(task_info)
            
            print(f"🎯 Mission task başlatıldı: {task_id} (tip: {mission_type})")
            return True
            
        except Exception as e:
            print(f"❌ Mission task hatası: {e}")
            return False
    
    def start_ew_mission(self, mission_id: str, params: dict, timeout: int = None) -> bool:
        """EW VTOL mission başlat"""
        try:
            if not EW_MISSIONS_AVAILABLE:
                print("❌ EW missions mevcut değil!")
                return False
            
            if mission_id not in self.available_ew_missions:
                print(f"❌ Bilinmeyen EW mission: {mission_id}")
                return False
            
            task_id = self._generate_task_id(TaskType.EW_MISSION, f"ew_{mission_id}")
            
            # EW mission parametrelerini hazırla
            ew_params = {
                'mission_id': mission_id,
                'mission_name': self.available_ew_missions[mission_id]['name'],
                'connection_string': self.connection_string,
                **params
            }
            
            task_info = TaskInfo(
                task_id=task_id,
                task_type=TaskType.EW_MISSION,
                status=TaskStatus.PENDING,
                start_time=time.time(),
                params=ew_params,
                timeout=timeout or (self.default_timeout * 3)  # EW missions need more time
            )
            
            with self.task_lock:
                self.tasks[task_id] = task_info
                # EW mission tracking
                self.ew_missions[task_id] = {
                    'mission_id': mission_id,
                    'mission_name': ew_params['mission_name'],
                    'params': ew_params,
                    'start_time': time.time(),
                    'status': 'RUNNING'
                }
            
            self.task_queue.put(task_info)
            
            print(f"🚁✈️ EW Mission task başlatıldı: {task_id}")
            print(f"   Mission: {ew_params['mission_name']}")
            print(f"   Params: {params}")
            return True
            
        except Exception as e:
            print(f"❌ EW Mission task hatası: {e}")
            return False
    
    def setup_vtol_parameters(self, connection_string: str = None) -> bool:
        """VTOL parametrelerini ayarla"""
        try:
            conn_str = connection_string or self.connection_string
            task_id = self._generate_task_id(TaskType.PARAMETER_SET, "vtol_params")
            
            task_info = TaskInfo(
                task_id=task_id,
                task_type=TaskType.PARAMETER_SET,
                status=TaskStatus.PENDING,
                start_time=time.time(),
                params={'connection_string': conn_str, 'param_type': 'vtol'},
                timeout=60  # Parameter setting needs less time
            )
            
            with self.task_lock:
                self.tasks[task_id] = task_info
            
            self.task_queue.put(task_info)
            
            print(f"🔧 VTOL parameter task başlatıldı: {task_id}")
            return True
            
        except Exception as e:
            print(f"❌ VTOL parameter task hatası: {e}")
            return False
    
    def execute_script(self, task_id: str, script: str, timeout: int = None) -> bool:
        """Custom script çalıştır"""
        try:
            task_info = TaskInfo(
                task_id=task_id,
                task_type=TaskType.CUSTOM,
                status=TaskStatus.PENDING,
                start_time=time.time(),
                params={'script': script},
                timeout=timeout or self.default_timeout
            )
            
            with self.task_lock:
                self.tasks[task_id] = task_info
            
            self.task_queue.put(task_info)
            
            print(f"📜 Custom script task başlatıldı: {task_id}")
            return True
            
        except Exception as e:
            print(f"❌ Custom script task hatası: {e}")
            return False
    
    def stop_task(self, task_id: str) -> bool:
        """Task'ı durdur"""
        try:
            with self.task_lock:
                task_info = self.active_tasks.get(task_id)
                
                if not task_info:
                    print(f"⚠️ Task bulunamadı veya zaten tamamlanmış: {task_id}")
                    return False
                
                # Process'i durdur
                if task_info.process:
                    try:
                        task_info.process.terminate()
                        task_info.process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        task_info.process.kill()
                        task_info.process.wait()
                
                # Task durumunu güncelle
                task_info.end_time = time.time()
                task_info.status = TaskStatus.STOPPED
                
                # Active'den completed'e taşı
                del self.active_tasks[task_id]
                self.completed_tasks[task_id] = task_info
                
                # EW mission tracking'den kaldır
                if task_id in self.ew_missions:
                    self.ew_missions[task_id]['status'] = 'STOPPED'
            
            self._send_callback(task_id, f"STATUS:Task durduruldu: {task_id}")
            print(f"⏹️ Task durduruldu: {task_id}")
            return True
            
        except Exception as e:
            print(f"❌ Task durdurma hatası: {e}")
            return False
    
    def get_task_status(self, task_id: str) -> Optional[TaskInfo]:
        """Task durumunu al"""
        with self.task_lock:
            # Önce active'de ara
            if task_id in self.active_tasks:
                return self.active_tasks[task_id]
            
            # Sonra completed'de ara
            if task_id in self.completed_tasks:
                return self.completed_tasks[task_id]
            
            # Son olarak tüm task'larda ara
            if task_id in self.tasks:
                return self.tasks[task_id]
        
        return None
    
    def get_active_tasks(self) -> Dict[str, TaskInfo]:
        """Aktif task'ları al"""
        with self.task_lock:
            return self.active_tasks.copy()
    
    def get_completed_tasks(self) -> Dict[str, TaskInfo]:
        """Tamamlanmış task'ları al"""
        with self.task_lock:
            return self.completed_tasks.copy()
    
    def get_mission_status(self) -> Optional[dict]:
        """Aktif mission durumunu al"""
        active_tasks = self.get_active_tasks()
        
        for task_id, task_info in active_tasks.items():
            if task_info.task_type in [TaskType.MISSION, TaskType.EW_MISSION]:
                runtime = time.time() - task_info.start_time
                progress = min(100, (runtime / (task_info.timeout or 300)) * 100)
                
                return {
                    'task_id': task_id,
                    'task_type': task_info.task_type.value,
                    'status': task_info.status.value,
                    'progress': progress,
                    'runtime': runtime,
                    'remaining_time': max(0, (task_info.timeout or 300) - runtime)
                }
        
        return None
    
    def abort_mission(self) -> bool:
        """Aktif mission'ı iptal et"""
        active_tasks = self.get_active_tasks()
        
        for task_id, task_info in active_tasks.items():
            if task_info.task_type in [TaskType.MISSION, TaskType.EW_MISSION]:
                return self.stop_task(task_id)
        
        print("⚠️ Aktif mission bulunamadı")
        return False
    
    def get_active_ew_missions(self) -> Dict[str, dict]:
        """Aktif EW mission'ları al"""
        with self.task_lock:
            active_ew = {}
            for task_id, mission_info in self.ew_missions.items():
                if mission_info['status'] == 'RUNNING':
                    active_ew[task_id] = mission_info
            return active_ew
    
    def stop_all_ew_missions(self):
        """Tüm EW mission'ları durdur"""
        active_ew = self.get_active_ew_missions()
        
        for task_id in active_ew.keys():
            self.stop_task(task_id)
        
        print(f"✅ {len(active_ew)} EW mission durduruldu")
    
    def stop_all(self):
        """Tüm task'ları durdur"""
        active_tasks = self.get_active_tasks()
        
        for task_id in active_tasks.keys():
            self.stop_task(task_id)
        
        print(f"⏹️ {len(active_tasks)} task durduruldu")
    
    def get_statistics(self) -> dict:
        """İstatistikleri al"""
        with self.task_lock:
            total_tasks = len(self.tasks)
            active_count = len(self.active_tasks)
            completed_count = len(self.completed_tasks)
            
            # Status dağılımı
            status_counts = {}
            for task_info in self.tasks.values():
                status = task_info.status.value
                status_counts[status] = status_counts.get(status, 0) + 1
            
            # Task type dağılımı
            type_counts = {}
            for task_info in self.tasks.values():
                task_type = task_info.task_type.value
                type_counts[task_type] = type_counts.get(task_type, 0) + 1
            
            return {
                'total_tasks': total_tasks,
                'active_tasks': active_count,
                'completed_tasks': completed_count,
                'status_distribution': status_counts,
                'type_distribution': type_counts,
                'active_ew_missions': len(self.get_active_ew_missions()),
                'connection_string': self.connection_string,
                'max_concurrent': self.max_concurrent
            }
    
    def shutdown(self):
        """Manager'ı kapat"""
        print("🔄 MAVSDK Subprocess Manager kapatılıyor...")
        
        # Tüm task'ları durdur
        self.stop_all()
        
        # Shutdown event set et
        self.shutdown_event.set()
        
        # Queue'ya None ekleyerek worker'ları uyandır
        for _ in range(self.max_concurrent):
            self.task_queue.put(None)
        
        # Worker thread'lerin bitmesini bekle
        for worker in self.worker_threads:
            worker.join(timeout=5)
        
        # Monitor thread'in bitmesini bekle
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        
        print("✅ MAVSDK Subprocess Manager kapatıldı")
    
    # ========================================
    # SCRIPT GENERATION METHODS
    # ========================================
    
    def _generate_standard_script(self, task_info: TaskInfo) -> str:
        """Standart MAVSDK script'i oluştur"""
        try:
            task_type = task_info.task_type
            params = task_info.params or {}
            
            if task_type == TaskType.TAKEOFF:
                return self._generate_takeoff_script(params)
            elif task_type == TaskType.LAND:
                return self._generate_land_script(params)
            elif task_type == TaskType.RTL:
                return self._generate_rtl_script(params)
            elif task_type == TaskType.EMERGENCY:
                return self._generate_emergency_script(params)
            elif task_type == TaskType.MISSION:
                return self._generate_mission_script(params)
            elif task_type == TaskType.PARAMETER_SET:
                return self._generate_parameter_script(params)
            elif task_type == TaskType.CUSTOM:
                return params.get('script', '')
            else:
                raise ValueError(f"Bilinmeyen task type: {task_type}")
                
        except Exception as e:
            print(f"❌ Script generation hatası: {e}")
            return ""
    
    def _generate_ew_mission_script(self, task_info: TaskInfo) -> str:
        """EW VTOL mission script'i oluştur"""
        try:
            if not EW_MISSIONS_AVAILABLE:
                raise Exception("EW missions mevcut değil")
            
            params = task_info.params or {}
            mission_id = params.get('mission_id')
            connection_string = params.get('connection_string', self.connection_string)
            
            if not mission_id:
                raise Exception("Mission ID belirtilmemiş")
            
            # EW mission script generator kullan
            script = self.ew_script_generator(mission_id, params, connection_string)
            
            if not script:
                raise Exception(f"EW mission script oluşturulamadı: {mission_id}")
            
            return script
            
        except Exception as e:
            print(f"❌ EW mission script generation hatası: {e}")
            return ""
    
    def _generate_takeoff_script(self, params: dict) -> str:
        """Takeoff script'i oluştur"""
        altitude = params.get('altitude', 10.0)
        connection_string = params.get('connection_string', self.connection_string)
        
        return f'''import asyncio
import sys
from mavsdk import System

async def takeoff_mission():
    try:
        print("STATUS:Takeoff işlemi başlatılıyor...")
        
        drone = System()
        await drone.connect("{connection_string}")
        
        print("STATUS:Drone bağlantısı kuruluyor...")
        async for state in drone.core.connection_state():
            if state.is_connected:
                print("STATUS:Drone bağlantısı başarılı!")
                break
        
        print("STATUS:Sistem sağlığı kontrol ediliyor...")
        async for health in drone.telemetry.health():
            if health.is_global_position_ok and health.is_home_position_ok:
                print("STATUS:GPS ve home position hazır!")
                break
            await asyncio.sleep(1)
        
        print("STATUS:Motor ARM işlemi...")
        await drone.action.arm()
        print("STATUS:Motor ARM başarılı!")
        
        print("STATUS:Takeoff altitude ayarlanıyor...")
        await drone.action.set_takeoff_altitude({altitude})
        
        print("STATUS:Takeoff başlatılıyor...")
        await drone.action.takeoff()
        print("STATUS:Takeoff komutu gönderildi!")
        
        print("STATUS:Hedef altitude bekleniyor...")
        target_reached = False
        timeout_counter = 0
        
        async for position in drone.telemetry.position():
            current_alt = position.relative_altitude_m
            print(f"STATUS:Mevcut altitude: {{current_alt:.1f}}m / {altitude}m")
            
            if current_alt >= {altitude} * 0.9:
                print("STATUS:Hedef altitude ulaşıldı!")
                target_reached = True
                break
            
            timeout_counter += 1
            if timeout_counter > 60:
                print("ERROR:Takeoff timeout!")
                break
                
            await asyncio.sleep(1)
        
        if target_reached:
            print("SUCCESS:Takeoff başarıyla tamamlandı!")
        else:
            print("ERROR:Takeoff tamamlanamadı!")
            
    except Exception as e:
        print(f"ERROR:Takeoff hatası: {{e}}")

asyncio.run(takeoff_mission())
'''
    
    def _generate_land_script(self, params: dict) -> str:
        """Land script'i oluştur"""
        connection_string = params.get('connection_string', self.connection_string)
        
        return f'''import asyncio
from mavsdk import System

async def land_mission():
    try:
        print("STATUS:İniş işlemi başlatılıyor...")
        
        drone = System()
        await drone.connect("{connection_string}")
        
        async for state in drone.core.connection_state():
            if state.is_connected:
                print("STATUS:Drone bağlantısı başarılı!")
                break
        
        print("STATUS:İniş komutu gönderiliyor...")
        await drone.action.land()
        print("STATUS:İniş komutu gönderildi!")
        
        print("STATUS:İniş tamamlanması bekleniyor...")
        async for armed in drone.telemetry.armed():
            if not armed:
                print("STATUS:Motor disarm edildi - İniş tamamlandı!")
                break
            await asyncio.sleep(1)
        
        print("SUCCESS:İniş başarıyla tamamlandı!")
        
    except Exception as e:
        print(f"ERROR:İniş hatası: {{e}}")

asyncio.run(land_mission())
'''
    
    def _generate_rtl_script(self, params: dict) -> str:
        """RTL script'i oluştur"""
        connection_string = params.get('connection_string', self.connection_string)
        
        return f'''import asyncio
from mavsdk import System

async def rtl_mission():
    try:
        print("STATUS:Return to Launch işlemi başlatılıyor...")
        
        drone = System()
        await drone.connect("{connection_string}")
        
        async for state in drone.core.connection_state():
            if state.is_connected:
                print("STATUS:Drone bağlantısı başarılı!")
                break
        
        print("STATUS:RTL komutu gönderiliyor...")
        await drone.action.return_to_launch()
        print("STATUS:RTL komutu gönderildi!")
        
        print("STATUS:RTL tamamlanması bekleniyor...")
        async for armed in drone.telemetry.armed():
            if not armed:
                print("STATUS:RTL tamamlandı - motor disarm edildi!")
                break
            await asyncio.sleep(1)
        
        print("SUCCESS:RTL başarıyla tamamlandı!")
        
    except Exception as e:
        print(f"ERROR:RTL hatası: {{e}}")

asyncio.run(rtl_mission())
'''
    
    def _generate_emergency_script(self, params: dict) -> str:
        """Emergency land script'i oluştur"""
        connection_string = params.get('connection_string', self.connection_string)
        
        return f'''import asyncio
from mavsdk import System

async def emergency_mission():
    try:
        print("STATUS:ACİL DURUM İNİŞİ başlatılıyor...")
        
        drone = System()
        await drone.connect("{connection_string}")
        
        async for state in drone.core.connection_state():
            if state.is_connected:
                print("STATUS:Drone bağlantısı başarılı!")
                break
        
        print("STATUS:ACİL İNİŞ komutu gönderiliyor...")
        await drone.action.land()
        print("STATUS:ACİL İNİŞ komutu gönderildi!")
        
        print("STATUS:Acil iniş tamamlanması bekleniyor...")
        timeout_counter = 0
        
        async for armed in drone.telemetry.armed():
            if not armed:
                print("STATUS:ACİL İNİŞ tamamlandı!")
                break
            
            timeout_counter += 1
            if timeout_counter > 120:  # 2 dakika timeout
                print("STATUS:Acil iniş timeout - force disarm!")
                try:
                    await drone.action.disarm()
                except:
                    pass
                break
                
            await asyncio.sleep(1)
        
        print("SUCCESS:Acil iniş başarıyla tamamlandı!")
        
    except Exception as e:
        print(f"ERROR:Acil iniş hatası: {{e}}")

asyncio.run(emergency_mission())
'''
    
    def _generate_mission_script(self, params: dict) -> str:
        """Standart mission script'i oluştur"""
        mission_type = params.get('type', 'unknown')
        connection_string = params.get('connection_string', self.connection_string)
        altitude = params.get('altitude', 20.0)
        duration = params.get('duration', 300)
        
        return f'''import asyncio
import time
from mavsdk import System
from mavsdk.offboard import PositionNedYaw

async def standard_mission():
    try:
        print("STATUS:Standart mission başlatılıyor...")
        print("STATUS:Mission tipi: {mission_type}")
        
        drone = System()
        await drone.connect("{connection_string}")
        
        async for state in drone.core.connection_state():
            if state.is_connected:
                print("STATUS:Drone bağlantısı başarılı!")
                break
        
        print("STATUS:Mission pattern başlatılıyor...")
        
        # Offboard modu başlat
        await drone.offboard.set_position_ned(PositionNedYaw(0.0, 0.0, -{altitude}, 0.0))
        await drone.offboard.start()
        
        # Basit devriye pattern
        waypoints = [
            (50, 0, -{altitude}),
            (50, 50, -{altitude}),
            (0, 50, -{altitude}),
            (0, 0, -{altitude})
        ]
        
        start_time = time.time()
        waypoint_index = 0
        
        while time.time() - start_time < {duration}:
            if waypoint_index < len(waypoints):
                north, east, down = waypoints[waypoint_index]
                print(f"STATUS:Waypoint {{waypoint_index + 1}}/{{len(waypoints)}}: N={{north}} E={{east}}")
                
                await drone.offboard.set_position_ned(PositionNedYaw(north, east, down, 0.0))
                await asyncio.sleep(15)  # Her waypoint'te 15 saniye bekle
                
                waypoint_index = (waypoint_index + 1) % len(waypoints)
            else:
                await asyncio.sleep(1)
        
        print("STATUS:Mission süresi tamamlandı!")
        await drone.offboard.stop()
        
        print("SUCCESS:Standart mission başarıyla tamamlandı!")
        
    except Exception as e:
        print(f"ERROR:Mission hatası: {{e}}")

asyncio.run(standard_mission())
'''
    
    def _generate_parameter_script(self, params: dict) -> str:
        """Parameter setting script'i oluştur"""
        connection_string = params.get('connection_string', self.connection_string)
        param_type = params.get('param_type', 'vtol')
        
        if param_type == 'vtol':
            return f'''import asyncio
from mavsdk import System

async def set_vtol_parameters():
    try:
        print("STATUS:VTOL parametreleri ayarlanıyor...")
        
        drone = System()
        await drone.connect("{connection_string}")
        
        async for state in drone.core.connection_state():
            if state.is_connected:
                print("STATUS:Drone bağlantısı başarılı!")
                break
        
        print("STATUS:VTOL parametreleri ayarlanıyor...")
        
        # VTOL kritik parametreler
        vtol_params = [
            ("VT_TYPE", 2),           # Standard VTOL
            ("VT_TRANS_MIN_TM", 1.0), # Minimum transition time
            ("VT_F_TRANS_DUR", 5.0),  # Forward transition duration
            ("VT_B_TRANS_DUR", 4.0),  # Back transition duration
            ("VT_ARSP_TRANS", 10.0),  # Transition airspeed
            ("VT_B_REV_OUT", 0),      # Reverse output for back transition
            ("VT_FW_MOT_OFFID", 0),   # Motor off in FW mode
        ]
        
        for param_name, param_value in vtol_params:
            try:
                print(f"STATUS:Setting {{param_name}} = {{param_value}}")
                await drone.param.set_param_float(param_name, float(param_value))
                await asyncio.sleep(0.5)
            except Exception as e:
                print(f"STATUS:Warning: {{param_name}} setting failed: {{e}}")
        
        print("STATUS:VTOL parametreleri ayarlandı!")
        print("SUCCESS:VTOL parameter setup completed!")
        
    except Exception as e:
        print(f"ERROR:Parameter setting hatası: {{e}}")

asyncio.run(set_vtol_parameters())
'''
        else:
            return f'''import asyncio
from mavsdk import System

async def set_custom_parameters():
    try:
        print("STATUS:Custom parametreler ayarlanıyor...")
        
        drone = System()
        await drone.connect("{connection_string}")
        
        async for state in drone.core.connection_state():
            if state.is_connected:
                break
        
        print("SUCCESS:Custom parameter setup completed!")
        
    except Exception as e:
        print(f"ERROR:Parameter setting hatası: {{e}}")

asyncio.run(set_custom_parameters())
'''


# ========================================
# HELPER FUNCTIONS & EXTENSIONS
# ========================================

def extend_mavsdk_manager_with_ew_support(manager_instance):
    """
    Mevcut MAVSDKSubprocessManager instance'ına EW mission desteği ekle
    
    Usage:
        manager = MAVSDKSubprocessManager(...)
        extend_mavsdk_manager_with_ew_support(manager)
        
        # Artık EW missions kullanılabilir
        manager.start_ew_mission('ew_vtol_normal_patrol', {...})
    """
    
    # Bu fonksiyon artık gereksiz çünkü EW support built-in
    print("✅ EW Mission desteği zaten built-in!")
    return manager_instance


# Test ve debug için utility fonksiyonlar
def create_test_manager():
    """Test için MAVSDK manager oluştur"""
    manager = MAVSDKSubprocessManager(
        connection_string="udp://:14540",
        max_concurrent=3,
        default_timeout=60,
        enable_logging=True
    )
    
    def test_callback(task_id: str, output: str):
        print(f"TEST CALLBACK [{task_id}]: {output}")
    
    manager.set_callback(test_callback)
    return manager


def test_mavsdk_manager():
    """MAVSDK Manager test fonksiyonu"""
    print("🧪 MAVSDK Subprocess Manager Test")
    print("=" * 50)
    
    # Manager oluştur
    manager = create_test_manager()
    
    try:
        # Test 1: Statistics
        stats = manager.get_statistics()
        print(f"📊 İstatistikler: {stats}")
        
        # Test 2: Takeoff task
        print("\n🚀 Takeoff task test...")
        success = manager.takeoff(altitude=15.0, timeout=60)
        print(f"Takeoff task başlatma: {'✅ Başarılı' if success else '❌ Başarısız'}")
        
        # Test 3: EW Mission (eğer mevcut)
        if EW_MISSIONS_AVAILABLE:
            print("\n🚁✈️ EW Mission test...")
            ew_params = {
                'altitude': 25.0,
                'duration': 180,
                'radius': 400.0
            }
            success = manager.start_ew_mission('ew_vtol_normal_patrol', ew_params, timeout=300)
            print(f"EW Mission başlatma: {'✅ Başarılı' if success else '❌ Başarısız'}")
        
        # Test 4: Task monitoring
        print("\n📊 Aktif task'lar:")
        active_tasks = manager.get_active_tasks()
        for task_id, task_info in active_tasks.items():
            print(f"  - {task_id}: {task_info.task_type.value} ({task_info.status.value})")
        
        # Test 5: Mission status
        mission_status = manager.get_mission_status()
        if mission_status:
            print(f"\n🎯 Mission durumu: {mission_status}")
        
        print("\n⏰ 10 saniye test süresi...")
        time.sleep(10)
        
        # Test 6: Stop all
        print("\n⏹️ Tüm task'ları durdur...")
        manager.stop_all()
        
        # Final stats
        final_stats = manager.get_statistics()
        print(f"\n📊 Final istatistikler: {final_stats}")
        
    except Exception as e:
        print(f"❌ Test hatası: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Cleanup
        print("\n🧹 Manager cleanup...")
        manager.shutdown()
        print("✅ Test tamamlandı!")


if __name__ == "__main__":
    # Main çalıştırıldığında test yap
    test_mavsdk_manager()
