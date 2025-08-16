from __future__ import annotations

import json
from typing import List

from langchain_core.language_models.chat_models import BaseChatModel
from core.schema import TreeNode, TreeResult, Profit
from agents.profit_mapper import map_profit_for_outcome
from core.debug import debug_log

from agents.geo_expert import ask_geo_expert
from agents.econ_expert import ask_econ_expert
from agents.tech_expert import ask_tech_expert
from agents.social_expert import ask_social_expert
from agents.moderator import moderate_and_select


def brainstorm_round(llm: BaseChatModel, scenario: str, debug: bool = False) -> str:
	geo_json = ask_geo_expert(llm, scenario, debug=debug)
	econ_json = ask_econ_expert(llm, scenario, debug=debug)
	tech_json = ask_tech_expert(llm, scenario, debug=debug)
	social_json = ask_social_expert(llm, scenario, debug=debug)
	final_json = moderate_and_select(geo_json, econ_json, tech_json, social_json, scenario, llm=llm, debug=debug)
	return final_json



def _ask_single(llm: BaseChatModel, expert: str, prompt_context: str, debug: bool = False) -> TreeNode:
	assert expert in {"geo", "econ", "tech", "social"}
	titles = {
		"geo": "geopolitical history analyst",
		"econ": "economic history analyst",
		"tech": "technology analyst",
		"social": "social dynamics analyst",
	}
	system = (
		f"You are a {titles[expert]} producing neutral, policy-compliant text. "
		"Read the context and propose exactly 1 distinct outcome. Return JSON only with this schema: "
		"{\"expert\":\"geo|econ|tech|social\",\"outcome\":\"...\", \"explanation\":\"...\"}\n"
		"Rules:\n- outcome: ONE short sentence, present tense, simple words.\n- explanation: ONE sentence, 18–40 words.\n- No probabilities/citations/extra fields; short or medium horizon."
	)
	user = f"Expert: {expert}\nContext: {prompt_context}\nReturn only the JSON."
	debug_log(debug, f"{expert.upper()} Single Prompt", f"SYSTEM:\n{system}\n\nUSER:\n{user}")
	resp = llm.invoke([("system", system), ("user", user)])
	text = (resp.content or "").strip()
	debug_log(debug, f"{expert.upper()} Single Response", text)
	# permissive parse
	import json as _json
	data = _json.loads(text)
	return TreeNode(
		expert=expert, outcome=str(data.get("outcome", "")).strip(), explanation=str(data.get("explanation", "")).strip(), children=[]
	)


def build_two_round_tree(llm: BaseChatModel, scenario: str, debug: bool = False) -> str:
	# Round 1: one suggestion per expert
	level1 = [
		_ask_single(llm, "geo", scenario, debug=debug),
		_ask_single(llm, "econ", scenario, debug=debug),
		_ask_single(llm, "tech", scenario, debug=debug),
		_ask_single(llm, "social", scenario, debug=debug),
	]

	# Profit map level-1 as well
	for parent in level1:
		p = map_profit_for_outcome(llm, parent.outcome, debug=debug)
		try:
			parent.profit = p if isinstance(p, Profit) else Profit(**p)
		except Exception:
			pass

	# Round 2: for each level-1, all 4 experts add one child
	for parent in level1:
		children = [
			_ask_single(llm, "geo", f"Parent outcome: {parent.outcome}\nScenario: {scenario}", debug=debug),
			_ask_single(llm, "econ", f"Parent outcome: {parent.outcome}\nScenario: {scenario}", debug=debug),
			_ask_single(llm, "tech", f"Parent outcome: {parent.outcome}\nScenario: {scenario}", debug=debug),
			_ask_single(llm, "social", f"Parent outcome: {parent.outcome}\nScenario: {scenario}", debug=debug),
		]
		# Profit map each leaf
		for leaf in children:
			p = map_profit_for_outcome(llm, leaf.outcome, debug=debug)
			try:
				leaf.profit = p if isinstance(p, Profit) else Profit(**p)
			except Exception:
				pass
		parent.children = children

	result = TreeResult(scenario=scenario, children=level1)
	text = json.dumps(result.model_dump(), ensure_ascii=False, indent=2)
	debug_log(debug, "Two-Round Tree", text)
	return text

