from fastapi import FastAPI, APIRouter
from fastapi_pagination import add_pagination
from starlette.middleware.cors import CORSMiddleware

from interfaces.api.endpoints import farm, zone, users, tree, \
    irrigation_task, sensor, water_source, water_switcher, auth, zone_sensors, sensor_record
from interfaces.api.helpers.permission import RBACMiddleware
from interfaces.api.helpers.tenant import TenantContextMiddleware

app = FastAPI(title="Tilthwave API", debug=False)

# CORS (Cross-Origin Resource Sharing) middleware
app.add_middleware(RBACMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust this according to your needs
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],  # Adjust this according to your needs
)
# Bind the caller's tenant (farm) from the JWT for per-farm object scoping.
# Added last -> outermost, so the ContextVar is set before any task boundary.
app.add_middleware(TenantContextMiddleware)
api_router = APIRouter()

# Include all routers that require authentication
api_router.include_router(users.router)
api_router.include_router(farm.router)
api_router.include_router(zone.router)
api_router.include_router(zone_sensors.router)
api_router.include_router(sensor_record.router)
api_router.include_router(sensor.router)
api_router.include_router(water_source.router)
api_router.include_router(water_switcher.router)
api_router.include_router(tree.router)
api_router.include_router(irrigation_task.router)

# Register the auth router without the authentication dependency
app.include_router(auth.router)

# Register the authenticated router with the main app
app.include_router(api_router)

add_pagination(app)  # add pagination to app
