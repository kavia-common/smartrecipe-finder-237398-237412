from __future__ import annotations

from fastapi import APIRouter, File, UploadFile
from fastapi.responses import JSONResponse

from src.api.schemas import IngredientNormalizeRequest, IngredientNormalizeResponse, IngredientRecognitionResponse
from src.api.services.ingredients import normalize_many, recognize_ingredients_stub

router = APIRouter(prefix="/ingredients", tags=["Ingredients"])


@router.post(
    "/recognize",
    summary="Recognize ingredients from an uploaded image (stub)",
    description="Accepts an image upload and returns stubbed ingredient candidates. This endpoint is designed to be replaced by a real CV/ML pipeline.",
    response_model=IngredientRecognitionResponse,
    operation_id="recognize_ingredients",
)
async def recognize_ingredients(file: UploadFile = File(...)) -> JSONResponse:
    """Upload an image and get ingredient recognition results (stubbed)."""
    content = await file.read()
    result = recognize_ingredients_stub(content, filename=file.filename)
    # Trim debug field from response model, but keep server-side deterministic behavior.
    payload = {
        "request_id": result["request_id"],
        "ingredients": result["ingredients"],
        "warnings": result.get("warnings", []),
    }
    return JSONResponse(payload)


@router.post(
    "/normalize",
    summary="Normalize ingredient strings",
    description="Lightweight normalization (lowercasing, stripping punctuation, naive plural handling).",
    response_model=IngredientNormalizeResponse,
    operation_id="normalize_ingredients",
)
async def normalize_ingredients(payload: IngredientNormalizeRequest) -> IngredientNormalizeResponse:
    """Normalize ingredient strings for matching."""
    items = []
    for original, normalized in normalize_many(payload.ingredients):
        items.append({"original": original, "normalized": normalized, "canonical": normalized or None})
    return IngredientNormalizeResponse(items=items)
