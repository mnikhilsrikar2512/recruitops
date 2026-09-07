from fastapi import APIRouter

from app.api.v1 import (
    approvals,
    auth,
    candidates,
    clients,
    daily_updates,
    dashboards,
    files,
    interviews,
    locations,
    meetings,
    notifications,
    offers,
    permissions,
    pipeline,
    requisitions,
    roles,
    system,
    users,
    workflow_actions,
)

api_router = APIRouter()
api_router.include_router(system.router, tags=["system"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(permissions.router, prefix="/permissions", tags=["permissions"])
api_router.include_router(locations.router, prefix="/locations", tags=["locations"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(roles.router, prefix="/roles", tags=["roles"])
api_router.include_router(clients.router, prefix="/clients", tags=["clients"])
api_router.include_router(requisitions.router, prefix="/requisitions", tags=["requisitions"])
api_router.include_router(candidates.router, prefix="/candidates", tags=["candidates"])
api_router.include_router(pipeline.router, prefix="/pipeline", tags=["pipeline"])
api_router.include_router(interviews.router, prefix="/interviews", tags=["interviews"])
api_router.include_router(offers.router, prefix="/offers", tags=["offers"])
api_router.include_router(daily_updates.router, prefix="/daily-updates", tags=["daily-updates"])
api_router.include_router(meetings.router, prefix="/meetings", tags=["meetings"])
api_router.include_router(dashboards.router, prefix="/dashboards", tags=["dashboards"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["notifications"])
api_router.include_router(files.router, prefix="/files", tags=["files"])
api_router.include_router(workflow_actions.router, prefix="/workflow-actions", tags=["workflow-actions"])
api_router.include_router(approvals.router, prefix="/approvals", tags=["approvals"])
