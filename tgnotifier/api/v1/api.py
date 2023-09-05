from fastapi import APIRouter, Depends
from fastapi.routing import APIRoute
from .deps import get_db
from .endpoints import (
	telegram
)
from fastapi.middleware.cors import CORSMiddleware
from tgnotifier.core.settings import settings

STANDART_DEPS = [Depends(get_db)]

api_router = APIRouter()
api_router.include_router(telegram.router, prefix="/telegram", tags=["telegram"], dependencies=STANDART_DEPS)

# Simplify route names in OpenAPI. Idea from https://fastapi-utils.davidmontague.xyz/user-guide/openapi/
for route in api_router.routes:
    if isinstance(route, APIRoute):
        route.operation_id = route.name
