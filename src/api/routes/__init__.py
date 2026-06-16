from fastapi import APIRouter

from src.api.routes.auth import router as auth_router
from src.api.routes.users import router as users_router
from src.api.routes.portfolio import router as portfolio_router
from src.api.routes.recommendations import router as recommendations_router
from src.api.routes.watchlists import router as watchlists_router
from src.api.routes.alerts import router as alerts_router
from src.api.routes.transactions import router as transactions_router
from src.api.routes.chat import router as chat_router

router = APIRouter()
router.include_router(auth_router, prefix="/auth", tags=["Auth"])
router.include_router(users_router, prefix="/users", tags=["Users"])
router.include_router(portfolio_router, prefix="/portfolio", tags=["Portfolio"])
router.include_router(recommendations_router, prefix="/recommendations", tags=["Recommendations"])
router.include_router(watchlists_router, prefix="/watchlists", tags=["Watchlists"])
router.include_router(alerts_router, prefix="/alerts", tags=["Alerts"])
router.include_router(transactions_router, prefix="/transactions", tags=["Transactions"])
router.include_router(chat_router, prefix="/chat", tags=["Chat"])
