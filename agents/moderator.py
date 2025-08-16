from __future__ import annotations

import json
import re
from typing import Dict, List, Tuple

from core.debug import debug_log
from core.schema import ExpertOutcome, ExpertResponse, FinalSelection, Profit
from agents.profit_mapper import map_profit_for_outcome
from langchain_core.language_models.chat_models import BaseChatModel

STOPWORDS = {
	"the","a","an","and","or","to","of","in","on","for","by","with","from","as","at","into","that","this","these","those"
}

THEMES = {
	"military": ["military", "troop", "naval", "missile", "standoff", "strike", "coup"],
	"sanctions_trade": ["tariff", "sanction", "export", "import", "quota", "trade"],
	"energy": ["oil", "gas", "energy", "grid", "refinery", "opec"],
	"finance_markets": ["bond", "equity", "cpi", "ppi", "inflation", "rate", "market", "index"],
	"migration": ["migrant", "refugee", "deport"],
	"public_health": ["virus", "outbreak", "health", "mortality"],
	"tech_cyber": ["semiconductor", "chip", "ai", "cyber", "quantum", "cloud"],
}

# Finer-grained subthemes to prevent near-duplicate selections
SUBTHEMES = {
	"user_shift": [
		"users", "user", "switch", "migrate", "migration", "adopt", "adoption", "move",
		"platform", "platforms", "apps", "gain users", "user growth", "more users",
	],
	"regulation_policy": ["regulatory", "policy", "ban", "restriction", "law", "rule", "incentive"],
	"protest_social": ["protest", "rally", "demonstration", "social", "public", "backlash"],
}


def _normalize(text: str) -> str:
	text = text.lower()
	text = re.sub(r"\d+|\b\d{1,2}\s*(months?|years?)\b", " ", text)
	text = re.sub(r"[^a-z\s]", " ", text)
	words = [w for w in text.split() if w not in STOPWORDS]
	return " ".join(words)


def _theme_bucket(text: str) -> str:
	lt = text.lower()
	for theme, kws in THEMES.items():
		if any(kw in lt for kw in kws):
			return theme
	return "other"


def _subtheme_bucket(text: str) -> str:
	lt = text.lower()
	for sub, kws in SUBTHEMES.items():
		if any(kw in lt for kw in kws):
			return sub
	return "other"


def _tokens(text: str) -> set:
	# very light stemming
	words = _normalize(text).split()
	stem = []
	for w in words:
		if w.endswith("ing") and len(w) > 5:
			w = w[:-3]
		elif w.endswith("es") and len(w) > 4:
			w = w[:-2]
		elif w.endswith("s") and len(w) > 3:
			w = w[:-1]
		stem.append(w)
	return set(stem)


def _near_duplicate(a: str, b: str) -> bool:
	# token containment or high Jaccard similarity signals near-duplicate phrasing
	ta, tb = _tokens(a), _tokens(b)
	if not ta or not tb:
		return False
	# containment
	if ta.issubset(tb) or tb.issubset(ta):
		return True
	# jaccard
	inter = len(ta & tb)
	union = len(ta | tb)
	if union == 0:
		return False
	return (inter / union) >= 0.5


def _dedupe(candidates: List[ExpertOutcome]) -> List[ExpertOutcome]:
	seen = set()
	out: List[ExpertOutcome] = []
	for c in candidates:
		key = _normalize(c.outcome)
		# exact/normalized duplicate
		if key in seen:
			continue
		# near-duplicate against those already in list
		is_dup = any(_near_duplicate(c.outcome, e.outcome) for e in out)
		if is_dup:
			continue
		seen.add(key)
		out.append(c)
	return out


def _score(outcome: ExpertOutcome) -> float:
	text = outcome.outcome.lower()
	likelihood = 3.0
	impact = 3.0
	novelty = 2.5
	coverage = 3.0
	if any(h in text for h in ["may", "might", "could"]):
		likelihood -= 1.0
	if any(tok in text for tok in ["$", "%", "pp", "b", "m"]):
		impact += 0.5
	if any(br in text for br in ["apple", "tesla", "byd", "tsmc", "huawei", "samsung", "intel"]):
		novelty += 0.5
	return 0.45 * likelihood + 0.30 * impact + 0.15 * novelty + 0.10 * coverage


def _enforce_diversity(candidates: List[ExpertOutcome], theme_cap: int = 2, sub_cap: int = 1, limit: int = 4) -> List[ExpertOutcome]:
	themes: Dict[str, int] = {}
	subthemes: Dict[str, int] = {}
	selected: List[ExpertOutcome] = []
	for c in candidates:
		th = _theme_bucket(c.outcome)
		sth = _subtheme_bucket(c.outcome)
		if themes.get(th, 0) >= theme_cap:
			continue
		if subthemes.get(sth, 0) >= sub_cap:
			continue
		# prevent near-duplicate within selected set
		if any(_near_duplicate(c.outcome, s.outcome) for s in selected):
			continue
		themes[th] = themes.get(th, 0) + 1
		subthemes[sth] = subthemes.get(sth, 0) + 1
		selected.append(c)
		if len(selected) >= limit:
			break
	return selected


def _parse_expert_json(raw: str, expected: str) -> ExpertResponse:
	data = json.loads(raw)
	if not isinstance(data, dict) or data.get("expert") != expected:
		raise ValueError("wrong expert or shape")
	items = data.get("outcomes")
	if not isinstance(items, list) or len(items) != 3:
		raise ValueError("must have exactly 3 outcomes")
	outcomes = [ExpertOutcome(**{"outcome": i["outcome"], "explanation": i["explanation"]}) for i in items]
	return ExpertResponse(expert=expected, outcomes=outcomes)


def moderate_and_select(
	geo_json: str,
	econ_json: str,
	tech_json: str,
	social_json: str,
	scenario: str,
	llm: BaseChatModel,
	debug: bool = False,
) -> str:
	# 1) Parse expert outputs
	geo = _parse_expert_json(geo_json, "geo")
	econ = _parse_expert_json(econ_json, "econ")
	tech = _parse_expert_json(tech_json, "tech")
	social = _parse_expert_json(social_json, "social")
	candidates = geo.outcomes + econ.outcomes + tech.outcomes + social.outcomes
	debug_log(debug, "Moderator Candidates", json.dumps([c.model_dump() for c in candidates], ensure_ascii=False, indent=2))

	# STEP 1: De-duplicate/merge until we have at least 4 distinct outcomes
	step1_system = """
	You are the moderator. Your job is to remove or merge outcomes that are too similar in meaning. After you finish the list will have outcomes that are distinct from one another and from different angles.
	The minimum number of outcomes is 4- you must have at least 4 outcomes.
	Return JSON ONLY: {"cleaned_outcomes":[{"outcome":"...","explanation":"..."}]}
	"""
	candidates_json = json.dumps([c.model_dump() for c in candidates], ensure_ascii=False)
	step1_user = f"Scenario: {scenario}\nCandidates (JSON array):\n{candidates_json}"
	debug_log(debug, "LLM Moderator Step1 Input", json.dumps([c.model_dump() for c in candidates], ensure_ascii=False, indent=2))
	resp1 = llm.invoke([("system", step1_system), ("user", step1_user)])
	text1 = (resp1.content or "").strip()
	debug_log(debug, "LLM Moderator Step1 Output Raw", text1)
	try:
		data1 = json.loads(text1)
		cleaned = data1.get("cleaned_outcomes", [])
	except Exception:
		cleaned = []
	# Fallback to local dedupe if LLM fails
	if not isinstance(cleaned, list) or len(cleaned) < 4:
		deduped = _dedupe(candidates)
		cleaned = [{"outcome": d.outcome, "explanation": d.explanation} for d in deduped][:4]
	debug_log(debug, "LLM Moderator Step1 Cleaned", json.dumps(cleaned, ensure_ascii=False, indent=2))

	# STEP 2: Score and select top 4 with diversity
	step2_system = """
	Select the best 4 that are clearly different from one another.
	Instructions:
	- Rate each candidate internally on Likelihood 0-5, Impact 0-5, Novelty 0-5.
	- Prefer items with higher combined scores and distinct angles (policy/regulation, trade/economy, consumer behavior, tech/security, social/culture, international relations, supply chain).
	- Do not include scores in the output.
	Return JSON ONLY: {"scenario": str, "selected_outcomes":[{"outcome":"...","explanation":"..."}]}
	"""
	step2_user = f"Scenario: {scenario}\nCleaned items:\n{json.dumps(cleaned, ensure_ascii=False)}"
	resp2 = llm.invoke([("system", step2_system), ("user", step2_user)])
	text2 = (resp2.content or "").strip()
	debug_log(debug, "LLM Moderator Step2 Output Raw", text2)
	data2 = json.loads(text2)

	selected_outcomes: List[ExpertOutcome] = []
	for item in data2.get("selected_outcomes", [])[:4]:
		eo = ExpertOutcome(outcome=str(item.get("outcome", "")).strip(), explanation=str(item.get("explanation", "")).strip())
		p = map_profit_for_outcome(llm, eo.outcome, debug=debug)
		try:
			eo.profit = p if isinstance(p, Profit) else Profit(**p)
		except Exception:
			pass
		selected_outcomes.append(eo)

	final = FinalSelection(scenario=scenario, selected_outcomes=selected_outcomes)
	result = json.dumps(final.model_dump(), ensure_ascii=False, indent=2)
	debug_log(debug, "Moderator Final", result)
	return result
