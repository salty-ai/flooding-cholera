"""Routers package."""
from app.routers.lgas import router as lgas_router
from app.routers.analytics import router as analytics_router
from app.routers.upload import router as upload_router
from app.routers.satellite import router as satellite_router
from app.routers.alerts import router as alerts_router
from app.routers.facilities import router as facilities_router
from app.routers.agent import router as agent_router
from app.routers.admin_data import router as admin_data_router
from app.routers.reports import router as reports_router

__all__ = ["lgas_router", "analytics_router", "upload_router", "satellite_router", "alerts_router", "facilities_router", "agent_router", "admin_data_router", "reports_router"]
