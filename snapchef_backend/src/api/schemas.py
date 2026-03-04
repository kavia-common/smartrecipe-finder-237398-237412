from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class ApiError(BaseModel):
    code: str = Field(..., description="Machine-readable error code.")
    message: str = Field(..., description="Human-readable error message.")
    details: dict[str, Any] | None = Field(default=None, description="Optional structured details.")


class PageMeta(BaseModel):
    limit: int = Field(..., ge=1, description="Page size limit.")
    offset: int = Field(..., ge=0, description="Page offset.")
    total: int = Field(..., ge=0, description="Total items matching query.")


class PagedResponse(BaseModel):
    meta: PageMeta
    items: list[Any]


class UserProfile(BaseModel):
    id: str = Field(..., description="Demo user id.")
    display_name: str = Field(..., description="User-visible display name.")
    created_at: datetime


class DemoLoginRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=64, description="Client-chosen demo user id.")
    display_name: str | None = Field(default=None, max_length=120)


class DemoLoginResponse(BaseModel):
    user: UserProfile


class IngredientCandidate(BaseModel):
    name: str = Field(..., description="Detected ingredient name (raw or normalized).")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Detection confidence 0..1.")


class IngredientRecognitionResponse(BaseModel):
    request_id: str = Field(..., description="Correlation id for this recognition request.")
    ingredients: list[IngredientCandidate] = Field(..., description="Ranked ingredient candidates (stubbed).")
    warnings: list[str] = Field(default_factory=list, description="Non-fatal warnings.")


class IngredientNormalizeRequest(BaseModel):
    ingredients: list[str] = Field(..., min_length=1, description="Ingredient strings to normalize.")


class IngredientNormalizeItem(BaseModel):
    original: str
    normalized: str
    canonical: str | None = Field(default=None, description="Optional canonical ingredient concept id/name.")


class IngredientNormalizeResponse(BaseModel):
    items: list[IngredientNormalizeItem]


class RecipeIngredient(BaseModel):
    name: str
    quantity: str | None = None
    unit: str | None = None


class RecipeOut(BaseModel):
    id: int
    title: str
    description: str | None = None
    cuisine: str | None = None
    diet_tags: list[str] = Field(default_factory=list)
    allergen_tags: list[str] = Field(default_factory=list)
    total_time_minutes: int | None = None
    servings: int | None = None
    ingredients: list[RecipeIngredient] = Field(default_factory=list)
    steps: list[str] = Field(default_factory=list)
    created_at: datetime


class RecipeSearchResponse(BaseModel):
    meta: PageMeta
    items: list[RecipeOut]


class RecipeSuggestionRequest(BaseModel):
    ingredients: list[str] = Field(..., min_length=1, description="Ingredients user has/selected.")
    cuisine: str | None = None
    diet: list[str] = Field(default_factory=list)
    allergens_exclude: list[str] = Field(default_factory=list)
    max_time_minutes: int | None = Field(default=None, ge=1)


class RecipeSuggestionResponse(BaseModel):
    meta: PageMeta
    items: list[RecipeOut]


class FavoriteOut(BaseModel):
    recipe_id: int
    created_at: datetime


class FavoritesResponse(BaseModel):
    meta: PageMeta
    items: list[RecipeOut]


class FavoriteToggleResponse(BaseModel):
    recipe_id: int
    is_favorite: bool


class ShoppingItemCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=140)
    quantity: str | None = Field(default=None, max_length=60)
    unit: str | None = Field(default=None, max_length=30)


class ShoppingItemUpdate(BaseModel):
    quantity: str | None = Field(default=None, max_length=60)
    unit: str | None = Field(default=None, max_length=30)
    checked: bool | None = None


class ShoppingItemOut(BaseModel):
    id: int
    name: str
    quantity: str | None = None
    unit: str | None = None
    checked: bool
    created_at: datetime


class ShoppingListResponse(BaseModel):
    meta: PageMeta
    items: list[ShoppingItemOut]


MealSlot = Literal["breakfast", "lunch", "dinner", "snack"]


class MealPlanCreate(BaseModel):
    day: date
    slot: MealSlot
    recipe_id: int | None = None
    note: str | None = Field(default=None, max_length=240)


class MealPlanOut(BaseModel):
    id: int
    day: date
    slot: MealSlot
    recipe_id: int | None = None
    note: str | None = None
    created_at: datetime


class MealPlanResponse(BaseModel):
    meta: PageMeta
    items: list[MealPlanOut]


class AnalyticsTrackRequest(BaseModel):
    event_name: str = Field(..., min_length=1, max_length=80)
    payload: dict[str, Any] = Field(default_factory=dict)


class AnalyticsTrackResponse(BaseModel):
    status: str = Field(..., description="ok")
    event_id: int


class AnalyticsSummaryResponse(BaseModel):
    total_events: int
    by_event_name: dict[str, int]
    last_7_days: dict[str, int] = Field(
        ..., description="Counts keyed by YYYY-MM-DD for last 7 days (including today)."
    )
