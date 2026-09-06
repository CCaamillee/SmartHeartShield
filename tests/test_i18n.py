from __future__ import annotations

import re
import unittest

from components.i18n import display_value, source_label, ui_text


class ClinicalDisplayTranslationTests(unittest.TestCase):
    def test_translates_compound_diagnosis_without_chinese_characters(self) -> None:
        source = (
            "1.不稳定性心绞痛 2.心功能Ⅱ级(NYHA分级) "
            "3.胃溃疡 4.冠状动脉支架植入术后状态"
        )

        translated = display_value(source)

        self.assertIn("unstable angina", translated)
        self.assertIn("cardiac function grade Ⅱ", translated)
        self.assertIn("gastric ulcer", translated)
        self.assertIn("status post coronary stent implantation", translated)
        self.assertIsNone(re.search(r"[\u3400-\u9fff]", translated))

    def test_translates_filter_values(self) -> None:
        self.assertEqual(display_value("心内科"), "Cardiology")
        self.assertEqual(display_value("女"), "Female")
        self.assertEqual(display_value("冠状动脉造影术"), "coronary angiography")

    def test_translates_database_sample_labels_and_sources(self) -> None:
        self.assertEqual(display_value("数据库样本"), "Database Sample")
        self.assertEqual(ui_text("数据库样本"), "Database Sample")
        self.assertEqual(source_label("院内结构化数据"), "Structured hospital data")

    def test_ui_fallback_never_exposes_untranslated_chinese(self) -> None:
        translated = ui_text("需要进一步核对的临床记录")

        self.assertIsNone(re.search(r"[\u3400-\u9fff]", translated))


if __name__ == "__main__":
    unittest.main()
