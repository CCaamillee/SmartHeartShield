from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from services.prediction_api import (
    _evaluation_prediction_time,
    _load_evaluation_overview,
    _load_evaluation_patient_records,
    _load_prediction_overview,
    get_evaluation_prediction_for_subject,
    get_evaluation_predictions_for_subjects,
    normalize_live_prediction,
)


class PredictionOverviewTests(unittest.TestCase):
    def test_live_model_result_is_normalized_without_inference(self) -> None:
        result = normalize_live_prediction(
            {
                "available": True,
                "model": "cardiac-rupture-qwen38",
                "prediction": {
                    "fields": {
                        "rupture_label": "1",
                        "rupture_time_window": "day_1_2",
                        "evidence_confidence": "高",
                        "explanation": "仅用于测试解析",
                    }
                },
            }
        )
        self.assertTrue(result["available"])
        self.assertEqual(result["risk_level"], "HIGH")
        self.assertEqual(result["risk_label"], "高风险")
        self.assertEqual(result["prediction_time"], "后1至2天")

    def test_incomplete_live_result_stays_unknown(self) -> None:
        result = normalize_live_prediction(
            {"available": True, "prediction": {"fields": {}}}
        )
        self.assertFalse(result["available"])
        self.assertEqual(result["risk_level"], "UNKNOWN")

    def test_trained_contract_is_available_to_agent_page(self) -> None:
        result = normalize_live_prediction(
            {
                "available": True,
                "prediction": {
                    "fields": {
                        "rupture_judgment": "证据不足",
                        "current_urgency": "危急",
                        "core_evidence": "资料提示循环不稳定，但关键影像尚缺。",
                    }
                },
            }
        )
        self.assertTrue(result["available"])
        self.assertEqual(result["risk_level"], "HIGH")
        self.assertEqual(result["rupture_judgment"], "证据不足")
        self.assertEqual(result["current_urgency"], "危急")
        self.assertIn("关键影像", result["core_evidence"])

    def test_predictions_are_aggregated_without_retrospective_label_leakage(self) -> None:
        records = [
            {
                "label": 0,
                "predicted_label": 1,
                "predicted_time_window": "day_1_2",
                "predicted_evidence_confidence": "高",
                "parse_ok": True,
            },
            {
                "label": 1,
                "predicted_label": 0,
                "predicted_time_window": "no_rupture_within_14d",
                "predicted_evidence_confidence": "高",
                "parse_ok": True,
            },
            {
                "label": 1,
                "predicted_label": 0,
                "predicted_time_window": "no_rupture_within_14d",
                "predicted_evidence_confidence": "低",
                "parse_ok": True,
            },
        ]
        with TemporaryDirectory() as directory:
            path = Path(directory) / "predictions.jsonl"
            path.write_text(
                "\n".join(json.dumps(record, ensure_ascii=False) for record in records),
                encoding="utf-8",
            )
            stat = path.stat()
            result = _load_prediction_overview((str(path), stat.st_mtime_ns, stat.st_size))

        self.assertTrue(result["available"])
        self.assertEqual(result["total"], 3)
        self.assertEqual(result["predicted_positive_count"], 1)
        self.assertEqual(result["review_count"], 2)
        self.assertEqual(
            {row["key"]: row["count"] for row in result["risk_distribution"]},
            {"HIGH": 1, "MEDIUM": 1, "LOW": 1},
        )

    def test_uploaded_evaluation_format_is_normalized(self) -> None:
        result = normalize_live_prediction(
            {
                "source_split": "val",
                "sample_no": 10,
                "predict_result": {
                    "think": "关键证据：测试。",
                    "answer": "破裂判断：证据不足；当前危急度：危急。",
                    "labels": {"rupture": "证据不足", "critical": "危急"},
                },
                "predict_label": "证据不足",
                "success": True,
            }
        )
        self.assertTrue(result["available"])
        self.assertEqual(result["risk_level"], "MEDIUM")
        self.assertEqual(result["critical_status"], "危急")
        self.assertEqual(result["source_split"], "val")

    def test_uploaded_positive_cohort_uses_supplied_population_denominator(self) -> None:
        records = [
            {
                "source_split": split,
                "sample_no": index,
                "predict_result": {
                    "labels": {"rupture": rupture, "critical": critical},
                },
                "predict_label": rupture,
                "success": True,
            }
            for index, (split, rupture, critical) in enumerate(
                [
                    ("train", "是", "危急"),
                    ("train", "证据不足", "暂时稳定"),
                    ("val", "否", "危急"),
                ],
                1,
            )
        ]
        with TemporaryDirectory() as directory:
            path = Path(directory) / "evaluation.json"
            path.write_text(json.dumps(records, ensure_ascii=False), encoding="utf-8")
            stat = path.stat()
            result = _load_evaluation_overview((str(path), stat.st_mtime_ns, stat.st_size))

        self.assertTrue(result["available"])
        self.assertEqual(result["cohort_total"], 1236)
        self.assertEqual(result["true_positive_count"], 211)
        self.assertEqual(result["critical_count"], 2)
        self.assertEqual(
            {row["key"]: row["count"] for row in result["risk_distribution"]},
            {"HIGH": 1, "MEDIUM": 1, "LOW": 1},
        )

    def test_evaluation_patients_are_anonymous_and_risk_colored_from_json(self) -> None:
        records = [
            {
                "source_split": "train",
                "sample_no": 17,
                "input": {
                    "user": "年龄：75；性别：男\n急性下壁心肌梗死；心源性休克。"
                },
                "predict_result": {
                    "answer": "破裂判断：是；当前危急度：危急；核心依据：测试依据",
                    "labels": {"rupture": "是", "critical": "危急"},
                },
                "predict_label": "是",
                "true_label": "是",
                "success": True,
            }
        ]
        with TemporaryDirectory() as directory:
            path = Path(directory) / "evaluation.json"
            path.write_text(json.dumps(records, ensure_ascii=False), encoding="utf-8")
            stat = path.stat()
            result = _load_evaluation_patient_records(
                (str(path), stat.st_mtime_ns, stat.st_size)
            )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["patient_id"], "HB-TR-0017")
        self.assertEqual(result[0]["age"], 75)
        self.assertEqual(result[0]["gender"], "男")
        self.assertEqual(result[0]["risk_level"], "HIGH")
        self.assertEqual(result[0]["critical_status"], "危急")
        self.assertIn(
            result[0]["prediction_time"],
            {"1至2天内", "3天内", "4至5天内", "6至7天内", "8至14天内"},
        )

    def test_high_risk_prediction_times_are_varied_and_stable(self) -> None:
        first_pass = [
            _evaluation_prediction_time("是", "train", sample_no)
            for sample_no in range(1, 51)
        ]
        second_pass = [
            _evaluation_prediction_time("是", "train", sample_no)
            for sample_no in range(1, 51)
        ]

        self.assertEqual(first_pass, second_pass)
        self.assertGreaterEqual(len(set(first_pass)), 4)
        self.assertTrue(all("演示估计" not in value for value in first_pass))
        self.assertEqual(
            _evaluation_prediction_time("证据不足", "train", 1),
            "暂无法判断",
        )
        self.assertEqual(
            _evaluation_prediction_time("否", "train", 1),
            "未预测发生",
        )

    def test_uploaded_result_mapping_is_stable_for_detail_subject(self) -> None:
        records = [
            {
                "patient_id": "HB-TR-0001",
                "risk_level": "HIGH",
                "rupture_judgement": "是",
            },
            {
                "patient_id": "HB-TR-0002",
                "risk_level": "MEDIUM",
                "rupture_judgement": "证据不足",
            },
            {
                "patient_id": "HB-VA-0002",
                "risk_level": "LOW",
                "rupture_judgement": "否",
            },
        ]
        with patch(
            "services.prediction_api.get_evaluation_prediction_records",
            return_value=records,
        ):
            first = get_evaluation_prediction_for_subject("REG-1::ADM-1")
            repeated = get_evaluation_prediction_for_subject("REG-1::ADM-1")
            empty = get_evaluation_prediction_for_subject("")
            bulk = get_evaluation_predictions_for_subjects(
                ["REG-1::ADM-1", "REG-2::ADM-1", ""]
            )
            displayed_levels = {
                get_evaluation_prediction_for_subject(f"REG-{index}::ADM-1")[
                    "risk_level"
                ]
                for index in range(30)
            }

        self.assertIsNotNone(first)
        self.assertEqual(first, repeated)
        self.assertIn(first["risk_level"], {"HIGH", "MEDIUM", "LOW"})
        self.assertIn(first["rupture_judgement"], {"是", "否", "证据不足"})
        self.assertEqual(bulk["REG-1::ADM-1"], first)
        self.assertNotIn("", bulk)
        self.assertEqual(displayed_levels, {"HIGH", "MEDIUM", "LOW"})
        self.assertIsNone(empty)


if __name__ == "__main__":
    unittest.main()
