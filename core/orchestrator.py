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
	# Round 1 via LLM moderation: collect 3 outcomes per expert and pick distinct 4
	geo_json = ask_geo_expert(llm, scenario, debug=debug)
	econ_json = ask_econ_expert(llm, scenario, debug=debug)
	tech_json = ask_tech_expert(llm, scenario, debug=debug)
	social_json = ask_social_expert(llm, scenario, debug=debug)
	from core.schema import FinalSelection
	import json as _json
	level1_json = moderate_and_select(geo_json, econ_json, tech_json, social_json, scenario, llm=llm, debug=debug)
	fs: FinalSelection = FinalSelection(**_json.loads(level1_json))
	level1 = [TreeNode(expert=None, outcome=o.outcome, explanation=o.explanation, profit=o.profit) for o in fs.selected_outcomes]

	# Round 2: for each level-1, all 4 experts add one child, then LLM-moderate siblings
	for parent in level1:
		draft_children = [
			_ask_single(llm, "geo", f"Parent outcome: {parent.outcome}\nScenario: {scenario}", debug=debug),
			_ask_single(llm, "econ", f"Parent outcome: {parent.outcome}\nScenario: {scenario}", debug=debug),
			_ask_single(llm, "tech", f"Parent outcome: {parent.outcome}\nScenario: {scenario}", debug=debug),
			_ask_single(llm, "social", f"Parent outcome: {parent.outcome}\nScenario: {scenario}", debug=debug),
		]
		# LLM sibling moderation
		from json import dumps as _dumps, loads as _loads
		step_system = (
			"You moderate child outcomes for a parent. Remove or merge near-duplicates and anything that restates the parent. "
			"Return exactly 4 distinct children. Output only JSON: {\"children\":[{\"outcome\":\"...\",\"explanation\":\"...\"}]}"
		)
		step_user = f"Parent: {parent.outcome}\nCandidates: " + _dumps([{ "outcome": c.outcome, "explanation": c.explanation } for c in draft_children], ensure_ascii=False)
		resp = llm.invoke([("system", step_system), ("user", step_user)])
		try:
			mod_children = _loads(resp.content or "").get("children", [])
		except Exception:
			mod_children = [{ "outcome": c.outcome, "explanation": c.explanation } for c in draft_children]
		children = [TreeNode(expert=None, outcome=mc.get("outcome",""), explanation=mc.get("explanation","")) for mc in mod_children][:4]
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

