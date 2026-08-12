import json
import os
import re

from mineai.engines.base import EngineCallbacks
from mineai.engines.service import TranslationService
from mineai.analysis_items import loose_file_scope
from mineai.io_utils import atomic_write_bytes
from mineai.json_utils import load_lenient_json
from mineai.output.pack_writer import PackWriter
from mineai.processors.locale_keys import (
    collect_lang_keys_to_translate,
    count_translatable_lang_entries,
)
from mineai.processors.locale_paths import ensure_distinct_paths, target_locale_path
from mineai.processors.selection import (
    build_book_json_output,
    collect_book_json_selection,
    skip_threshold_reached,
)
from mineai.runtime.state import JobState


class LooseJsonProcessor:
    def __init__(self, service: TranslationService, state: JobState, callbacks: EngineCallbacks) -> None:
        self.service = service
        self.state = state
        self.callbacks = callbacks

    def process(
        self,
        file_path: str,
        mc_dir: str,
        *,
        target_lang: dict,
        mode: str,
        output_mode: str,
        pack_writer: PackWriter | None,
    ) -> str | None:
        rel = os.path.relpath(file_path, mc_dir).replace("\\", "/")
        if "assets/" in rel:
            internal = rel[rel.find("assets/") :]
        else:
            parts = rel.split("/")
            try:
                lang_index = next(
                    index
                    for index, value in enumerate(parts)
                    if value.casefold() == "lang"
                    and index + 1 == len(parts) - 1
                )
                namespace = parts[lang_index - 1]
            except (StopIteration, IndexError):
                namespace = "kubejs"
            internal = (
                f"assets/{namespace}/lang/" + os.path.basename(file_path)
            )

        target_filename = f"{target_lang['file']}.json"
        is_book = loose_file_scope(file_path) == "books"
        if is_book:
            tr_internal = re.sub(
                r"(?i)(?<=/)en_us(?=/)",
                target_lang["file"],
                internal,
                count=1,
            )
            tr_disk = re.sub(
                r"(?i)(?<=[\\/])en_us(?=[\\/])",
                target_lang["file"],
                file_path,
                count=1,
            )
        else:
            tr_internal = target_locale_path(internal, target_filename)
            tr_disk = target_locale_path(file_path, target_filename)
        ensure_distinct_paths(file_path, tr_disk)

        with open(file_path, encoding="utf-8") as f:
            en_data = load_lenient_json(f.read().encode("utf-8"))
        tr_data = {}
        if os.path.exists(tr_disk):
            with open(tr_disk, encoding="utf-8") as f:
                tr_data = load_lenient_json(f.read().encode("utf-8"))

        if is_book:
            source_map, preserved, pending = collect_book_json_selection(
                en_data,
                tr_data,
                mode,
                target_lang,
            )
            total = len(source_map)
        else:
            pending = collect_lang_keys_to_translate(
                en_data,
                tr_data,
                mode,
                target_lang["regex"],
            )
            total = count_translatable_lang_entries(en_data)
        label = "Словарь: " + os.path.basename(os.path.dirname(os.path.dirname(file_path)))

        if mode == "skip" and skip_threshold_reached(total, len(pending)):
            if output_mode == "resourcepack" and pack_writer and os.path.exists(tr_disk):
                with open(tr_disk, "rb") as f:
                    pack_writer.write(tr_internal, f.read())
            return

        if is_book:
            merged = build_book_json_output(en_data, preserved, {})
        else:
            merged = en_data.copy()
            for k, v in tr_data.items():
                if k in merged:
                    merged[k] = v

        if pending:
            self.callbacks.on_log(f"⚡ Перевод {label} — {len(pending)} строк", "cyan")
            translate = (
                getattr(self.service, "translate_formatted_dict", None)
                if is_book
                else None
            ) or self.service.translate_dict
            translated = translate(
                pending,
                target_lang,
                self.callbacks,
                context="Локализация Квестов/Скриптов",
                prompt_type="books",
            )

            if not self.state.should_run():
                return

            if is_book:
                merged = build_book_json_output(en_data, preserved, translated)
            else:
                merged.update(translated)

        payload = json.dumps(merged, ensure_ascii=False, indent=2).encode("utf-8")
        if output_mode == "resourcepack" and pack_writer:
            pack_writer.write(tr_internal, payload)
        elif output_mode == "inplace":
            atomic_write_bytes(tr_disk, payload)
            return tr_disk
        return None
