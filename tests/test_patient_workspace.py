from __future__ import annotations

import unittest

from views.patient_workspace import (
    _estimated_days_to_rupture,
    _forecast_outcome,
    _ordered_encounter_keys,
    _prediction_success_stats,
)


class PatientWorkspaceForecastTests(unittest.TestCase):
    def test_prediction_success_stats_cover_all_available_results(self) -> None:
        encounter_keys = [f"REG-{index}::ADM-1" for index in range(300)]
        predictions = {
            encounter_key: {
                "patient_id": f"DEMO-{index}",
                "rupture_judgement": "是",
            }
            for index, encounter_key in enumerate(encounter_keys)
        }
        predictions[encounter_keys[-1]]["rupture_judgement"] = "否"

        stats = _prediction_success_stats(encounter_keys, predictions)

        self.assertEqual(stats["total"], 299)
        self.assertEqual(stats["success"] + stats["failure"], 299)
        self.assertGreater(stats["success"], stats["failure"])
        self.assertAlmostEqual(
            stats["success_rate"] + stats["failure_rate"],
            1.0,
        )

    def test_day_estimate_is_stable_and_uses_expected_range(self) -> None:
        critical = {"patient_id": "HB-TR-0001", "critical_status": "危急"}
        stable = {"patient_id": "HB-TR-0002", "critical_status": "暂时稳定"}

        critical_days = _estimated_days_to_rupture("REG-1::ADM-1", critical)
        repeated_days = _estimated_days_to_rupture("REG-1::ADM-1", critical)
        stable_days = _estimated_days_to_rupture("REG-2::ADM-1", stable)

        self.assertEqual(critical_days, repeated_days)
        self.assertIn(critical_days, {3, 4, 5, 6, 7})
        self.assertIn(stable_days, {7, 9, 10, 12, 14})

    def test_forecast_outcome_is_stable_and_includes_both_demo_results(self) -> None:
        prediction = {"patient_id": "HB-TR-0001", "critical_status": "危急"}
        first = _forecast_outcome("REG-1::ADM-1", prediction)
        repeated = _forecast_outcome("REG-1::ADM-1", prediction)
        outcomes = {
            _forecast_outcome(f"REG-{index}::ADM-1", prediction)
            for index in range(30)
        }
        outcome_sequence = [
            _forecast_outcome(f"REG-{index}::ADM-1", prediction)
            for index in range(300)
        ]

        self.assertEqual(first, repeated)
        self.assertEqual(outcomes, {"success", "failure"})
        success_rate = outcome_sequence.count("success") / len(outcome_sequence)
        self.assertGreaterEqual(success_rate, 0.87)
        self.assertLessEqual(success_rate, 0.93)

    def test_detail_encounters_are_ordered_from_high_to_low_risk(self) -> None:
        encounters = {
            "low": {"diagnosis": "低风险诊断"},
            "high-empty": {"diagnosis": "暂无诊断记录"},
            "medium": {"diagnosis": "中风险诊断"},
            "high-diagnosed-1": {"diagnosis": "急性心肌梗死"},
            "high-diagnosed-2": {"diagnosis": "心源性休克"},
        }
        predictions = {
            "low": {"risk_level": "LOW"},
            "high-empty": {"risk_level": "HIGH"},
            "medium": {"risk_level": "MEDIUM"},
            "high-diagnosed-1": {"risk_level": "HIGH"},
            "high-diagnosed-2": {"risk_level": "HIGH"},
        }

        self.assertEqual(
            _ordered_encounter_keys(encounters, predictions),
            [
                "high-diagnosed-1",
                "high-diagnosed-2",
                "high-empty",
                "medium",
                "low",
            ],
        )


if __name__ == "__main__":
    unittest.main()
