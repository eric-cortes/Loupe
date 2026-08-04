"""Exercises the planner -> curator handoff logic in isolation, mocking
both agents so this runs in CI without an OpenAI key or a database.
"""
from __future__ import annotations

from unittest.mock import patch

from agents.curator import CuratorVerdict
from agents.orchestrator import run_conversation

MATCH = {"id": 1, "file_path": "/a.jpg", "caption": "a photo"}


def test_returns_curator_answer_when_first_pass_is_sufficient():
    with (
        patch("agents.orchestrator.plan_and_search") as plan_and_search,
        patch("agents.orchestrator.curate") as curate,
    ):
        plan_and_search.return_value = {"structured_calls": [{"semantic_query": "a"}], "matches": [MATCH]}
        curate.return_value = CuratorVerdict(sufficient=True, answer="Here's what I found.")

        result = run_conversation([{"role": "user", "content": "find me something"}])

        assert result["answer"] == "Here's what I found."
        assert result["matches"] == [MATCH]
        assert plan_and_search.call_count == 1
        assert curate.call_count == 1


def test_asks_planner_to_refine_once_when_matches_are_thin():
    with (
        patch("agents.orchestrator.plan_and_search") as plan_and_search,
        patch("agents.orchestrator.curate") as curate,
    ):
        plan_and_search.side_effect = [
            {"structured_calls": [{"semantic_query": "a"}], "matches": []},
            {"structured_calls": [{"semantic_query": "b"}], "matches": [MATCH]},
        ]
        curate.side_effect = [
            CuratorVerdict(sufficient=False, refinement_instructions="try a broader query"),
            CuratorVerdict(sufficient=True, answer="Found it on the second try."),
        ]

        result = run_conversation([{"role": "user", "content": "find me something"}])

        assert result["answer"] == "Found it on the second try."
        assert plan_and_search.call_count == 2
        assert curate.call_count == 2

        second_call_messages = plan_and_search.call_args_list[1].args[0]
        assert "try a broader query" in second_call_messages[-1]["content"]


def test_gives_up_honestly_after_max_refinement_rounds():
    with (
        patch("agents.orchestrator.plan_and_search") as plan_and_search,
        patch("agents.orchestrator.curate") as curate,
    ):
        plan_and_search.return_value = {"structured_calls": [], "matches": []}
        curate.return_value = CuratorVerdict(sufficient=False, refinement_instructions="nothing helped")

        result = run_conversation([{"role": "user", "content": "find me something"}])

        assert "couldn't find enough" in result["answer"]
        assert plan_and_search.call_count == 2
        assert curate.call_count == 2
