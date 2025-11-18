# app/main.py
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from prometheus_fastapi_instrumentator import Instrumentator

from app.core.config import settings
from app.core.manager import manager
from app.core.middleware import register_middleware
from app.db.session import create_tables
from app.api.routers import (
    auth,
    users,
    posts,
    comments,
    likes,
    channels,
    communities,
    complaints,
    notifications,
    admin,
    messages,
    student_portal,
    institutions,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Lifespan manager for startup and shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    # On startup
    logger.info("Starting up...")
    await create_tables()
    yield
    # On shutdown
    logger.info("Shutting down...")


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Backend for the LagTALK microblogging platform.",
    version="0.1.0",
    lifespan=lifespan,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)


# Prometheus Metrics Integration
Instrumentator().instrument(app).expose(app)


# CORS Middleware
register_middleware(app)





# Include API Routers
api_prefix = settings.API_V1_STR
app.include_router(auth.router, prefix=f"{api_prefix}/auth", tags=["Auth"])
app.include_router(admin.router, prefix=f"{api_prefix}/admin", tags=["Admin"])
app.include_router(users.router, prefix=f"{api_prefix}/users", tags=["Users"])
app.include_router(posts.router, prefix=f"{api_prefix}/posts", tags=["Posts & Reels"])
app.include_router(comments.router, prefix=f"{api_prefix}/posts/{{post_id}}/comments", tags=["Comments"])
app.include_router(likes.router, prefix=f"{api_prefix}/likes", tags=["Likes"])
app.include_router(channels.router, prefix=f"{api_prefix}/channels", tags=["Channels"])
app.include_router(communities.router, prefix=f"{api_prefix}/communities", tags=["Communities"])
app.include_router(complaints.router, prefix=f"{api_prefix}/complaints", tags=["Complaints"])
app.include_router(notifications.router, prefix=f"{api_prefix}/notifications", tags=["Notifications"])
app.include_router(messages.router, prefix=f"{api_prefix}/messages", tags=["Messages"])
app.include_router(student_portal.router, prefix=f"{api_prefix}/student-portal", tags=["Student Portal"])
app.include_router(institutions.router, prefix=f"{api_prefix}/institutions", tags=["Institutions"])



@app.get("/", tags=["Health Check"])
async def root():
    """Health check endpoint."""
    return {"message": "LagTALK API is running!"}

@app.websocket("/ws/notifications/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    # Here you would add authentication logic for the WebSocket connection
    # For simplicity, we are trusting the user_id from the path
    await manager.connect(websocket, user_id)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)





if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=10000, reload=True)

    # uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
