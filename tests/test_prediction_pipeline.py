from __future__ import annotations

import unittest

from agent.prediction_pipeline import run_all_patient_rupture_pipeline


class PredictionPipelineTests(unittest.TestCase):
    def test_pipeline_keeps_encounters_separate_and_deduplicates_keys(self) -> None:
        records = [
            {"encounter_key": "PATIENT-A::VISIT-1"},
            {"encounter_key": "PATIENT-A::VISIT-2"},
            {"encounter_key": "PATIENT-A::VISIT-1"},
        ]
        requested_contexts: list[str] = []
        requested_predictions: list[str] = []

        def context_provider(encounter_key: str) -> dict:
            requested_contexts.append(encounter_key)
            return {"clinical_input": "已脱敏的预测截点前资料", "sources": ["测试"]}

        def risk_predictor(encounter_key: str, context: dict) -> dict:
            requested_predictions.append(encounter_key)
            self.assertIn("clinical_input", context)
            return {
                "available": True,
                "prediction": {
                    "fields": {
                        "rupture_judgment": "否",
                        "current_urgency": "暂时稳定",
                        "core_evidence": "当前观察窗内未见明确破裂证据。",
                        "rupture_label": "0",
                        "rupture_time_window": "no_rupture_within_14d",
                        "evidence_confidence": "中",
                        "explanation": "测试输出",
                    },
                    "answer": "测试输出",
                },
            }

        result = run_all_patient_rupture_pipeline(
            records,
            context_provider=context_provider,
            risk_predictor=risk_predictor,
        )

        self.assertEqual(result["total"], 2)
        self.assertEqual(result["completed"], 2)
        self.assertEqual(requested_contexts, ["PATIENT-A::VISIT-1", "PATIENT-A::VISIT-2"])
        self.assertEqual(requested_predictions, requested_contexts)
        model_output = result["results"][0]["model_output"]
        self.assertEqual(model_output["rupture_judgment"], "否")
        self.assertEqual(model_output["current_urgency"], "暂时稳定")
        self.assertIn("未见明确破裂证据", model_output["core_evidence"])


if __name__ == "__main__":
    unittest.main()
