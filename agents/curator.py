"""Curator agent: takes the brief and the planner's retrieved matches and
writes a grounded, conversational answer — or, if the matches are too thin
to say anything useful, asks the planner to refine its search instead of
guessing.
"""
from __future__ import annotations

import json

from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

SYSTEM_PROMPT = """You are a curator's assistant for an editorial and \
documentary photo archive. You do not search the archive yourself — a \
planner agent has already run a search and handed you its candidate \
matches as JSON.

Answer conversationally, grounded ONLY in the matches you were given: cite \
specific frames by file path, describe what's actually there, and if the \
brief calls for something the matches don't cover, say so honestly rather \
than inventing detail.

If the matches are too thin or off-target to say anything useful (e.g. \
empty, or clearly the wrong kind of shot), set sufficient=false and give \
concrete refinement_instructions the planner should try next (a better \
semantic_query phrasing, a different keyword/collection filter, a dropped \
constraint, etc.) instead of writing an answer."""


class CuratorVerdict(BaseModel):
    sufficient: bool = Field(
        description="True if the matches are enough to answer the brief."
    )
    answer: str | None = Field(
        default=None, description="The grounded, conversational answer, if sufficient."
    )
    refinement_instructions: str | None = Field(
        default=None,
        description="What the planner should try differently, if not sufficient.",
    )


def build_curator_agent():
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    return llm.with_structured_output(CuratorVerdict)


def curate(messages: list[dict], matches: list[dict]) -> CuratorVerdict:
    agent = build_curator_agent()
    prompt = (
        f"Conversation so far:\n{json.dumps(messages, indent=2)}\n\n"
        f"Matches returned by the planner's search:\n{json.dumps(matches, indent=2)}"
    )
    return agent.invoke(
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]
    )
