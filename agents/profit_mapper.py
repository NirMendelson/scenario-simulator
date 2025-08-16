from typing import Dict
from langchain_core.language_models.chat_models import BaseChatModel
from core.debug import debug_log
import json


def map_profit_for_outcome(llm: BaseChatModel, outcome_text: str, debug: bool = False) -> Dict[str, str]:
    system = (
        "You suggest a concrete investment based on the outcome.\n"
        "Rules:\n"
        "- idea MUST be: 'Invest in {between 1 and 3 TICKER or ETF or specific company stock}'.\n"
        "- Do NOT suggest diversifying, shorting, hedging, or strategies. Only a single investable asset name/ticker.\n"
        "- Use plain language. Keep explanation under 18 words, neutral and educational.\n"
        "Return JSON ONLY with keys 'idea' and 'explanation'."
    )
    user = (
        f"Outcome: {outcome_text}\n"
        "Return only JSON: {\"idea\":\"Invest in ...\", \"explanation\":\"...\"}"
    )
    debug_log(debug, "ImpactMapper Prompt", f"SYSTEM:\n{system}\n\nUSER:\n{user}")
    response = llm.invoke([("system", system), ("user", user)])
    text = response.content or ""
    debug_log(debug, "ImpactMapper Response", text)
    # Parse JSON strictly
    try:
        data = json.loads(text)
        idea = str(data.get("idea", "")).strip()
        explanation = str(data.get("explanation", "")).strip()
        if idea.lower().startswith("invest in ") and explanation:
            return {"idea": idea, "explanation": explanation}
    except Exception:
        pass
    # Fallback with a safe pattern
    return {
        "idea": "Invest in SPY",
        "explanation": "Broad market exposure while you research sector leaders.",
    }


