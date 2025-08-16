from typing import List, Optional
from langchain_core.language_models.chat_models import BaseChatModel
from core.debug import debug_log


def generate_seed_scenarios(
    llm: BaseChatModel,
    num_seeds: int = 3,
    debug: bool = False,
    require_specific: bool = False,
    domain: str = "geopolitics",  # default to geopolitics
    examples: Optional[List[str]] = None,
) -> List[str]:
    base_policy = (
        "Follow all safety policies and provide safe, neutral content. "
        "Avoid violent conflict, sexual content, self-harm, or anything disallowed."
    )
    domain_instr = (
        "Generate scenarios in non-sensitive domains (technology, economy, climate, supply chain, consumer behavior, policy changes)."
        if domain != "geopolitics"
        else "Generate scenarios in global affairs and markets. Keep analysis neutral and non-graphic."
    )
    specificity = (
        "Use named entities (companies, governments, countries) and concrete details. Include a 6–24 month timeframe."
        if require_specific
        else "Keep concise and neutral."
    )

    system = (
        f"You generate concise seed scenarios. {base_policy} {domain_instr} {specificity} "
        "Return each scenario as a single sentence."
    )

    examples_block = ""
    if examples:
        few_shots = "\n".join(f"- {e}" for e in examples if e.strip())
        examples_block = f"\n\nExamples:\n{few_shots}"
    elif require_specific and domain == "geopolitics":
        few_shots = "\n".join(
            [
                "- Russia uses a tactical nuclear weapon in Ukraine",
                "- North Korea launches a full-scale invasion of South Korea",
                "- Iran closes the Strait of Hormuz",
                "- Europe enforces mass deportations of Middle Eastern & African migrants",
                "- India forcibly annexes Pakistan-administered Kashmir",
                "- Military coup in China",
                "- US formally recognizes Taiwan as independent",
                "- Iran religious government gets thrown",
                "- China’s housing bubble collapse",
                "- Japan’s public debt crisis explodes",
                "- A virus with higher mortality than COVID spreads globally",
                "- Quantum computing cracks all modern encryption",
                "- Deepfake of a world leader triggers a false military escalation",
                "- EU collapses after France or Germany exits",
            ]
        )
        examples_block = f"\n\nExamples (hypothetical, for neutral analysis only):\n{few_shots}"

    user = (
        f"Generate {num_seeds} distinct high-impact seed scenarios strictly within the guidance above. "
        "Be concrete, avoid duplicates." + examples_block
    )

    messages = [("system", system), ("user", user)]
    debug_log(debug, "SeedGenerator Prompt", f"SYSTEM:\n{system}\n\nUSER:\n{user}")
    response = llm.invoke(messages)
    text = response.content or ""
    debug_log(debug, "SeedGenerator Response", text)
    lines = [line.strip("- ") for line in text.splitlines() if line.strip()]
    if len(lines) >= num_seeds:
        return lines[:num_seeds]
    return [text.strip()] if text.strip() else ["TSMC announces a 3nm yield breakthrough, accelerating flagship smartphone releases within 12 months."]


def choose_seed_from_list(
    llm: BaseChatModel,
    seed_candidates: List[str],
    debug: bool = False,
) -> str:
    joined = "\n".join(f"- {s}" for s in seed_candidates)
    system = (
        "You select the single most analyzable, specific, and time-bounded scenario from a safe list. "
        "Prefer named entities and operational/market relevance."
    )
    user = f"Choose the best scenario from this list and return only the chosen sentence:\n{joined}"
    messages = [("system", system), ("user", user)]
    debug_log(debug, "SeedChooser Prompt", f"SYSTEM:\n{system}\n\nUSER:\n{user}")
    response = llm.invoke(messages)
    text = (response.content or seed_candidates[0]).strip()
    debug_log(debug, "SeedChooser Response", text)
    return text


