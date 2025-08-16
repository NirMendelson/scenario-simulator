from __future__ import annotations

import json
from typing import List

from langchain_core.language_models.chat_models import BaseChatModel

from agents.geo_expert import ask_geo_expert
from agents.econ_expert import ask_econ_expert
from agents.tech_expert import ask_tech_expert
from agents.social_expert import ask_social_expert
from agents.profit_mapper import map_profit_for_outcome
from core.schema import Profit, TreeNode, TreeResult


def _parse_single(raw: str, expected: str) -> dict:
	import json as _json
	data = _json.loads(raw)
	if not isinstance(data, dict) or data.get("expert") != expected:
		raise ValueError("invalid expert json")
	return {"expert": expected, "outcome": data["outcome"], "explanation": data["explanation"]}


def _build_children(llm: BaseChatModel, scenario: str, debug: bool) -> List[TreeNode]:
	# Round 1: each expert returns one
	geo = _parse_single(ask_geo_expert(llm, scenario, debug=debug).strip(), "geo")
	econ = _parse_single(ask_econ_expert(llm, scenario, debug=debug).strip(), "econ")
	tech = _parse_single(ask_tech_expert(llm, scenario, debug=debug).strip(), "tech")
	social = _parse_single(ask_social_expert(llm, scenario, debug=debug).strip(), "social")
	level1 = [geo, econ, tech, social]

	# Round 2: for each of level1, run all four experts again
	result_nodes: List[TreeNode] = []
	for n in level1:
		children: List[TreeNode] = []
		base = n["outcome"]
		for exp, fn in [
			("geo", ask_geo_expert),
			("econ", ask_econ_expert),
			("tech", ask_tech_expert),
			("social", ask_social_expert),
		]:
			sub = _parse_single(fn(llm, base, debug=debug).strip(), exp)
			p = map_profit_for_outcome(llm, sub["outcome"], debug=debug)
			children.append(TreeNode(expert=exp, outcome=sub["outcome"], explanation=sub["explanation"], profit=Profit(**p), children=[]))
		result_nodes.append(
			TreeNode(
				expert=n["expert"],
				outcome=n["outcome"],
				explanation=n["explanation"],
				profit=None,
				children=children,
			)
		)
	return result_nodes


def brainstorm_round(llm: BaseChatModel, scenario: str, debug: bool = False) -> str:
	children = _build_children(llm, scenario, debug)
	tree = TreeResult(scenario=scenario, children=children)
	return json.dumps(tree.model_dump(), ensure_ascii=False, indent=2)


