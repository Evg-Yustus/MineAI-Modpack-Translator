"""Tests for snbt_chapter_lang module — Beta41 chapter→lang extraction."""
import pytest
from mineai.processors.snbt_chapter_lang import (
    is_chapter_or_reward_snbt,
    is_lang_snbt,
    extract_chapter_lang_entries,
    load_lang_snbt,
    dump_lang_snbt,
    merge_and_write_lang_snbt,
)


# ---------------------------------------------------------------------------
# Path detection
# ---------------------------------------------------------------------------


class TestIsChapterOrRewardSnbt:
    def test_chapter_file(self):
        path = r"C:\mc\config\ftbquests\quests\chapters\getting_started.snbt"
        assert is_chapter_or_reward_snbt(path)

    def test_reward_table_file(self):
        path = "config/ftbquests/quests/reward_tables/default.snbt"
        assert is_chapter_or_reward_snbt(path)

    def test_data_snbt(self):
        path = "config/ftbquests/quests/data.snbt"
        assert is_chapter_or_reward_snbt(path)

    def test_lang_catalog_excluded(self):
        path = "config/ftbquests/quests/lang/en_us.snbt"
        assert not is_chapter_or_reward_snbt(path)

    def test_non_quest_snbt(self):
        path = "config/something_else.snbt"
        assert not is_chapter_or_reward_snbt(path)


class TestIsLangSnbt:
    def test_lang_folder(self):
        assert is_lang_snbt("config/ftbquests/quests/lang/ru_ru.snbt")

    def test_lang_subfolder(self):
        assert is_lang_snbt("config/ftbquests/quests/lang/en_us/chapter.snbt")

    def test_chapter_not_lang(self):
        assert not is_lang_snbt("config/ftbquests/quests/chapters/ch.snbt")


# ---------------------------------------------------------------------------
# Entry extraction
# ---------------------------------------------------------------------------


CHAPTER_FIXTURE = """\
{
\tid: "1A2B3C4D5E6F7890"
\ttitle: "Getting Started"
\tdescription: ["First step", "Second step"]
\tsubtitle: "{atm9.some.key}"
}
"""

CHAPTER_ATM9 = """\
{
\tid: "AAAAAAAAAAAAAAAA"
\ttitle: "{atm9.quest.title}"
\tdescription: ["Literal hint here"]
}
"""

MULTI_ENTRY_CHAPTER = """\
{
\tid: "1111111111111111"
\ttitle: "Quest One"
\tdesc: ["Step one"]
\tid: "2222222222222222"
\ttitle: "Quest Two"
\tquest_desc: ["Step two A", "Step two B"]
}
"""


class TestExtractChapterLangEntries:
    def test_title_extracted(self):
        entries = extract_chapter_lang_entries(CHAPTER_FIXTURE)
        assert "1A2B3C4D5E6F7890.title" in entries
        assert entries["1A2B3C4D5E6F7890.title"] == "Getting Started"

    def test_description_extracted_as_list(self):
        entries = extract_chapter_lang_entries(CHAPTER_FIXTURE)
        assert "1A2B3C4D5E6F7890.quest_desc" in entries
        assert entries["1A2B3C4D5E6F7890.quest_desc"] == ["First step", "Second step"]

    def test_translation_key_subtitle_excluded(self):
        """subtitle: {atm9.some.key} must not be extracted (it's a reference key)."""
        entries = extract_chapter_lang_entries(CHAPTER_FIXTURE)
        assert not any("subtitle" in k for k in entries)

    def test_atm9_chapter_only_literal_extracted(self):
        """ATM9 chapter: title is a reference key → excluded; description is literal → included."""
        entries = extract_chapter_lang_entries(CHAPTER_ATM9)
        assert "AAAAAAAAAAAAAAAA.title" not in entries
        assert "AAAAAAAAAAAAAAAA.quest_desc" in entries
        assert entries["AAAAAAAAAAAAAAAA.quest_desc"] == ["Literal hint here"]

    def test_multiple_quests_in_chapter(self):
        entries = extract_chapter_lang_entries(MULTI_ENTRY_CHAPTER)
        assert entries.get("1111111111111111.title") == "Quest One"
        assert entries.get("2222222222222222.title") == "Quest Two"
        assert entries.get("2222222222222222.quest_desc") == ["Step two A", "Step two B"]

    def test_empty_chapter(self):
        assert extract_chapter_lang_entries("{}") == {}

    def test_no_entries_without_hex_id(self):
        """Text without a preceding id: "HEXID" must not be extracted."""
        content = '{\n\ttitle: "Orphan title"\n}'
        entries = extract_chapter_lang_entries(content)
        assert entries == {}

    def test_technical_terms_excluded(self):
        """Technical-looking strings must not be extracted."""
        content = '{\n\tid: "ABCDEF1234567890"\n\ttitle: "mod:some_id"\n}'
        entries = extract_chapter_lang_entries(content)
        assert not entries


# ---------------------------------------------------------------------------
# SNBT file I/O
# ---------------------------------------------------------------------------


class TestDumpLoadLangSnbt:
    def test_roundtrip_string(self):
        data = {"ABCD.title": "Hello World"}
        dumped = dump_lang_snbt(data)
        loaded = load_lang_snbt.__wrapped__(dumped) if hasattr(load_lang_snbt, "__wrapped__") else None
        # Parse directly
        from mineai.processors.snbt_chapter_lang import _parse_lang_snbt
        reloaded = _parse_lang_snbt(dumped)
        assert reloaded == data

    def test_roundtrip_list(self):
        data = {"ABCD.quest_desc": ["Line one", "Line two"]}
        from mineai.processors.snbt_chapter_lang import _parse_lang_snbt
        assert _parse_lang_snbt(dump_lang_snbt(data)) == data

    def test_roundtrip_unicode_and_escapes(self):
        data = {"FF00.title": 'Qu\u00eate avec "guillemets"'}
        from mineai.processors.snbt_chapter_lang import _parse_lang_snbt
        assert _parse_lang_snbt(dump_lang_snbt(data)) == data

    def test_empty_dict(self):
        assert dump_lang_snbt({}) == "{\n}\n"


class TestMergeAndWriteLangSnbt:
    def test_creates_file_if_missing(self, tmp_path):
        target = tmp_path / "ru_ru.snbt"
        merge_and_write_lang_snbt(str(target), {"A.title": "Hello"})
        from mineai.processors.snbt_chapter_lang import _parse_lang_snbt
        loaded = _parse_lang_snbt(target.read_text(encoding="utf-8"))
        assert loaded == {"A.title": "Hello"}

    def test_existing_keys_preserved_by_default(self, tmp_path):
        target = tmp_path / "ru_ru.snbt"
        target.write_text('{\n\t"A.title": "Old Value"\n}\n', encoding="utf-8")
        merge_and_write_lang_snbt(str(target), {"A.title": "New Value", "B.title": "New"})
        from mineai.processors.snbt_chapter_lang import _parse_lang_snbt
        loaded = _parse_lang_snbt(target.read_text(encoding="utf-8"))
        # Old value preserved, new key added
        assert loaded["A.title"] == "Old Value"
        assert loaded["B.title"] == "New"

    def test_overwrite_existing_keys(self, tmp_path):
        target = tmp_path / "ru_ru.snbt"
        target.write_text('{\n\t"A.title": "Old"\n}\n', encoding="utf-8")
        merge_and_write_lang_snbt(
            str(target),
            {"A.title": "New"},
            overwrite_existing=True,
        )
        from mineai.processors.snbt_chapter_lang import _parse_lang_snbt
        loaded = _parse_lang_snbt(target.read_text(encoding="utf-8"))
        assert loaded["A.title"] == "New"
