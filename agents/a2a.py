from __future__ import annotations

import json
from typing import Dict, List, Optional

from langchain_core.language_models.chat_models import BaseChatModel
from core.debug import debug_log

EXPERTS: List[str] = ["geo", "econ", "tech", "social"]


def _expert_label(expert: str) -> str:
	labels = {"geo": "Geopolitics", "econ": "Economy", "tech": "Technology", "social": "Society"}
	return labels.get(expert, expert)


def expert_propose(
	llm: BaseChatModel,
	expert: str,
	scenario: str,
	parent: Optional[str] = None,
	debug: bool = False,
) -> Dict:
	scope = f"Scenario: {scenario}" if not parent else f"Scenario: {scenario}\nParent outcome: {parent}"
	system = f"""
You are the {_expert_label(expert)} expert. Propose ONE outcome.
Constraints:
- outcome: <= 14 words, present tense, simple words, no hedging words (may/might/could), no vague phrases.
- Be SPECIFIC: name concrete actors, places, instruments, or policies when possible.
- make sure to not suggest a restatement or trivial follow-on, it should be a step forward but one that make sense why its the outcome of the parent.
- explanation: ONE sentence, 18–40 words, plain language.
Return ONLY JSON: {{"outcome":"...","explanation":"..."}}
"""
	user = scope
	resp = llm.invoke([("system", system), ("user", user)])
	text = (resp.content or "").strip()
	debug_log(debug, f"A2A {expert} PROPOSE raw", text)
	return json.loads(text)


def expert_critique(
	llm: BaseChatModel,
	expert: str,
	scenario: str,
	my_outcome: Dict,
	peer_outcomes: List[Dict],
	parent: Optional[str] = None,
	debug: bool = False,
) -> Dict:
	scope = {"scenario": scenario, "parent": parent, "mine": my_outcome, "peers": peer_outcomes}
	system = f"""
You are the {_expert_label(expert)} expert. Briefly critique peers and flag overlaps or restatements of the parent.
Rules:
- Keep it short and actionable.
- Max 3 notes.
Return ONLY JSON: {{"notes":[{{"target":"geo|econ|tech|social","issue":"overlap|vague|small-step","tip":"<= 14 words"}}]}}
"""
	resp = llm.invoke([("system", system), ("user", json.dumps(scope, ensure_ascii=False))])
	text = (resp.content or "").strip()
	debug_log(debug, f"A2A {expert} CRITIQUE raw", text)
	return json.loads(text)


def expert_revise(
	llm: BaseChatModel,
	expert: str,
	scenario: str,
	all_outcomes: List[Dict],
	critiques: Dict,
	parent: Optional[str] = None,
	debug: bool = False,
) -> Dict:
	payload = {
		"scenario": scenario,
		"parent": parent,
		"all_outcomes": all_outcomes,
		"critiques": critiques,
	}
	system = f"""
You are the {_expert_label(expert)} expert. REVISE your own outcome.
Requirements:
- Make it DISTINCT from peers.
- Make it SPECIFIC (concrete actors/places/instruments/policies).
- Make it a BIG STEP beyond the parent if parent is given.
- Keep constraints: outcome <= 14 words, present tense, plain words; explanation single sentence 18–40 words.
- Do not restate the parent; avoid vague language.
Return ONLY JSON: {{"outcome":"...","explanation":"..."}}
"""
	resp = llm.invoke([("system", system), ("user", json.dumps(payload, ensure_ascii=False))])
	text = (resp.content or "").strip()
	debug_log(debug, f"A2A {expert} REVISE raw", text)
	return json.loads(text)


