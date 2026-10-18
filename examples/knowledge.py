"""Small local retrieval example; no embedding API or database account needed."""
import json
import re
from pathlib import Path

FAQ_PATH = Path(__file__).resolve().parents[1] / "data" / "faq.json"


def terms(text: str) -> set[str]:
    return set(re.findall(r"\w+", text.casefold()))


def search_faq(query: str) -> dict:
    if not query.strip() or len(query) > 500:
        return {"found": False, "reason": "Use a query between 1 and 500 characters."}
    records = json.loads(FAQ_PATH.read_text(encoding="utf-8"))
    query_terms = terms(query)
    # Match curated keywords, not generic question words such as "what"/"is".
    ranked = sorted(records, key=lambda r: len(query_terms & terms(
        " ".join(r["keywords"]))), reverse=True)
    best = ranked[0] if ranked else None
    if best is None or not query_terms & terms(" ".join(best["keywords"])):
        return {"found": False, "reason": "No matching tutorial fact. Do not guess."}
    return {"found": True, "answer": best["answer"], "source": best["source"]}

