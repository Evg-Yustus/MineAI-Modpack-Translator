import subprocess
import time

import requests

from mineai.config import ConfigManager
from mineai.constants import KOBOLD_MODELS_URL


class AiLauncher:
    def __init__(self, config: ConfigManager) -> None:
        self.config = config
        self.process: subprocess.Popen | None = None

    def is_alive(self) -> bool:
        try:
            return requests.get(KOBOLD_MODELS_URL, timeout=1).status_code == 200
        except requests.RequestException:
            return False

    def ensure_running(self, should_continue, on_status, on_log) -> bool:
        if self.is_alive():
            on_log("✅ ИИ уже работает", "green")
            return True

        exe = self.config.get("AI", "exe_path")
        model = self.config.get("AI", "model_path")
        gpu = self.config.get("AI", "gpu_layers")
        if not gpu.isdigit():
            gpu = "99"

        on_log("🤖 Запуск ИИ...", "cyan")
        try:
            self.process = subprocess.Popen(
                [
                    exe,
                    model,
                    "--port",
                    "5001",
                    "--quiet",
                    "--contextsize",
                    "4096",
                    "--gpulayers",
                    gpu,
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except OSError as exc:
            on_log(f"❌ Ошибка запуска ИИ: {exc}", "red")
            return False

        for i in range(180):
            if not should_continue():
                return False
            on_status(f"Прогрев нейросети... ({i}/600 сек)")
            if self.is_alive():
                on_log("✅ ИИ успешно запущен!\n", "green")
                return True
            time.sleep(1)

        on_log("❌ Сервер ИИ не отвечает.", "red")
        return False

    def terminate(self) -> None:
        if self.process:
            try:
                self.process.terminate()
            except OSError:
                pass
            self.process = None
