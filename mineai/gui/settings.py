import customtkinter as ctk
from tkinter import filedialog

from mineai.config import ConfigManager
from mineai.constants import DEFAULT_OPENROUTER_MODEL


class SettingsWindow(ctk.CTkToplevel):
    def __init__(self, parent, config: ConfigManager, on_saved) -> None:
        super().__init__(parent)
        self.config = config
        self.on_saved = on_saved
        self.title("⚙ Настройки MineAI")
        self.geometry("540x680")
        self.resizable(False, False)
        self.grab_set()

        tabs = ctk.CTkTabview(self)
        tabs.pack(fill="both", expand=True, padx=10, pady=10)
        tab_ai = tabs.add("Локальный ИИ")
        tab_or = tabs.add("OpenRouter")
        tab_gen = tabs.add("Общие и API")

        ctk.CTkLabel(tab_ai, text="Исполняемый файл KoboldCPP (.exe):", font=("", 12, "bold")).pack(
            anchor="w", pady=(10, 0), padx=10
        )
        self.ent_ai_exe = ctk.CTkEntry(tab_ai, width=360)
        self.ent_ai_exe.insert(0, config.get("AI", "exe_path"))
        self.ent_ai_exe.pack(fill="x", padx=10, pady=5)
        ctk.CTkButton(
            tab_ai, text="Обзор", width=80, command=lambda: self._browse(self.ent_ai_exe, [("Executables", "*.exe")])
        ).pack(anchor="e", padx=10)

        ctk.CTkLabel(tab_ai, text="Модель (.gguf):", font=("", 12, "bold")).pack(anchor="w", pady=(10, 0), padx=10)
        self.ent_ai_mod = ctk.CTkEntry(tab_ai, width=360)
        self.ent_ai_mod.insert(0, config.get("AI", "model_path"))
        self.ent_ai_mod.pack(fill="x", padx=10, pady=5)
        ctk.CTkButton(
            tab_ai, text="Обзор", width=80, command=lambda: self._browse(self.ent_ai_mod, [("GGUF Models", "*.gguf")])
        ).pack(anchor="e", padx=10)

        gpu_val = config.getint("AI", "gpu_layers", 99)
        self.lbl_gpu = ctk.CTkLabel(tab_ai, text=f"Слои GPU: {gpu_val}", font=("", 12, "bold"))
        self.lbl_gpu.pack(anchor="w", pady=(10, 0), padx=10)
        self.slider_gpu = ctk.CTkSlider(
            tab_ai,
            from_=0,
            to=99,
            number_of_steps=99,
            command=lambda v: self.lbl_gpu.configure(text=f"Слои GPU: {int(v)}"),
        )
        self.slider_gpu.set(gpu_val)
        self.slider_gpu.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(
            tab_or,
            text="Ключ: openrouter.ai/keys",
            font=("", 11),
            text_color="gray",
        ).pack(anchor="w", padx=10, pady=(10, 0))
        
        ctk.CTkLabel(tab_or, text="API URL (для Ollama, vLLM и др.):", font=("", 12, "bold")).pack(anchor="w", padx=10, pady=(10, 0))
        self.ent_or_url = ctk.CTkEntry(tab_or)
        self.ent_or_url.insert(0, config.get("OPENROUTER", "api_url"))
        self.ent_or_url.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(tab_or, text="API ключ OpenRouter:", font=("", 12, "bold")).pack(anchor="w", padx=10, pady=(5, 0))
        self.ent_or_key = ctk.CTkEntry(tab_or, show="*")
        self.ent_or_key.insert(0, config.get("OPENROUTER", "api_key"))
        self.ent_or_key.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(tab_or, text="ID модели (напр. qwen/qwen-2.5-72b-instruct):", font=("", 12, "bold")).pack(
            anchor="w", padx=10, pady=(10, 0)
        )
        self.ent_or_model = ctk.CTkEntry(tab_or)
        self.ent_or_model.insert(0, config.get("OPENROUTER", "model") or DEFAULT_OPENROUTER_MODEL)
        self.ent_or_model.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(tab_or, text="Site URL (необязательно, для статистики):", font=("", 12, "bold")).pack(
            anchor="w", padx=10, pady=(10, 0)
        )
        self.ent_or_site = ctk.CTkEntry(tab_or)
        self.ent_or_site.insert(0, config.get("OPENROUTER", "site_url"))
        self.ent_or_site.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(tab_or, text="Название приложения (X-Title):", font=("", 12, "bold")).pack(
            anchor="w", padx=10, pady=(10, 0)
        )
        self.ent_or_app = ctk.CTkEntry(tab_or)
        self.ent_or_app.insert(0, config.get("OPENROUTER", "app_name"))
        self.ent_or_app.pack(fill="x", padx=10, pady=5)

        self.var_smart = ctk.BooleanVar(value=config.getboolean("GENERAL", "smart_glue"))
        ctk.CTkSwitch(tab_gen, text="✨ Умный склейщик предложений", variable=self.var_smart).pack(
            anchor="w", padx=10, pady=15
        )

        workers = config.getint("GENERAL", "google_workers", 5)
        ctk.CTkLabel(tab_gen, text="Потоки Google Translate:", font=("", 12, "bold")).pack(anchor="w", padx=10)
        self.slider_thr = ctk.CTkSlider(tab_gen, from_=1, to=10, number_of_steps=9)
        self.slider_thr.set(workers)
        self.slider_thr.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(tab_gen, text="API ключ DeepL:", font=("", 12, "bold")).pack(anchor="w", pady=(10, 0), padx=10)
        self.ent_deepl = ctk.CTkEntry(tab_gen, show="*")
        self.ent_deepl.insert(0, config.get("API", "deepl_key"))
        self.ent_deepl.pack(fill="x", padx=10, pady=5)

        ctk.CTkButton(
            self,
            text="💾 Сохранить настройки",
            fg_color="#28a745",
            hover_color="#218838",
            command=self._save,
        ).pack(fill="x", padx=20, pady=10)

    def _browse(self, entry: ctk.CTkEntry, filetypes) -> None:
        path = filedialog.askopenfilename(filetypes=filetypes)
        if path:
            entry.delete(0, "end")
            entry.insert(0, path)

    def _save(self) -> None:
        self.config.set("AI", "exe_path", self.ent_ai_exe.get())
        self.config.set("AI", "model_path", self.ent_ai_mod.get())
        self.config.set("AI", "gpu_layers", int(self.slider_gpu.get()))
        self.config.set("OPENROUTER", "api_key", self.ent_or_key.get())
        self.config.set("OPENROUTER", "api_url", self.ent_or_url.get().strip())
        self.config.set("OPENROUTER", "model", self.ent_or_model.get().strip())
        self.config.set("OPENROUTER", "site_url", self.ent_or_site.get().strip())
        self.config.set("OPENROUTER", "app_name", self.ent_or_app.get().strip())
        self.config.set("GENERAL", "smart_glue", self.var_smart.get())
        self.config.set("GENERAL", "google_workers", int(self.slider_thr.get()))
        self.config.set("API", "deepl_key", self.ent_deepl.get())
        self.on_saved()
        self.destroy()
