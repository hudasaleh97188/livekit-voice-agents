"""Free-only OpenRouter chat and public model discovery; no LiveKit needed."""
import argparse
from decimal import Decimal, InvalidOperation

import requests

from .config import free_model, load_settings, required
from .http_helpers import json_response, run_cli

BASE = "https://openrouter.ai/api/v1"


def is_zero_price(model: dict) -> bool:
    pricing = model.get("pricing", {})
    try:
        return all(Decimal(str(pricing.get(k, "-1"))) == 0
                   for k in ("prompt", "completion"))
    except InvalidOperation:
        return False


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("prompt", nargs="?", default="Explain LiveKit in three short sentences.")
    parser.add_argument("--list-free", action="store_true")
    args = parser.parse_args()
    load_settings()
    if args.list_free:
        with requests.get(f"{BASE}/models", timeout=(10, 30)) as response:
            models = json_response(response)["data"]
        for model in models:
            if (model["id"].endswith(":free") or model["id"] == "openrouter/free") and is_zero_price(model):
                tools = "tools" in model.get("supported_parameters", [])
                print(f"{model['id']} | tools={tools} | context={model.get('context_length')}")
        return
    model = free_model()
    headers = {"Authorization": f"Bearer {required('OPENROUTER_API_KEY')}"}
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": "Answer clearly and briefly. Match the user's language."},
            {"role": "user", "content": args.prompt},
        ],
        "max_tokens": 300,
        # No paid fallback models or paid web-search plugins.
        "provider": {"max_price": {"prompt": 0, "completion": 0}},
    }
    with requests.post(f"{BASE}/chat/completions", headers=headers, json=body,
                       timeout=(10, 60)) as response:
        result = json_response(response)
    try:
        answer = result["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        raise RuntimeError("Unexpected chat response format.") from None
    if not isinstance(answer, str) or not answer.strip():
        raise RuntimeError("No text returned. Try another free model or a larger output budget.")
    print(answer)
    print(f"\nModel used: {result.get('model', model)}")


if __name__ == "__main__":
    run_cli(main)

