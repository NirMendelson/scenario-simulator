from __future__ import annotations

import json
import re
from typing import Dict, List, Tuple

from core.debug import debug_log
from core.schema import ExpertOutcome, ExpertResponse, FinalSelection
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


def _dedupe(candidates: List[ExpertOutcome]) -> List[ExpertOutcome]:
	seen = set()
	out: List[ExpertOutcome] = []
	for c in candidates:
		key = _normalize(c.outcome)
		if key in seen:
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


def _enforce_diversity(candidates: List[ExpertOutcome], cap: int = 2, limit: int = 3) -> List[ExpertOutcome]:
	buckets: Dict[str, int] = {}
	selected: List[ExpertOutcome] = []
	for c in candidates:
		b = _theme_bucket(c.outcome)
		if buckets.get(b, 0) >= cap:
			continue
		buckets[b] = buckets.get(b, 0) + 1
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


def moderate_and_select(geo_json: str, econ_json: str, scenario: str, llm: BaseChatModel, debug: bool = False) -> str:
	geo = _parse_expert_json(geo_json, "geo")
	econ = _parse_expert_json(econ_json, "econ")
	candidates = geo.outcomes + econ.outcomes
	debug_log(debug, "Moderator Candidates", json.dumps([c.model_dump() for c in candidates], ensure_ascii=False, indent=2))
	candidates = _dedupe(candidates)
	scored: List[Tuple[ExpertOutcome, float]] = [(c, _score(c)) for c in candidates]
	scored.sort(key=lambda x: x[1], reverse=True)
	ranked = [c for c, _ in scored]
	selected = _enforce_diversity(ranked, cap=2, limit=3)
	for s in selected:
		p = map_profit_for_outcome(llm, s.outcome, debug=debug)
		s.profit = p  # type: ignore
	for s in selected:
		s.explanation = s.explanation.strip()
	final = FinalSelection(scenario=scenario, selected_outcomes=selected)
	text = json.dumps(final.model_dump(), ensure_ascii=False, indent=2)
	debug_log(debug, "Moderator Final", text)
	return text
