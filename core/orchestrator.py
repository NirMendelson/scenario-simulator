from __future__ import annotations

import json
from typing import List

from langchain_core.language_models.chat_models import BaseChatModel
from core.schema import TreeNode, TreeResult, Profit
from agents.profit_mapper import map_profit_for_outcome
from core.debug import debug_log

from agents.a2a import expert_propose, expert_critique, expert_revise, EXPERTS


def brainstorm_round(llm: BaseChatModel, scenario: str, debug: bool = False) -> str:
	# Produce 4 outcomes via A2A (no moderator)
	items = _run_a2a_round(llm, scenario, parent=None, debug=debug)
	from core.schema import FinalSelection, ExpertOutcome
	selected = [ExpertOutcome(outcome=i["outcome"], explanation=i["explanation"]) for i in items]
	return json.dumps(FinalSelection(scenario=scenario, selected_outcomes=selected).model_dump(), ensure_ascii=False, indent=2)



def _run_a2a_round(llm: BaseChatModel, scenario: str, parent: str | None, debug: bool = False, critique_rounds: int = 1) -> List[dict]:
	# Round 1: propose
	proposed: dict[str, dict] = {}
	for ex in EXPERTS:
		proposed[ex] = expert_propose(llm, ex, scenario, parent=parent, debug=debug)
	debug_log(debug, "A2A Proposed", json.dumps(proposed, ensure_ascii=False, indent=2))

	current = proposed
	for r in range(critique_rounds):
		# Critique
		critiques: dict[str, dict] = {}
		for ex in EXPERTS:
			peers = [{"expert": k, **v} for k, v in current.items() if k != ex]
			critiques[ex] = expert_critique(llm, ex, scenario, my_outcome=current[ex], peer_outcomes=peers, parent=parent, debug=debug)
		debug_log(debug, f"A2A Critiques R{r+1}", json.dumps(critiques, ensure_ascii=False, indent=2))

		# Revise
		all_list = [{"expert": k, **v} for k, v in current.items()]
		revised: dict[str, dict] = {}
		for ex in EXPERTS:
			revised[ex] = expert_revise(llm, ex, scenario, all_outcomes=all_list, critiques=critiques.get(ex, {}), parent=parent, debug=debug)
		current = revised
		debug_log(debug, f"A2A Revised R{r+1}", json.dumps(current, ensure_ascii=False, indent=2))

	# Return list in stable expert order
	return [current[ex] for ex in EXPERTS]



def build_two_round_tree(llm: BaseChatModel, scenario: str, debug: bool = False) -> str:
	# Level 1 via A2A
	items_l1 = _run_a2a_round(llm, scenario, parent=None, debug=debug, critique_rounds=1)
	level1: List[TreeNode] = [
		TreeNode(expert=None, outcome=i["outcome"], explanation=i["explanation"], children=[])
		for i in items_l1
	]

	# Profit mapping for level 1 nodes
	for node in level1:
		p = map_profit_for_outcome(llm, node.outcome, debug=debug)
		try:
			node.profit = p if isinstance(p, Profit) else Profit(**p)
		except Exception:
			pass

	# Level 2 via A2A per parent + profit mapping
	for parent in level1:
		items_l2 = _run_a2a_round(llm, scenario, parent=parent.outcome, debug=debug, critique_rounds=1)
		children: List[TreeNode] = []
		for i in items_l2:
			leaf = TreeNode(expert=None, outcome=i["outcome"], explanation=i["explanation"], children=[])
			p = map_profit_for_outcome(llm, leaf.outcome, debug=debug)
			try:
				leaf.profit = p if isinstance(p, Profit) else Profit(**p)
			except Exception:
				pass
			children.append(leaf)
		parent.children = children

	result = TreeResult(scenario=scenario, children=level1)
	text = json.dumps(result.model_dump(), ensure_ascii=False, indent=2)
	debug_log(debug, "Two-Round Tree", text)
	return text

