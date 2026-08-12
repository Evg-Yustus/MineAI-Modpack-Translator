import json
import os
import tempfile
import unittest
from unittest import mock
import zipfile

from mineai.cache import TranslationCache
from mineai.io_utils import atomic_write_bytes
from mineai.output.pack_writer import PackWriter


class AtomicWriteTests(unittest.TestCase):
    def test_corrupt_ai_cache_is_replaced_immediately_after_backup(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "ai_cache.json")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write("{not-json")

            TranslationCache(path)

            self.assertTrue(os.path.exists(path + ".corrupt"))
            with open(path, encoding="utf-8") as handle:
                repaired = json.load(handle)
            self.assertIsInstance(repaired, dict)

    def test_incomplete_ai_cache_entry_is_removed_during_load(self):
        source = (
            "The grid fills itself when the items are ready, meaning you do "
            "not have to keep checking if the items are available."
        )
        incomplete = (
            "Сетка заполняется автоматически, meaning you do not have to "
            "keep checking if the items are available."
        )

        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "ai_cache.json")
            cache = TranslationCache(path)
            cache.set("ru", source, incomplete)
            cache.save()

            repaired = TranslationCache(path)

            self.assertEqual(repaired.get("ru", source), (None, False))
            self.assertTrue(os.path.exists(path + ".pre-auto-repair"))
            with open(path + ".pre-auto-repair", encoding="utf-8") as handle:
                self.assertIn("ru_" + source, json.load(handle))
            with open(path, encoding="utf-8") as handle:
                self.assertNotIn("ru_" + source, json.load(handle))

    def test_beta25_ai_cache_is_backed_up_and_invalidated_once(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "ai_cache.json")
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(
                    {"ru_When fully upgraded.": "Экспорт"},
                    handle,
                    ensure_ascii=False,
                )

            cache = TranslationCache(path)

            self.assertEqual(cache.get("ru", "When fully upgraded."), (None, False))
            self.assertTrue(os.path.exists(path + ".pre-beta26"))
            cache.set("ru", "Hello", "Привет")
            cache.save()
            reloaded = TranslationCache(path)
            self.assertEqual(reloaded.get("ru", "Hello"), ("Привет", False))

    def test_failed_replace_preserves_original_and_removes_temp_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "data.json")
            with open(path, "wb") as handle:
                handle.write(b"original")

            with mock.patch("mineai.io_utils.os.replace", side_effect=OSError("locked")):
                with self.assertRaisesRegex(OSError, "locked"):
                    atomic_write_bytes(path, b"replacement")

            with open(path, "rb") as handle:
                self.assertEqual(handle.read(), b"original")
            self.assertEqual(os.listdir(directory), ["data.json"])

    def test_corrupt_cache_is_backed_up_before_next_save(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "cache.json")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write("{not-json")

            cache = TranslationCache(path)
            cache.set("ru", "Hello", "Привет")
            cache.save()

            with open(path + ".corrupt", encoding="utf-8") as handle:
                self.assertEqual(handle.read(), "{not-json")
            with open(path, encoding="utf-8") as handle:
                self.assertEqual(json.load(handle)["ru_Hello"], "Привет")


class PackWriterTests(unittest.TestCase):
    def test_created_resource_pack_is_enabled_with_highest_priority(self):
        with tempfile.TemporaryDirectory() as directory:
            options = os.path.join(directory, "options.txt")
            with open(options, "w", encoding="utf-8", newline="") as handle:
                handle.write(
                    'resourcePacks:["vanilla","file/Older.zip"]\r\n'
                    "incompatibleResourcePacks:[]\r\n"
                )
            writer = PackWriter(directory, "MineAI New", "1.21.1", "Russian")
            writer.write("assets/example/lang/ru_ru.json", b"{}")

            resourcepack, _datapack = writer.close()

            self.assertIsNotNone(resourcepack)
            with open(options, encoding="utf-8", newline="") as handle:
                saved = handle.read()
            self.assertIn(
                'resourcePacks:["vanilla", "file/Older.zip", "file/MineAI New.zip"]',
                saved,
            )
            self.assertNotIn("\n", saved.replace("\r\n", ""))
            self.assertTrue(writer.resourcepack_enabled)

    def test_datapack_only_output_does_not_change_resource_pack_options(self):
        with tempfile.TemporaryDirectory() as directory:
            options = os.path.join(directory, "options.txt")
            original = 'resourcePacks:["vanilla"]\n'
            with open(options, "w", encoding="utf-8") as handle:
                handle.write(original)
            writer = PackWriter(directory, "Quest Pack", "1.21.1", "Russian")
            writer.write("data/example/quests/ru_ru.snbt", b"{}")

            writer.close()

            with open(options, encoding="utf-8") as handle:
                self.assertEqual(handle.read(), original)
            self.assertFalse(writer.resourcepack_enabled)

    def test_empty_new_packs_are_removed_without_touching_existing_pack(self):
        with tempfile.TemporaryDirectory() as directory:
            resourcepacks = os.path.join(directory, "resourcepacks")
            os.makedirs(resourcepacks)
            existing = os.path.join(resourcepacks, "MineAI_Pack.zip")
            with open(existing, "wb") as handle:
                handle.write(b"existing-pack")

            writer = PackWriter(directory, "MineAI_Pack", "1.20.1", "Russian")
            outputs = writer.close()

            with open(existing, "rb") as handle:
                self.assertEqual(handle.read(), b"existing-pack")
            self.assertEqual(outputs, (None, None))
            self.assertFalse(
                os.path.exists(os.path.join(resourcepacks, "MineAI_Pack_1.zip"))
            )

    def test_close_keeps_only_pack_with_payload(self):
        with tempfile.TemporaryDirectory() as directory:
            writer = PackWriter(directory, "MineAI_Pack", "1.20.1", "Russian")
            writer.write("assets/example/lang/ru_ru.json", b"{}")

            resourcepack, datapack = writer.close()

            self.assertIsNotNone(resourcepack)
            self.assertIsNone(datapack)
            self.assertTrue(os.path.exists(resourcepack))
            with zipfile.ZipFile(resourcepack) as archive:
                self.assertEqual(
                    set(archive.namelist()),
                    {"pack.mcmeta", "assets/example/lang/ru_ru.json"},
                )


if __name__ == "__main__":
    unittest.main()
