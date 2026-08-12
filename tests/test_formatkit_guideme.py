import unittest

from formatkit import FormatRegistry


class GuideMeAdapterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = FormatRegistry.default()

    def test_guideme_uses_underscored_locale_and_preserves_scene(self) -> None:
        source = (
            "---\n"
            "navigation:\n"
            "  title: Getting Started\n"
            "---\n\n"
            "# Getting Started\n\n"
            '<GameScene zoom="4">\n'
            '  <ImportStructure src="assets/assemblies/meteor_interior.snbt" />\n'
            "</GameScene>\n\n"
            'The <ItemLink id="ae2:chest" /> is useful.\n'
        )

        plan = self.registry.plan(
            "assets/ae2/ae2guide/getting-started.md",
            source,
            "ru_ru",
        )

        self.assertEqual(
            plan.target_path,
            "assets/ae2/ae2guide/_ru_ru/getting-started.md",
        )
        self.assertTrue(all("ImportStructure" not in u.payload for u in plan.units))
        body = next(u for u in plan.units if "useful" in u.payload)
        anchor = next(a.token for a in body.anchors)
        result = plan.apply({body.id: f"{anchor} полезен."})
        self.assertIn('<ItemLink id="ae2:chest" /> полезен.', result.text)
        self.assertIn("meteor_interior.snbt", result.text)

    def test_markdown_table_cells_are_translation_units(self) -> None:
        source = (
            "| Setting | Description |\n"
            "| --- | --- |\n"
            "| Default | Standard channel mode |\n"
        )
        plan = self.registry.plan(
            "assets/ae2/ae2guide/channels.md",
            source,
            "ru_ru",
        )
        payloads = {unit.payload for unit in plan.units}

        self.assertIn("Setting", payloads)
        self.assertIn("Description", payloads)
        self.assertIn("Standard channel mode", payloads)
        translations = {
            unit.id: {
                "Setting": "Настройка",
                "Description": "Описание",
                "Default": "По умолчанию",
                "Standard channel mode": "Стандартный режим каналов",
            }[unit.payload]
            for unit in plan.units
        }
        result = plan.apply(translations)
        self.assertEqual(
            result.text,
            "| Настройка | Описание |\n"
            "| --- | --- |\n"
            "| По умолчанию | Стандартный режим каналов |\n",
        )

    def test_wrapped_paragraph_is_one_contextual_unit(self) -> None:
        source = (
            "Spatial cells can store regions across\n"
            "dimensions.\n"
        )
        plan = self.registry.plan(
            "assets/ae2/ae2guide/spatial.md",
            source,
            "ru_ru",
        )

        self.assertEqual(len(plan.units), 1)
        self.assertIn("Spatial cells", plan.units[0].payload)
        self.assertIn("dimensions.", plan.units[0].payload)
        self.assertIn("FK", plan.units[0].payload)

    def test_wrapped_links_and_tags_remain_protected(self) -> None:
        source = (
            "Read [Pattern\nProviders](ae2:pattern_provider.md) and use "
            '<ItemLink\nid="ae2:memory_card" />.\n'
        )
        plan = self.registry.plan(
            "assets/mae2/ae2guide/page.md",
            source,
            "ru_ru",
        )

        self.assertEqual(plan.apply({}).text, source)
        payload = plan.units[0].payload
        self.assertIn("Pattern", payload)
        self.assertIn("Providers", payload)
        self.assertNotIn("pattern_provider.md", payload)
        self.assertNotIn("ItemLink", payload)

    def test_fenced_code_block_is_never_a_translation_unit(self) -> None:
        source = "Before text.\n\n```js\nconst label = 'Do not translate';\n```\n"
        plan = self.registry.plan(
            "assets/ae2/ae2guide/code.md",
            source,
            "ru_ru",
        )

        payloads = "\n".join(unit.payload for unit in plan.units)
        self.assertIn("Before text", payloads)
        self.assertNotIn("Do not translate", payloads)
        self.assertEqual(plan.apply({}).text, source)


if __name__ == "__main__":
    unittest.main()
