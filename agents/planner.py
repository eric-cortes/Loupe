"""Planner agent: translates a creative brief into search_archive tool
calls and gathers candidate matches. It does not write the final answer —
that's the curator agent's job (agents/curator.py); this agent's only
concern is search strategy.
"""
from __future__ import annotations

import json

from langchain.agents import create_agent
from langchain_core.messages import AIMessage, ToolMessage
from langchain_openai import ChatOpenAI

from agents.search_tool import search_archive

SYSTEM_PROMPT = """You are the search planner for an editorial and \
documentary photo archive.

Users describe an editorial or creative need in plain language — a campaign \
brief, a mood, a story they're building — not a literal search string. \
Examples: "we need images for a travel campaign, warm tones should dominate", \
"something intimate and quiet to close a photo essay", "high-energy street \
shots, vertical, for an Instagram carousel".

Your only job is to translate that brief into the search_archive tool's \
structured arguments and run the search:
- semantic_query: a dense visual/mood description for embedding similarity \
  (colors, subject, energy, composition) — translate abstract concepts into \
  concrete visual language (e.g. "travel" + "warm tones" -> "golden hour \
  street scene, warm light, market stalls, crowd energy").
- collection / keyword: use these if the brief maps to something specific \
  the archive actually has.
- min_rating, camera_model, capture_year: only if the user specifies them.

Call the tool as many times as useful — try a few phrasings or filter \
combinations if the first attempt returns little. Once you have a good set \
of candidate matches (or you've genuinely exhausted useful search \
strategies), stop calling tools and reply with a one-line note on what you \
searched for. Do not describe, evaluate, or recommend individual images —
that is the curator's job, not yours."""


def build_planner_agent():
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    return create_agent(llm, tools=[search_archive], system_prompt=SYSTEM_PROMPT)


def plan_and_search(messages: list[dict]) -> dict:
    """Run the planner over a conversation (optionally with a trailing
    refinement instruction appended) and return the structured tool calls
    made plus the deduplicated matches retrieved.
    """
    agent = build_planner_agent()
    result = agent.invoke({"messages": messages})
    result_messages = result["messages"]

    structured_calls = []
    matches_by_id: dict[int, dict] = {}
    for msg in result_messages:
        if isinstance(msg, AIMessage) and msg.tool_calls:
            structured_calls.extend(tc["args"] for tc in msg.tool_calls)
        if isinstance(msg, ToolMessage):
            try:
                for m in json.loads(msg.content):
                    matches_by_id[m["id"]] = m
            except (json.JSONDecodeError, TypeError):
                pass

    return {"structured_calls": structured_calls, "matches": list(matches_by_id.values())}
