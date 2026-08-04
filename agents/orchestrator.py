"""Two-agent pipeline: a planner agent (agents/planner.py) turns a creative
brief into archive searches, a curator agent (agents/curator.py) turns
those results into a grounded answer — and can hand control back to the
planner once if the first pass came back too thin, instead of either agent
guessing on its own.
"""
from __future__ import annotations

from agents.curator import curate
from agents.planner import plan_and_search

MAX_REFINEMENT_ROUNDS = 1


def run_conversation(messages: list[dict]) -> dict:
    """Run the planner -> curator pipeline on a full conversation (list of
    {role, content} dicts, roles "user"/"assistant") and return the new
    assistant answer plus the structured tool calls and matches gathered
    along the way, for a "query inspector" view in the UI.
    """
    planner_messages = list(messages)
    structured_calls: list[dict] = []
    matches: list[dict] = []
    answer = "I couldn't find enough in the archive to answer that."

    for round_num in range(MAX_REFINEMENT_ROUNDS + 1):
        plan_result = plan_and_search(planner_messages)
        structured_calls.extend(plan_result["structured_calls"])
        matches = plan_result["matches"]

        verdict = curate(messages, matches)
        if verdict.sufficient or round_num == MAX_REFINEMENT_ROUNDS:
            if verdict.answer:
                answer = verdict.answer
            break

        planner_messages = planner_messages + [
            {
                "role": "user",
                "content": f"Refine the search: {verdict.refinement_instructions}",
            }
        ]

    return {
        "answer": answer,
        "structured_calls": structured_calls,
        "matches": matches,
    }


if __name__ == "__main__":
    import json
    import sys

    query = " ".join(sys.argv[1:]) or "we need images for a travel campaign, warm tones should dominate"
    result = run_conversation([{"role": "user", "content": query}])
    print("QUERY:", query)
    print("\nSTRUCTURED CALLS:")
    print(json.dumps(result["structured_calls"], indent=2))
    print(f"\nMATCHES: {len(result['matches'])}")
    for m in result["matches"][:5]:
        print(" -", m["file_path"], "|", m.get("caption") or "(no caption)")
    print("\nANSWER:\n", result["answer"])
