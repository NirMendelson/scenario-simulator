from langchain_core.language_models.chat_models import BaseChatModel
from core.debug import debug_log


def is_outcome_plausible(llm: BaseChatModel, seed_text: str, outcome_text: str, debug: bool = False) -> bool:
    system = (
        "You assess whether an outcome is plausible within 0-24 months given a seed scenario. "
        "Follow safety policies; if content is disallowed, treat it as NOT plausible. "
        "Respond with only 'YES' or 'NO'."
    )
    user = (
        f"Seed: {seed_text}\nOutcome: {outcome_text}\n"
        "Is this outcome plausible in the next 0-24 months? Reply 'YES' or 'NO' only."
    )
    debug_log(debug, "PlausibilityChecker Prompt", f"SYSTEM:\n{system}\n\nUSER:\n{user}")
    response = llm.invoke([("system", system), ("user", user)])
    answer = (response.content or "").strip().upper()
    debug_log(debug, "PlausibilityChecker Response", answer)
    return answer.startswith("Y")


