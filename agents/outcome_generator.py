from typing import List, Dict
from langchain_core.language_models.chat_models import BaseChatModel
from core.debug import debug_log
import json


def generate_outcomes_for_seed(
    llm: BaseChatModel,
    seed_text: str,
    num_outcomes: int = 3,
    debug: bool = False,
) -> List[Dict[str, str]]:
    system = (
        "You generate specific outcomes with strict formatting.\n"
        "Constraints for each item:\n"
        "- outcome: ONE short sentence, <= 14 words AND <= 120 characters, present tense, no hedging (no 'may/might/could').\n"
        "- explanation: ONE sentence, 18–40 words, can elaborate on mechanism/impact.\n"
        "- Use plain, simple language. Avoid jargon, buzzwords, academic or highbrow words. Prefer everyday terms.\n"
        "- Include named entities and a time horizon if relevant.\n"
        "- Keep neutral, policy-compliant language.\n"
        "Output JSON ONLY with this schema (no extra text):\n"
        "{\"outcomes\":[{\"outcome\":\"...\", \"explanation\":\"...\"}]}"
    )

    examples = {
        "outcomes": [
            {
                "outcome": "US farm exports to China rise $10–15B within 12 months.",
                "explanation": "Tariff cuts and stronger demand for soybeans, corn, and pork push up sales. Better shipping and useful exchange rates help too."}
        ]
    }

    user = (
        f"Seed: {seed_text}\n"
        f"Generate exactly {num_outcomes} outcomes. Return ONLY the JSON. Here is the style example (do not copy entities):\n"
        f"{json.dumps(examples)}"
    )

    messages = [("system", system), ("user", user)]
    debug_log(debug, "OutcomeGenerator Prompt", f"SYSTEM:\n{system}\n\nUSER:\n{user}")
    response = llm.invoke(messages)
    text = response.content or ""
    debug_log(debug, "OutcomeGenerator Response", text)

    # Parse JSON robustly
    items: List[Dict[str, str]] = []
    try:
        data = json.loads(text)
        raw = data.get("outcomes", [])
        for it in raw[:num_outcomes]:
            outcome = str(it.get("outcome", "")).strip()
            explanation = str(it.get("explanation", "")).strip()
            if outcome:
                items.append({"outcome": outcome, "explanation": explanation})
    except Exception:
        # Fallback: line parse (outcome only)
        lines = [line.strip("- ") for line in text.splitlines() if line.strip()]
        for ln in lines[:num_outcomes]:
            items.append({"outcome": ln, "explanation": ""})

    # Final fallback
    if not items:
        items = [
            {
                "outcome": "US farm exports to China rise $10–15B within 12 months.",
                "explanation": "Tariff cuts and stronger demand lift sales; shipping and exchange rates help.",
            }
        ]

    return items


