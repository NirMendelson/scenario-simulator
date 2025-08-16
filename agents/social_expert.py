from langchain_core.language_models.chat_models import BaseChatModel
from core.debug import debug_log


def ask_social_expert(llm: BaseChatModel, scenario: str, debug: bool = False) -> str:
	system = (
		"You are a social dynamics analyst producing neutral, policy-compliant text for hypothetical analysis. "
		"Read the scenario and propose exactly 1 distinct outcome. Return JSON only with this schema: "
		"{\"expert\":\"social\",\"outcome\":\"...\", \"explanation\":\"...\"}" 
		"Rules:\n- Only 'outcome' and 'explanation'.\n- One sentence per explanation.\n- No probabilities, no citations, no extra fields.\n- Short or medium horizon."
	)
	user = f"Scenario: {scenario}\nReturn only the JSON."
	debug_log(debug, "SocialExpert Prompt", f"SYSTEM:\n{system}\n\nUSER:\n{user}")
	resp = llm.invoke([("system", system), ("user", user)])
	text = resp.content or ""
	debug_log(debug, "SocialExpert Response", text)
	return text
