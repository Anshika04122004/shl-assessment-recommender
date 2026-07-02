from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = ROOT / "shl_product_catalog.json"

KEY_TO_CODE = {
    "Ability & Aptitude": "A",
    "Assessment Exercises": "E",
    "Biodata & Situational Judgment": "B",
    "Competencies": "C",
    "Development & 360": "D",
    "Knowledge & Skills": "K",
    "Personality & Behavior": "P",
    "Simulations": "S",
}


def normalize_text(value: str) -> str:
    value = value.lower()
    value = value.replace("&", " and ")
    value = re.sub(r"[^a-z0-9+#.]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def tokenize(value: str) -> set[str]:
    return {token for token in normalize_text(value).split() if len(token) > 1}


# Generic hiring/conversation words that add noise to lexical matching. They are
# stripped from the *query* side only (never from product text) so that role and
# skill terms drive retrieval instead of filler like "hiring" or "candidate".
SEARCH_STOPWORDS = frozenset(
    {
        "a", "an", "and", "or", "the", "for", "to", "of", "in", "on", "with", "we",
        "our", "i", "you", "they", "them", "is", "are", "be", "need", "needs",
        "want", "looking", "look", "help", "please", "hire", "hiring", "hired",
        "role", "roles", "job", "jobs", "position", "positions", "candidate",
        "candidates", "assess", "assessment", "assessments", "test", "tests",
        "testing", "screen", "screening", "evaluate", "evaluation", "team",
        "teams", "staff", "people", "person", "someone", "new", "good", "great",
        "quick", "quickly", "level", "experience", "years", "shl", "solution",
        "solutions", "recommend", "recommendation", "add", "also", "some",
    }
)


@dataclass(frozen=True)
class Product:
    entity_id: str
    name: str
    url: str
    job_levels: tuple[str, ...]
    languages: tuple[str, ...]
    duration: str
    remote: str
    adaptive: str
    description: str
    keys: tuple[str, ...]
    test_type: str
    search_text: str
    tokens: frozenset[str]

    @property
    def is_report(self) -> bool:
        return "report" in self.name.lower()


class Catalog:
    def __init__(self, products: list[Product]):
        self.products = products
        self.by_name = {p.name: p for p in products}
        self.by_name_norm = {normalize_text(p.name): p for p in products}
        self.urls = {p.url for p in products}

    @classmethod
    def load(cls, path: Path = CATALOG_PATH) -> "Catalog":
        raw = path.read_text(encoding="utf-8")
        rows = json.loads(raw, strict=False)
        if not isinstance(rows, list):
            raise ValueError("Catalog must be a JSON list")

        products: list[Product] = []
        for row in rows:
            required = ("entity_id", "name", "link", "keys")
            missing = [field for field in required if field not in row or row[field] in (None, "")]
            if missing:
                raise ValueError(f"Catalog product missing required fields {missing}: {row!r}")
            keys = tuple(row.get("keys") or ())
            codes = [KEY_TO_CODE[key] for key in keys if key in KEY_TO_CODE]
            test_type = ",".join(codes)
            search_text = " ".join(
                [
                    row.get("name", ""),
                    row.get("description", ""),
                    " ".join(row.get("job_levels") or []),
                    " ".join(row.get("languages") or []),
                    " ".join(keys),
                ]
            )
            products.append(
                Product(
                    entity_id=str(row["entity_id"]),
                    name=str(row["name"]),
                    url=str(row["link"]),
                    job_levels=tuple(row.get("job_levels") or ()),
                    languages=tuple(row.get("languages") or ()),
                    duration=str(row.get("duration") or ""),
                    remote=str(row.get("remote") or ""),
                    adaptive=str(row.get("adaptive") or ""),
                    description=str(row.get("description") or ""),
                    keys=keys,
                    test_type=test_type,
                    search_text=search_text,
                    tokens=frozenset(tokenize(search_text)),
                )
            )

        if len(products) < 300:
            raise ValueError(f"Catalog unexpectedly small: {len(products)} products")
        return cls(products)

    def get(self, name: str) -> Product | None:
        product = self.by_name.get(name)
        if product:
            return product
        return self.by_name_norm.get(normalize_text(name))

    def find_mentions(self, text: str) -> list[Product]:
        norm = normalize_text(text)
        found: list[Product] = []
        for name_norm, product in self.by_name_norm.items():
            if name_norm and name_norm in norm:
                found.append(product)
        return dedupe_products(found)

    def search(self, query: str, limit: int = 30) -> list[tuple[Product, float]]:
        query_tokens = tokenize(query) - SEARCH_STOPWORDS
        if not query_tokens:
            return []
        scored: list[tuple[Product, float]] = []
        for product in self.products:
            overlap = query_tokens & product.tokens
            if not overlap:
                continue
            score = 0.0
            score += len(overlap)
            name_tokens = tokenize(product.name)
            score += 2.5 * len(query_tokens & name_tokens)
            desc_tokens = tokenize(product.description)
            score += 0.25 * len(query_tokens & desc_tokens)
            if product.is_report:
                score -= 1.0
            scored.append((product, score))
        scored.sort(key=lambda item: item[1], reverse=True)
        return scored[:limit]


def dedupe_products(products: list[Product]) -> list[Product]:
    seen: set[str] = set()
    result: list[Product] = []
    for product in products:
        if product.url in seen:
            continue
        seen.add(product.url)
        result.append(product)
    return result

