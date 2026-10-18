"""Small bilingual lexical retriever with explicit no-match behavior."""
import json
import math
import re
from pathlib import Path

STOP = set("a an the is are was were i my me you your we our can could do does how what when where to of for in on with it this that and or please have has want tell about noura لي ما من في عن علي على هو هي هل كيف متى اين انا هذا هذه ان اريد ممكن لو سمحت نورا".split())


def words(text):
    text = re.sub(r"[\u064b-\u065f\u0670ـ]", "", text.casefold())
    text = re.sub("[أإآ]", "ا", text).replace("ى", "ي")
    tokens = [word for word in re.findall(r"[a-z0-9\u0621-\u064a]+", text) if word not in STOP and len(word) > 1]
    # Preserve originals and add simple English plural variants (refunds/refund).
    return tokens + [word[:-1] for word in tokens if re.fullmatch(r"[a-z]{4,}s", word) and not word.endswith("ss")]


class KnowledgeBase:
    def __init__(self, path=None):
        self.articles = json.loads((path or Path(__file__).with_name("knowledge.json")).read_text(encoding="utf-8"))
        self.by_id = {a["id"]: a for a in self.articles}
        self.index = []
        for article in self.articles:
            strong = set(words(" ".join(article["keywords"])))
            titles = set(words(article["title"] + " " + article["title_ar"]))
            body = set(words(article["body"] + " " + article["body_ar"]))
            self.index.append((article, strong, titles, body))

    def search(self, query, limit=3):
        terms = set(words(query))
        ranked = []
        for article, keywords, titles, body in self.index:
            # At least a subject keyword/title match prevents generic prose matches.
            anchors = terms & (keywords | titles)
            if not anchors:
                continue
            score = 0.0
            for term in terms:
                frequency = sum(term in (k | t | b) for _, k, t, b in self.index)
                weight = math.log(1 + len(self.articles) / (1 + frequency))
                score += weight * (5 * (term in keywords) + 3 * (term in titles) + (term in body))
            ranked.append((score, article))
        ranked.sort(key=lambda item: (-item[0], item[1]["id"]))
        threshold = ranked[0][0] * 0.55 if ranked else 0
        return [article for score, article in ranked[:limit] if score >= threshold]

    def excerpt(self, article, language):
        return {"id": article["id"], "title": article["title_ar"] if language == "ar" else article["title"],
                "category": article["category"], "body": article["body_ar"] if language == "ar" else article["body"]}
