from __future__ import annotations

import unittest

from agent.tools import extract_clinical_features, get_patient_timeline
from services.clinical_context import get_patient_clinical_context
from services.react_data import (
    get_encounter_dataframe,
    get_encounter_detail,
    get_source_record,
)


class ReActDatabaseSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.frame = get_encounter_dataframe(20)
        cls.positive_id = str(
            cls.frame.loc[cls.frame["cohort_label"].eq(1), "encounter_key"].iloc[0]
        )

    def test_react_sample_contains_real_positive_and_negative_rows(self) -> None:
        self.assertEqual(set(self.frame["cohort_label"]), {0, 1})
        self.assertTrue(self.frame["encounter_key"].str.startswith("XD-").all())
        self.assertEqual(
            set(self.frame.groupby("cohort_label")["cohort_group"].first()),
            {"心脏破裂组", "非破裂组"},
        )

    def test_database_detail_matches_selected_positive_sample(self) -> None:
        detail = get_encounter_detail(self.positive_id)
        self.assertEqual(detail["profile"]["cohort_group"], "心脏破裂组")
        self.assertEqual(detail["profile"]["risk_level"], "UNKNOWN")
        self.assertTrue(detail["timeline"])

    def test_prediction_context_uses_database_without_label_leakage(self) -> None:
        source = get_source_record(self.positive_id)
        context = get_patient_clinical_context(
            self.positive_id,
            use_llm_compression=False,
        )
        clinical_input = str(context.get("clinical_input") or "")

        self.assertNotIn("error", context)
        self.assertGreater(context["event_count"], 0)
        self.assertEqual(context["sources"][0], "patient_data.db")
        self.assertNotIn("label", clinical_input.lower())
        self.assertNotIn(str(source.get("regno") or ""), clinical_input)
        self.assertNotIn(str(source.get("admno") or ""), clinical_input)

    def test_untimed_narrative_is_kept_without_fabricating_a_time_bucket(self) -> None:
        patient_id = "XD-DCE3E85796"
        context = get_patient_clinical_context(
            patient_id,
            use_llm_compression=False,
        )

        self.assertGreater(context["grounded_fact_count"], 0)
        self.assertIn("阵发性胸痛2天", context["clinical_input"])
        self.assertIn("急性侧壁正后壁心肌梗死", context["clinical_input"])
        self.assertIn("具体记录时间未可靠对齐", context["clinical_input"])
        self.assertEqual(sum(context["window_event_counts"].values()), 0)
        self.assertNotIn("心脏破裂组", context["clinical_input"])

    def test_react_tools_resolve_database_display_id(self) -> None:
        timeline = get_patient_timeline(self.positive_id)
        features = extract_clinical_features(self.positive_id)

        self.assertGreater(timeline["event_count"], 0)
        self.assertIn("patient_data.db", timeline["sources"][0])
        self.assertEqual(features["profile"]["cohort_group"], "心脏破裂组")
        self.assertIn("patient_data.db", features["sources"][0])


if __name__ == "__main__":
    unittest.main()
