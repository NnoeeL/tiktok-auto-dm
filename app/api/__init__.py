from fastapi import APIRouter
from app.api.routes_rules import router as rules_router
from app.api.routes_bot import router as bot_router
from app.api.routes_logs import router as logs_router

api_router = APIRouter(prefix="/api")
api_router.include_router(rules_router, prefix="/rules", tags=["Rules"])
api_router.include_router(bot_router, prefix="/bot", tags=["Bot Control"])
api_router.include_router(logs_router, prefix="/logs", tags=["Logs & Stats"])
