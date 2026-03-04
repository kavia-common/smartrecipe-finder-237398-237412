from src.api.routers.analytics import router as analytics_router
from src.api.routers.auth import router as auth_router
from src.api.routers.favorites import router as favorites_router
from src.api.routers.ingredients import router as ingredients_router
from src.api.routers.mealplan import router as mealplan_router
from src.api.routers.recipes import router as recipes_router
from src.api.routers.shopping import router as shopping_router

__all__ = [
    "analytics_router",
    "auth_router",
    "favorites_router",
    "ingredients_router",
    "mealplan_router",
    "recipes_router",
    "shopping_router",
]
