from langchain_core.language_models.chat_models import BaseChatModel
from core.debug import debug_log


def ask_econ_expert(llm: BaseChatModel, scenario: str, debug: bool = False) -> str:
	system = (
		"You are an economic history analyst producing neutral, policy-compliant text. "
		"Read the scenario and propose exactly 3 distinct outcomes. Return JSON only with this schema: "
		"{\"expert\":\"econ\",\"outcomes\":[{\"outcome\":\"...\", \"explanation\":\"...\"}]}\n"
		"Rules:\n- outcome: ONE short sentence, present tense, simple words.\n- explanation: ONE sentence, 18–40 words.\n- No probabilities/citations/extra fields; short or medium horizon."
	)
	user = f"Scenario: {scenario}\nReturn only the JSON."
	debug_log(debug, "EconExpert Prompt", f"SYSTEM:\n{system}\n\nUSER:\n{user}")
	resp = llm.invoke([("system", system), ("user", user)])
	text = resp.content or ""
	debug_log(debug, "EconExpert Response", text)
	return text
