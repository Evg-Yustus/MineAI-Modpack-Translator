import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from mineai.constants import LANGUAGES
from mineai.analysis_items import loose_file_scope
from mineai.engines.base import EngineCallbacks
from mineai.processors.discovery import discover_loose_lang_files
from mineai.processors.estimator import StringEstimator
from mineai.processors.locale_paths import target_locale_path
from mineai.processors.loose_json import LooseJsonProcessor
from mineai.runtime.state import JobState


TARGET_LANG = LANGUAGES["Русский"]


class _FakeService:
    def translate_dict(
        self,
        pending,
        _target_lang,
        _callbacks,
        **_kwargs,
    ):
        return {key: "Перевод" for key in pending}


class _MemoryPackWriter:
    def __init__(self) -> None:
        self.writes: dict[str, bytes] = {}

    def write(self, path: str, payload: bytes) -> None:
        self.writes[path] = payload


def _callbacks() -> EngineCallbacks:
    return EngineCallbacks(
        should_run=lambda: True,
        wait_if_paused=lambda: None,
        on_log=lambda *_args: None,
        on_status=lambda *_args: None,
    )


def _make_source(root: str, filename: str) -> tuple[Path, bytes]:
    lang_dir = Path(root) / "kubejs" / "assets" / "example" / "lang"
    lang_dir.mkdir(parents=True)
    source = lang_dir / filename
    original = b'{"message":"Original text"}'
    source.write_bytes(original)
    return source, original


class LooseLocalePathSafetyTests(unittest.TestCase):
    def _processor(self) -> LooseJsonProcessor:
        return LooseJsonProcessor(
            _FakeService(),
            JobState(is_running=True),
            _callbacks(),
        )

    def test_inplace_preserves_source_for_case_variants(self) -> None:
        for filename in ("en_us.json", "EN_US.JSON", "En_Us.Json"):
            with self.subTest(filename=filename), tempfile.TemporaryDirectory() as tmp:
                source, original = _make_source(tmp, filename)

                self.assertIn(str(source), discover_loose_lang_files(tmp))
                written_path = self._processor().process(
                    str(source),
                    tmp,
                    target_lang=TARGET_LANG,
                    mode="append",
                    output_mode="inplace",
                    pack_writer=None,
                )

                target = source.with_name("ru_ru.json")
                self.assertEqual(written_path, str(target))
                self.assertTrue(source.exists())
                self.assertEqual(source.read_bytes(), original)
                self.assertTrue(target.exists())
                self.assertNotEqual(
                    os.path.normcase(os.path.abspath(source)),
                    os.path.normcase(os.path.abspath(target)),
                )
                self.assertEqual(
                    json.loads(target.read_text(encoding="utf-8"))["message"],
                    "Перевод",
                )

    def test_resourcepack_uses_target_locale_name_for_uppercase_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source, original = _make_source(tmp, "EN_US.JSON")
            writer = _MemoryPackWriter()

            self._processor().process(
                str(source),
                tmp,
                target_lang=TARGET_LANG,
                mode="append",
                output_mode="resourcepack",
                pack_writer=writer,
            )

            self.assertEqual(source.read_bytes(), original)
            self.assertIn("assets/example/lang/ru_ru.json", writer.writes)
            self.assertNotIn("assets/example/lang/EN_US.JSON", writer.writes)
            self.assertEqual(
                json.loads(
                    writer.writes["assets/example/lang/ru_ru.json"].decode("utf-8")
                )["message"],
                "Перевод",
            )

    def test_estimator_uses_same_case_insensitive_target_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source, _original = _make_source(tmp, "En_Us.Json")
            estimator = StringEstimator(JobState(is_running=True))

            self.assertEqual(
                estimator._estimate_loose(
                    str(source),
                    "ru_ru.json",
                    "append",
                    TARGET_LANG["regex"],
                ),
                1,
            )

            source.with_name("ru_ru.json").write_text(
                json.dumps({"message": "Перевод"}, ensure_ascii=False),
                encoding="utf-8",
            )
            self.assertEqual(
                estimator._estimate_loose(
                    str(source),
                    "ru_ru.json",
                    "append",
                    TARGET_LANG["regex"],
                ),
                0,
            )

    def test_self_overwrite_guard_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source, original = _make_source(tmp, "EN_US.JSON")

            with mock.patch(
                "mineai.processors.loose_json.target_locale_path",
                side_effect=lambda path, _target: path,
            ):
                with self.assertRaisesRegex(
                    RuntimeError,
                    "Refusing to overwrite source locale file",
                ):
                    self._processor().process(
                        str(source),
                        tmp,
                        target_lang=TARGET_LANG,
                        mode="append",
                        output_mode="inplace",
                        pack_writer=None,
                    )

            self.assertEqual(source.read_bytes(), original)
            self.assertFalse(source.with_name("ru_ru.json").exists())

    def test_target_locale_path_replaces_only_trailing_locale_filename(self) -> None:
        source = "root/en_us.json_backup/assets/example/lang/EN_US.JSON"
        self.assertEqual(
            target_locale_path(source, "ru_ru.json"),
            "root/en_us.json_backup/assets/example/lang/ru_ru.json",
        )

    def test_discovers_config_namespace_language_dictionary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = (
                Path(tmp)
                / "config"
                / "collapsiblegroups"
                / "lang"
                / "en_us.json"
            )
            source.parent.mkdir(parents=True)
            source.write_text(
                json.dumps({"collapsible_groups.title": "Groups"}),
                encoding="utf-8",
            )

            self.assertIn(str(source), discover_loose_lang_files(tmp))

    def test_config_dictionary_uses_its_namespace_in_resourcepack(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = (
                Path(tmp)
                / "config"
                / "collapsiblegroups"
                / "lang"
                / "en_us.json"
            )
            source.parent.mkdir(parents=True)
            source.write_text(
                json.dumps({"collapsible_groups.title": "Groups"}),
                encoding="utf-8",
            )
            writer = _MemoryPackWriter()

            self._processor().process(
                str(source),
                tmp,
                target_lang=TARGET_LANG,
                mode="append",
                output_mode="resourcepack",
                pack_writer=writer,
            )

            self.assertIn(
                "assets/collapsiblegroups/lang/ru_ru.json",
                writer.writes,
            )

    def test_discovers_and_processes_nested_locale_book_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = (
                Path(tmp)
                / "kubejs"
                / "assets"
                / "tconstruct"
                / "book"
                / "encyclopedia"
                / "en_us"
                / "bonus.json"
            )
            source.parent.mkdir(parents=True)
            source.write_text(
                json.dumps(
                    {
                        "title": "Bonus",
                        "effects": ["Single use", "Slotless"],
                    }
                ),
                encoding="utf-8",
            )
            writer = _MemoryPackWriter()

            self.assertIn(str(source), discover_loose_lang_files(tmp))
            self.assertEqual(loose_file_scope(str(source)), "books")
            self.assertEqual(
                StringEstimator(JobState(is_running=True))._estimate_loose(
                    str(source),
                    "ru_ru.json",
                    "force",
                    TARGET_LANG["regex"],
                ),
                3,
            )
            self._processor().process(
                str(source),
                tmp,
                target_lang=TARGET_LANG,
                mode="force",
                output_mode="resourcepack",
                pack_writer=writer,
            )

            target = (
                "assets/tconstruct/book/encyclopedia/ru_ru/bonus.json"
            )
            self.assertIn(target, writer.writes)
            translated = json.loads(writer.writes[target])
            self.assertEqual(translated["title"], "Перевод")
            self.assertEqual(translated["effects"], ["Перевод", "Перевод"])


if __name__ == "__main__":
    unittest.main()
