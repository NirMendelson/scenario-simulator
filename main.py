import argparse
import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI, AzureChatOpenAI

from core.orchestrator import brainstorm_round


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scenario Generator (4 Experts x 2 Rounds)")
    parser.add_argument("--seed", type=str, default="", help="Scenario to use (if empty, you will be prompted)")
    parser.add_argument("--model", type=str, default=os.getenv("MODEL_NAME", "grok-3-mini"), help="Model name")
    parser.add_argument("--out", type=str, default="data/final.json", help="Path to save JSON output")
    parser.add_argument("--debug", action="store_true", help="Print agent prompts and responses")
    return parser.parse_args()


def _create_llm(model: str):
    grok_api_key = os.getenv("GROK_API_KEY") or os.getenv("XAI_API_KEY")
    if grok_api_key:
        grok_base_url = os.getenv("GROK_BASE_URL", "https://api.x.ai/v1")
        return ChatOpenAI(api_key=grok_api_key, base_url=grok_base_url, model=model, temperature=0.3)

    azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    azure_api_key = os.getenv("AZURE_OPENAI_API_KEY")
    azure_api_version = os.getenv("OPENAI_API_VERSION")
    azure_deployment = os.getenv("GPT_4O_MINI_DEPLOYMENT_NAME") or os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT_NAME")
    if azure_endpoint and azure_api_key and azure_api_version and azure_deployment:
        return AzureChatOpenAI(
            azure_endpoint=azure_endpoint,
            api_version=azure_api_version,
            azure_deployment=azure_deployment,
            api_key=azure_api_key,
            temperature=0.3,
        )
    return ChatOpenAI(model=model, temperature=0.3)


def main() -> None:
    load_dotenv()
    args = parse_args()

    grok_present = bool(os.getenv("GROK_API_KEY") or os.getenv("XAI_API_KEY"))
    azure_present = (
        os.getenv("AZURE_OPENAI_ENDPOINT")
        and os.getenv("AZURE_OPENAI_API_KEY")
        and os.getenv("OPENAI_API_VERSION")
        and (os.getenv("GPT_4O_MINI_DEPLOYMENT_NAME") or os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT_NAME"))
    )
    openai_present = bool(os.getenv("OPENAI_API_KEY"))
    if not (grok_present or azure_present or openai_present):
        raise RuntimeError("No API key found: set GROK_API_KEY (recommended), or Azure/OpenAI env vars")

    llm = _create_llm(args.model)
    scenario = args.seed or input("Insert scenario: ").strip()
    tree_json = brainstorm_round(llm, scenario, debug=bool(args.debug))
    print(tree_json)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        f.write(tree_json)
    print(f"Saved to {out_path}")


if __name__ == "__main__":
    main()


