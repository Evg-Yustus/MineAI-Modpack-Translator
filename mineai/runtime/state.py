import threading
import time
from dataclasses import dataclass, field

@dataclass
class JobState:
    is_running: bool = False
    is_paused: bool = False
    
    # Статистика по строкам
    total_strings: int = 0
    translated_strings: int = 0
    
    # Статистика по файлам (НОВОЕ)
    current_file_type: str = ""
    current_file_done: int = 0
    total_files: int = 0
    
    start_time: float | None = None
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def wait_if_paused(self) -> None:
        while self.is_paused and self.is_running:
            time.sleep(0.5)

    def should_run(self) -> bool:
        with self._lock:
            return self.is_running

    def stop(self) -> None:
        with self._lock:
            self.is_running = False
            self.is_paused = False

    def increment_translated(self, count: int = 1) -> None:
        with self._lock:
            self.translated_strings += count

    # НОВОЕ: Функция для обновления прогресса файлов
    def update_file_progress(self, file_type: str, done: int, total: int) -> None:
        with self._lock:
            self.current_file_type = file_type
            self.current_file_done = done
            self.total_files = total

    def eta_text(self) -> str:
        if not self.start_time or self.translated_strings == 0:
            return "расчёт..."
        elapsed = time.time() - self.start_time
        if elapsed < 5:
            return "расчёт..."
        remaining = self.total_strings - self.translated_strings
        if remaining <= 0:
            return "готово"
        rate = self.translated_strings / elapsed
        seconds = remaining / rate
        if seconds < 60:
            return f"{int(seconds)} сек"
        if seconds < 3600:
            return f"{int(seconds // 60)} мин {int(seconds % 60)} сек"
        return f"{int(seconds // 3600)} ч {int((seconds % 3600) // 60)} мин"

    # НОВОЕ: Единая функция генерации красивого статуса
    def get_full_status(self, engine_msg: str = "") -> str:
        with self._lock:
            # 1. Прогресс по файлам (например: "Модов 5/150")
            file_info = ""
            if self.total_files > 0:
                file_info = f"[{self.current_file_type} {self.current_file_done}/{self.total_files}] "
                
            # 2. Прогресс по строкам (например: "Строки 100/5000")
            string_info = ""
            if self.total_strings > 0:
                string_info = f"Строки: {self.translated_strings}/{self.total_strings} | "
                
            # 3. Сообщение от движка (например: "ИИ переводит...")
            engine_info = f"{engine_msg} | " if engine_msg else ""
            
            # 4. ETA
            eta = f"Осталось: {self.eta_text()}"
            
            return f"{file_info}{string_info}{engine_info}{eta}"