from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from services.chat_store import (
    append_chat_message,
    clear_chat_feed,
    clear_encounter_chat,
    load_chat_feed,
    load_encounter_chat,
)


class EncounterChatStoreTests(unittest.TestCase):
    def test_real_rupture_cohort_samples_are_ordered_first(self) -> None:
        from views.clinical_agent import _ordered_encounter_keys

        encounters = {
            "sample-negative-2": {"cohort_label": 0},
            "sample-positive-2": {"cohort_label": 1},
            "sample-negative-1": {"cohort_label": 0},
            "sample-positive-1": {"cohort_label": 1},
        }

        self.assertEqual(
            _ordered_encounter_keys(encounters),
            [
                "sample-positive-1",
                "sample-positive-2",
                "sample-negative-1",
                "sample-negative-2",
            ],
        )

    def test_only_latest_one_hundred_messages_are_persisted(self) -> None:
        with TemporaryDirectory() as directory:
            database_path = Path(directory) / "chat.db"
            for index in range(105):
                append_chat_message(
                    "REG-1::ADM-1",
                    {"role": "user", "content": f"消息 {index}"},
                    database_path=database_path,
                )

            messages = load_encounter_chat(
                "REG-1::ADM-1", database_path=database_path
            )
            self.assertEqual(len(messages), 100)
            self.assertEqual(messages[0]["content"], "消息 5")
            self.assertEqual(messages[-1]["content"], "消息 104")

    def test_encounter_key_is_normalized_at_database_boundary(self) -> None:
        with TemporaryDirectory() as directory:
            database_path = Path(directory) / "chat.db"
            append_chat_message(
                "  REG-1::ADM-1  ",
                {"role": "user", "content": "这是一条真实记录"},
                database_path=database_path,
            )

            messages = load_encounter_chat(
                "REG-1::ADM-1", database_path=database_path
            )
            self.assertEqual([item["content"] for item in messages], ["这是一条真实记录"])

            clear_encounter_chat(" REG-1::ADM-1 ", database_path=database_path)
            self.assertEqual(
                load_encounter_chat("REG-1::ADM-1", database_path=database_path),
                [],
            )

    def test_messages_are_isolated_ordered_and_clearable(self) -> None:
        with TemporaryDirectory() as directory:
            database_path = Path(directory) / "chat.db"
            append_chat_message(
                "REG-1::ADM-1",
                {"role": "user", "content": "请汇总当前就诊。"},
                database_path=database_path,
            )
            append_chat_message(
                "REG-1::ADM-1",
                {
                    "role": "assistant",
                    "content": "已完成汇总。",
                    "trace": [{"tool": "extract_clinical_features"}],
                },
                database_path=database_path,
            )
            append_chat_message(
                "REG-2::ADM-1",
                {"role": "user", "content": "另一名患者。"},
                database_path=database_path,
            )

            messages = load_encounter_chat(
                "REG-1::ADM-1", database_path=database_path
            )
            self.assertEqual([item["role"] for item in messages], ["user", "assistant"])
            self.assertEqual(messages[1]["trace"][0]["tool"], "extract_clinical_features")

            clear_encounter_chat("REG-1::ADM-1", database_path=database_path)
            self.assertEqual(
                load_encounter_chat("REG-1::ADM-1", database_path=database_path),
                [],
            )
            self.assertEqual(
                len(load_encounter_chat("REG-2::ADM-1", database_path=database_path)),
                1,
            )

    def test_ui_feed_keeps_messages_from_all_encounters_in_order(self) -> None:
        with TemporaryDirectory() as directory:
            database_path = Path(directory) / "chat.db"
            append_chat_message(
                "REG-1::ADM-1",
                {"role": "user", "content": "患者一的问题"},
                database_path=database_path,
            )
            append_chat_message(
                "REG-1::ADM-1",
                {"role": "assistant", "content": "患者一的回答"},
                database_path=database_path,
            )
            append_chat_message(
                "REG-2::ADM-2",
                {"role": "user", "content": "患者二的问题"},
                database_path=database_path,
            )

            feed = load_chat_feed(database_path=database_path)

            self.assertEqual(
                [item["content"] for item in feed],
                ["患者一的问题", "患者一的回答", "患者二的问题"],
            )
            self.assertEqual(
                [item["encounter_key"] for item in feed],
                ["REG-1::ADM-1", "REG-1::ADM-1", "REG-2::ADM-2"],
            )

    def test_complete_feed_is_only_deleted_by_explicit_clear(self) -> None:
        with TemporaryDirectory() as directory:
            database_path = Path(directory) / "chat.db"
            append_chat_message(
                "REG-1::ADM-1",
                {"role": "user", "content": "患者一的问题"},
                database_path=database_path,
            )
            append_chat_message(
                "REG-2::ADM-2",
                {"role": "assistant", "content": "患者二的回答"},
                database_path=database_path,
            )

            self.assertEqual(len(load_chat_feed(database_path=database_path)), 2)
            clear_chat_feed(database_path=database_path)

            self.assertEqual(load_chat_feed(database_path=database_path), [])
            self.assertEqual(
                load_encounter_chat("REG-1::ADM-1", database_path=database_path),
                [],
            )

    def test_switching_back_reuses_each_encounters_session_memory(self) -> None:
        from views.clinical_agent import _encounter_history

        state: dict = {"chat_history": {}}
        stored = {
            "REG-1::ADM-1": [{"role": "user", "content": "患者一的问题"}],
            "REG-2::ADM-1": [{"role": "user", "content": "患者二的问题"}],
        }
        fake_streamlit = SimpleNamespace(session_state=state)
        with (
            patch("views.clinical_agent.st", fake_streamlit),
            patch(
                "views.clinical_agent.load_encounter_chat",
                side_effect=lambda key: list(stored[key]),
            ) as loader,
        ):
            first_history = _encounter_history("REG-1::ADM-1")
            self.assertEqual(first_history, stored["REG-1::ADM-1"])
            first_history.append(
                {"role": "assistant", "content": "患者一的回答已保存在当前会话"}
            )
            self.assertEqual(_encounter_history("REG-2::ADM-1"), stored["REG-2::ADM-1"])
            self.assertEqual(
                _encounter_history("REG-1::ADM-1")[-1]["content"],
                "患者一的回答已保存在当前会话",
            )

        self.assertEqual(loader.call_count, 2)
        self.assertEqual(
            [item["content"] for item in state["chat_history"]["REG-1::ADM-1"]],
            ["患者一的问题", "患者一的回答已保存在当前会话"],
        )
        self.assertEqual(
            [item["content"] for item in state["chat_history"]["REG-2::ADM-1"]],
            ["患者二的问题"],
        )

    def test_new_question_keeps_prior_history_for_the_agent(self) -> None:
        from views.clinical_agent import _submit_question

        state: dict = {
            "chat_history": {
                "REG-1::ADM-1": [
                    {"role": "user", "content": "上一轮问题"},
                    {"role": "assistant", "content": "上一轮回答"},
                ]
            },
            "pending_agent_questions": {},
        }
        fake_streamlit = SimpleNamespace(session_state=state)
        with (
            patch("views.clinical_agent.st", fake_streamlit),
            patch("views.clinical_agent.append_chat_message") as writer,
            patch("views.clinical_agent.load_chat_feed", return_value=[]),
        ):
            _submit_question("REG-1::ADM-1", "继续核对检查结果")

        pending = state["pending_agent_questions"]["REG-1::ADM-1"]
        self.assertEqual(
            [item["content"] for item in pending["history"]],
            ["上一轮问题", "上一轮回答"],
        )
        self.assertEqual(
            state["chat_history"]["REG-1::ADM-1"][-1]["content"],
            "继续核对检查结果",
        )
        writer.assert_called_once_with(
            "REG-1::ADM-1",
            {"role": "user", "content": "继续核对检查结果"},
        )
        self.assertEqual(
            state["agent_chat_transcript"][-1]["encounter_key"],
            "REG-1::ADM-1",
        )

    def test_clear_removes_only_current_encounter_from_cache_and_database(self) -> None:
        from views.clinical_agent import _clear_history

        state: dict = {
            "chat_history": {
                "REG-1::ADM-1": [{"role": "user", "content": "患者一"}],
                "REG-2::ADM-2": [{"role": "user", "content": "患者二"}],
            },
            "pending_agent_questions": {"REG-1::ADM-1": {"question": "患者一"}},
            "agent_chat_transcript": [
                {
                    "role": "user",
                    "content": "患者一",
                    "encounter_key": "REG-1::ADM-1",
                },
                {
                    "role": "user",
                    "content": "患者二",
                    "encounter_key": "REG-2::ADM-2",
                },
            ],
        }
        fake_streamlit = SimpleNamespace(session_state=state)
        with (
            patch("views.clinical_agent.st", fake_streamlit),
            patch("views.clinical_agent.clear_encounter_chat") as clearer,
        ):
            _clear_history("REG-1::ADM-1")

        self.assertEqual(state["chat_history"]["REG-1::ADM-1"], [])
        self.assertNotIn("REG-1::ADM-1", state["pending_agent_questions"])
        self.assertEqual(
            [item["encounter_key"] for item in state["agent_chat_transcript"]],
            ["REG-2::ADM-2"],
        )
        clearer.assert_called_once_with("REG-1::ADM-1")

    def test_clear_transcript_resets_all_chat_state_and_persistent_feed(self) -> None:
        from views.clinical_agent import _clear_chat_transcript

        state: dict = {
            "chat_history": {
                "REG-1::ADM-1": [{"role": "user", "content": "患者一"}],
                "REG-2::ADM-2": [{"role": "assistant", "content": "患者二"}],
            },
            "pending_agent_questions": {
                "REG-1::ADM-1": {"question": "待处理问题"}
            },
            "agent_chat_transcript": [
                {
                    "role": "user",
                    "content": "患者一",
                    "encounter_key": "REG-1::ADM-1",
                }
            ],
        }
        fake_streamlit = SimpleNamespace(session_state=state)
        with (
            patch("views.clinical_agent.st", fake_streamlit),
            patch("views.clinical_agent.clear_chat_feed") as clearer,
        ):
            _clear_chat_transcript()

        self.assertEqual(state["chat_history"], {})
        self.assertEqual(state["pending_agent_questions"], {})
        self.assertEqual(state["agent_chat_transcript"], [])
        clearer.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
