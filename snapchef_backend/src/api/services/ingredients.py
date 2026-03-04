from __future__ import annotations

import hashlib
import random
import re
from typing import Iterable

from src.api.core.utils import now_utc_iso


_COMMON_SYNONYMS = {
    "bell pepper": ["capsicum", "sweet pepper"],
    "garlic": ["garlic clove", "garlic cloves"],
    "tomato": ["tomatoes", "roma tomato", "cherry tomatoes"],
    "onion": ["yellow onion", "red onion", "white onion"],
    "olive oil": ["extra virgin olive oil", "evoo"],
    "chicken": ["chicken breast", "chicken thighs"],
    "milk": ["whole milk", "skim milk"],
}

_STRIP_RE = re.compile(r"[^a-z0-9\s\-]")


# PUBLIC_INTERFACE
def normalize_ingredient_name(name: str) -> str:
    """Normalize an ingredient string for matching/search (simple heuristic)."""
    s = (name or "").strip().lower()
    s = _STRIP_RE.sub("", s)
    s = re.sub(r"\s+", " ", s).strip()
    # basic plural stripping
    if s.endswith("es") and len(s) > 4:
        s = s[:-2]
    elif s.endswith("s") and len(s) > 3:
        s = s[:-1]
    return s


# PUBLIC_INTERFACE
def normalize_many(names: Iterable[str]) -> list[tuple[str, str]]:
    """Normalize many ingredient strings."""
    out: list[tuple[str, str]] = []
    for n in names:
        out.append((n, normalize_ingredient_name(n)))
    return out


# PUBLIC_INTERFACE
def recognize_ingredients_stub(image_bytes: bytes, filename: str | None = None) -> dict:
    """Stubbed ingredient recognition.

    This is intentionally deterministic-ish per image (hash-based) so clients can
    demo stable behavior without a real ML pipeline.
    """
    digest = hashlib.sha256(image_bytes).hexdigest()
    seed = int(digest[:8], 16)
    rng = random.Random(seed)

    candidates = ["tomato", "onion", "garlic", "olive oil", "chicken", "milk", "bell pepper", "basil", "egg", "cheese"]
    rng.shuffle(candidates)
    picked = candidates[: rng.randint(3, 6)]

    ingredients = []
    base_conf = 0.92
    for i, name in enumerate(picked):
        confidence = max(0.25, base_conf - i * rng.uniform(0.08, 0.15))
        ingredients.append({"name": name, "confidence": round(confidence, 2)})

    return {
        "request_id": f"rec_{digest[:10]}_{now_utc_iso()}",
        "ingredients": ingredients,
        "warnings": ["ingredient_recognition_stub_enabled"],
        "debug": {"filename": filename, "sha256": digest},
    }


# PUBLIC_INTERFACE
def expand_synonyms(normalized_name: str) -> list[str]:
    """Return synonyms for normalized ingredient names (used for matching)."""
    normalized_name = normalize_ingredient_name(normalized_name)
    out = {normalized_name}
    for canonical, syns in _COMMON_SYNONYMS.items():
        c_norm = normalize_ingredient_name(canonical)
        if normalized_name == c_norm:
            out.update(normalize_ingredient_name(s) for s in syns)
        else:
            for s in syns:
                if normalized_name == normalize_ingredient_name(s):
                    out.add(c_norm)
                    out.update(normalize_ingredient_name(x) for x in syns)
    return sorted(out)
