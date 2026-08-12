import unittest

from formatkit import FormatRegistry


class ImmersiveEngineeringAdapterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = FormatRegistry.default()

    def test_link_with_apostrophe_keeps_id_and_translates_label(self) -> None:
        source = (
            "Blueprints\n"
            "Engineering!\n"
            "All blueprints can be used in an "
            "<link;engineers_workbench;Engineer's Workbench> to craft items.<np>\n"
        )
        plan = self.registry.plan(
            "assets/immersiveengineering/manual/en_us/blueprints.txt",
            source,
            "ru_ru",
        )
        body = plan.units[2]

        self.assertNotIn("engineers_workbench", body.payload)
        self.assertNotIn("<link", body.payload)
        self.assertIn("Engineer's Workbench", body.payload)
        tokens = [anchor.token for anchor in body.anchors]
        translated = (
            f"Все чертежи можно использовать в {tokens[0]}"
            f"Инженерном верстаке{tokens[1]} для создания предметов.{tokens[2]}"
        )
        result = plan.apply({body.id: translated})

        self.assertIn(
            "<link;engineers_workbench;Инженерном верстаке>",
            result.text,
        )
        self.assertIn("<np>", result.text)

    def test_recipe_and_format_codes_round_trip_losslessly(self) -> None:
        source = (
            "<&frame_recipe>§lAccumulators§r store energy.<br>\r\n"
        )
        plan = self.registry.plan(
            "assets/immersiveengineering/manual/en_us/accumulators.txt",
            source,
            "ru_ru",
        )

        self.assertEqual(plan.apply({}).text, source)
        payload = plan.units[0].payload
        self.assertNotIn("frame_recipe", payload)
        self.assertNotIn("§", payload)
        self.assertNotIn("<br>", payload)

    def test_ie_target_path_uses_plain_locale(self) -> None:
        plan = self.registry.plan(
            "assets/immersiveengineering/manual/en_us/page.txt",
            "Page\nSubtitle\nBody text.\n",
            "ru_ru",
        )
        self.assertEqual(
            plan.target_path,
            "assets/immersiveengineering/manual/ru_ru/page.txt",
        )


if __name__ == "__main__":
    unittest.main()

