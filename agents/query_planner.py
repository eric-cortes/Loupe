"""Curator chat agent: a creative brief, in conversation, -> structured
archive search -> grounded answer.

The point of the LLM here isn't keyword lookup — it's translating a fuzzy
editorial brief ("a moody travel piece, cool tones, mostly wide shots") into
concrete search_archive arguments (semantic_query text, and any relevant
collection/keyword the archive actually has), and doing it conversationally
so the user can refine ("more candid, less posed") across turns.
"""
from __future__ import annotations

import json
import sys

from langchain.agents import create_agent
from langchain_core.messages import AIMessage, ToolMessage
from langchain_openai import ChatOpenAI

from agents.search_tool import search_archive

SYSTEM_PROMPT = """You are a curator's assistant for an editorial and \
documentary photo archive.

Users describe an editorial or creative need in plain language — a campaign \
brief, a mood, a story they're building — not a literal search string. \
Examples: "we need images for a travel campaign, warm tones should dominate", \
"something intimate and quiet to close a photo essay", "high-energy street \
shots, vertical, for an Instagram carousel".

Your job is to translate that brief into the search_archive tool's structured \
arguments:
- semantic_query: a dense visual/mood description for embedding similarity \
  (colors, subject, energy, composition) — translate abstract concepts into \
  concrete visual language (e.g. "travel" + "warm tones" -> "golden hour \
  street scene, warm light, market stalls, crowd energy").
- collection / keyword: use these if the brief maps to something specific \
  the archive actually has.
- min_rating, camera_model, capture_year: only if the user specifies them.

Call the tool as many times as useful — try a few phrasings or filter \
combinations if the first attempt returns little. Then respond \
conversationally: explain what you searched for and why, describe what you \
found grounded ONLY in the returned data (cite specific frames by file path), \
and if the results are thin, say so and suggest what would help (e.g. "that \
collection has few captions — here's what's tagged there"). This is a \
conversation: ask a clarifying question if the brief is \
too vague to search meaningfully, and take earlier turns into account when \
the user refines their ask."""


def build_agent():
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    return create_agent(llm, tools=[search_archive], system_prompt=SYSTEM_PROMPT)


def run_conversation(messages: list[dict]) -> dict:
    """Run the agent on a full conversation (list of {role, content} dicts,
    roles "user"/"assistant") and return the new assistant answer plus the
    structured tool calls and matches from this turn, for a "query inspector"
    view in the UI.
    """
    agent = build_agent()
    result = agent.invoke({"messages": messages})
    result_messages = result["messages"]

    structured_calls = []
    matches = []
    for msg in result_messages:
        if isinstance(msg, AIMessage) and msg.tool_calls:
            structured_calls.extend(tc["args"] for tc in msg.tool_calls)
        if isinstance(msg, ToolMessage):
            try:
                matches.extend(json.loads(msg.content))
            except (json.JSONDecodeError, TypeError):
                pass

    final_answer = result_messages[-1].content if result_messages else ""

    return {
        "answer": final_answer,
        "structured_calls": structured_calls,
        "matches": matches,
    }


if __name__ == "__main__":
    query = " ".join(sys.argv[1:]) or "we need images for a travel campaign, warm tones should dominate"
    result = run_conversation([{"role": "user", "content": query}])
    print("QUERY:", query)
    print("\nSTRUCTURED CALLS:")
    print(json.dumps(result["structured_calls"], indent=2))
    print(f"\nMATCHES: {len(result['matches'])}")
    for m in result["matches"][:5]:
        print(" -", m["file_path"], "|", m.get("caption") or "(no caption)")
    print("\nANSWER:\n", result["answer"])
