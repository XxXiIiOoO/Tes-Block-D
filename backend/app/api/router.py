from fastapi import APIRouter

from app.api.routes import admin, auth, automation, health, project_secrets, projects, runs, stats, tests


api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(projects.router)
api_router.include_router(project_secrets.router)
api_router.include_router(tests.router)
api_router.include_router(runs.router)
api_router.include_router(stats.router)
api_router.include_router(admin.router)
api_router.include_router(automation.router)
