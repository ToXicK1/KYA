from fastapi import APIRouter
from src.presentation.api.v1.endpoints import agents, health, auth

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(agents.router)
