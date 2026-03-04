from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.models import Recipe


_SEED_RECIPES = [
    {
        "title": "Garlic Tomato Pasta",
        "description": "A quick weeknight pasta with tomato, garlic, and olive oil.",
        "cuisine": "italian",
        "diet_tags": ["vegetarian"],
        "allergen_tags": ["gluten"],
        "total_time_minutes": 20,
        "servings": 2,
        "ingredients": [
            {"name": "pasta", "quantity": "200", "unit": "g"},
            {"name": "tomato", "quantity": "2", "unit": "pcs"},
            {"name": "garlic", "quantity": "2", "unit": "cloves"},
            {"name": "olive oil", "quantity": "2", "unit": "tbsp"},
            {"name": "basil", "quantity": None, "unit": None},
        ],
        "steps": ["Boil pasta.", "Sauté garlic in olive oil.", "Add tomato.", "Toss pasta and serve with basil."],
    },
    {
        "title": "Simple Chicken Stir-Fry",
        "description": "Chicken with bell pepper and onion, served over rice.",
        "cuisine": "asian",
        "diet_tags": ["high-protein"],
        "allergen_tags": ["soy"],
        "total_time_minutes": 25,
        "servings": 2,
        "ingredients": [
            {"name": "chicken breast", "quantity": "300", "unit": "g"},
            {"name": "bell pepper", "quantity": "1", "unit": "pcs"},
            {"name": "onion", "quantity": "1/2", "unit": "pcs"},
            {"name": "soy sauce", "quantity": "2", "unit": "tbsp"},
        ],
        "steps": ["Slice chicken.", "Stir-fry chicken.", "Add veggies.", "Add soy sauce and serve."],
    },
    {
        "title": "Cheesy Omelet",
        "description": "Classic omelet with eggs, milk, and cheese.",
        "cuisine": "american",
        "diet_tags": ["vegetarian", "gluten-free"],
        "allergen_tags": ["dairy", "egg"],
        "total_time_minutes": 10,
        "servings": 1,
        "ingredients": [
            {"name": "egg", "quantity": "2", "unit": "pcs"},
            {"name": "milk", "quantity": "2", "unit": "tbsp"},
            {"name": "cheese", "quantity": "40", "unit": "g"},
        ],
        "steps": ["Whisk eggs with milk.", "Pour into pan.", "Add cheese.", "Fold and serve."],
    },
]


# PUBLIC_INTERFACE
async def ensure_seed_data(session: AsyncSession) -> None:
    """Insert a small set of demo recipes if the recipes table is empty."""
    existing = await session.execute(select(Recipe.id).limit(1))
    if existing.first() is not None:
        return

    for r in _SEED_RECIPES:
        session.add(Recipe(**r))
    await session.commit()
