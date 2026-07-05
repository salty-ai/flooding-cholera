"""Cholera Environmental Surveillance System - Main FastAPI Application."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.background import BackgroundScheduler
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import get_settings
from app.database import init_db, SessionLocal
from app.routers import lgas_router, analytics_router, upload_router, satellite_router, alerts_router, facilities_router, agent_router, admin_data_router
from app.services.risk_calculator import RiskCalculator
from app.exceptions import setup_exception_handlers
from app.rate_limiter import limiter, rate_limit_exceeded_handler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

settings = get_settings()

# Initialize Sentry if configured
if settings.sentry_dsn:
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
        from sentry_sdk.integrations.logging import LoggingIntegration

        sentry_logging = LoggingIntegration(
            level=logging.INFO,
            event_level=logging.ERROR
        )

        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            environment=settings.sentry_environment,
            traces_sample_rate=settings.sentry_traces_sample_rate,
            integrations=[
                FastApiIntegration(transaction_style="endpoint"),
                SqlalchemyIntegration(),
                sentry_logging,
            ],
            send_default_pii=False,
        )
        logger.info(f"Sentry initialized for environment: {settings.sentry_environment}")
    except ImportError:
        logger.warning("sentry-sdk not installed, error tracking disabled")
    except Exception as e:
        logger.error(f"Failed to initialize Sentry: {e}")

# Background scheduler for periodic tasks
scheduler = BackgroundScheduler()


def scheduled_risk_calculation():
    """Scheduled task to recalculate risk scores."""
    logger.info("Running scheduled risk calculation...")
    db = SessionLocal()
    try:
        calculator = RiskCalculator(db)
        results = calculator.calculate_all()
        logger.info(f"Calculated risk scores for {len(results)} LGAs")
    except Exception as e:
        logger.error(f"Error in scheduled risk calculation: {e}")
    finally:
        db.close()


def auto_seed_if_empty():
    """Seed database with nationwide LGAs if empty."""
    import os
    from app.models import LGA
    from app.services.lga_loader import load_national_lgas
    db = SessionLocal()
    try:
        lga_count = db.query(LGA).count()
        if lga_count == 0:
            logger.info("Database is empty, loading nationwide LGAs...")
            geojson_path = os.path.join(
                os.path.dirname(__file__), "..", "data", "boundaries",
                "nigeria_lgas_774.geojson",
            )
            count = load_national_lgas(db, geojson_path)
            logger.info(f"Loaded {count} nationwide LGAs")

            if settings.seed_demo:
                logger.info("SEED_DEMO=true — seeding synthetic scenario")
                from app.seed_database import (
                    seed_demo_scenario, calculate_initial_risks, seed_demo_alerts,
                )
                seed_demo_scenario()
                calculate_initial_risks()
                seed_demo_alerts()
        else:
            logger.info(f"Database already has {lga_count} LGAs, skipping seed")
    except Exception as e:
        logger.error(f"Auto-seed failed: {e}")
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown events."""
    # Startup
    logger.info("Starting Cholera Surveillance System...")

    # Initialize database tables (for development - use Alembic in production)
    init_db()
    logger.info("Database initialized")

    # Auto-seed if database is empty
    auto_seed_if_empty()

    # Start scheduler for periodic tasks
    # Run risk calculation daily at 6 AM
    scheduler.add_job(
        scheduled_risk_calculation,
        'cron',
        hour=6,
        minute=0,
        id='daily_risk_calculation'
    )
    scheduler.start()
    logger.info("Background scheduler started")

    yield

    # Shutdown
    scheduler.shutdown()
    logger.info("Scheduler stopped")


# Create FastAPI app
app = FastAPI(
    title="Cholera Environmental Surveillance System",
    description="""
    Integrated surveillance system for monitoring cholera risk in Cross River State, Nigeria.

    Features:
    - Real-time risk scoring based on satellite and epidemiological data
    - Interactive map visualization with LGA-level risk indicators
    - Integration with Google Earth Engine and NASA GPM for environmental data
    - Data upload and management capabilities
    - Alert system for early warning notifications
    """,
    version="1.0.0",
    lifespan=lifespan
)

# Set up rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

# Set up global exception handlers
setup_exception_handlers(app)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_origin_regex=r"https://flooding-cholera.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(lgas_router)
app.include_router(analytics_router)
app.include_router(upload_router)
app.include_router(satellite_router)
app.include_router(alerts_router)
app.include_router(facilities_router)
app.include_router(agent_router)
app.include_router(admin_data_router)


@app.get("/")
def root():
    """Root endpoint with API information."""
    return {
        "name": "Cholera Environmental Surveillance System",
        "version": "1.0.0",
        "status": "operational",
        "region": "Cross River State, Nigeria",
        "endpoints": {
            "lgas": "/api/lgas",
            "analytics": "/api/analytics",
            "upload": "/api/upload",
            "satellite": "/api/satellite",
            "alerts": "/api/alerts",
            "docs": "/docs"
        }
    }


@app.get("/health")
def health_check():
    """Health check endpoint."""
    from app.models import LGA
    db = SessionLocal()
    try:
        lga_count = db.query(LGA).count()
    finally:
        db.close()
    return {
        "status": "healthy",
        "database": "connected",
        "scheduler": "running" if scheduler.running else "stopped",
        "lga_count": lga_count
    }


@app.post("/api/seed")
def trigger_seed():
    """Manually trigger database seeding (for debugging)."""
    from app.models import LGA
    db = SessionLocal()
    try:
        lga_count = db.query(LGA).count()
        if lga_count > 0:
            return {"status": "skipped", "message": f"Database already has {lga_count} LGAs"}
        
        from app.seed_database import seed_lgas, seed_demo_scenario, calculate_initial_risks, seed_demo_alerts
        seed_lgas()
        seed_demo_scenario()
        calculate_initial_risks()
        seed_demo_alerts()
        
        new_count = db.query(LGA).count()
        return {"status": "success", "message": f"Seeded {new_count} LGAs"}
    except Exception as e:
        logger.error(f"Manual seed failed: {e}")
        import traceback
        return {"status": "error", "message": str(e), "traceback": traceback.format_exc()}
    finally:
        db.close()


@app.get("/api/risk-scores")
@limiter.limit("60/minute")
def get_current_risk_scores(request: Request):
    """Get current risk levels for all LGAs (convenience endpoint)."""
    from sqlalchemy import func
    from app.models import RiskScore, LGA

    db = SessionLocal()
    try:
        # Get latest risk scores for each LGA
        subquery = (
            db.query(
                RiskScore.lga_id,
                func.max(RiskScore.score_date).label("max_date")
            )
            .group_by(RiskScore.lga_id)
            .subquery()
        )

        scores = (
            db.query(RiskScore, LGA.name)
            .join(LGA)
            .join(
                subquery,
                (RiskScore.lga_id == subquery.c.lga_id) &
                (RiskScore.score_date == subquery.c.max_date)
            )
            .all()
        )

        return {
            "count": len(scores),
            "scores": [
                {
                    "lga_id": rs.lga_id,
                    "lga_name": name,
                    "score": rs.score,
                    "level": rs.level,
                    "score_date": rs.score_date.isoformat(),
                    "recent_cases": rs.recent_cases,
                    "recent_deaths": rs.recent_deaths
                }
                for rs, name in scores
            ]
        }
    finally:
        db.close()


@app.post("/api/risk-scores/calculate")
@limiter.limit("5/minute")
def trigger_risk_calculation(request: Request):
    """Trigger immediate risk recalculation for all LGAs."""
    from app.exceptions import APIError

    db = SessionLocal()
    try:
        calculator = RiskCalculator(db)
        results = calculator.calculate_all()
        return {
            "success": True,
            "message": f"Calculated risk scores for {len(results)} LGAs",
            "results": results
        }
    except Exception as e:
        logger.error(f"Error calculating risks: {e}")
        raise APIError(
            message="Failed to calculate risk scores",
            error_code="CALCULATION_ERROR",
            details={"error": str(e)}
        )
    finally:
        db.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
