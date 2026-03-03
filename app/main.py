from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from contextlib import asynccontextmanager
from database import init_db
from app.routers import api
from app.services.message_listener import message_listener


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()
    print("[Startup] Database initialized")

    # Start message listeners automatically
    try:
        await message_listener.start_all_listeners()
        print(f"[Startup] Message listeners started: {message_listener.get_active_listeners_count()} active")
    except Exception as e:
        print(f"[Startup] Error starting listeners: {e}")

    yield

    # Shutdown
    try:
        await message_listener.stop_all_listeners()
        print("[Shutdown] All message listeners stopped")
    except Exception as e:
        print(f"[Shutdown] Error stopping listeners: {e}")


app = FastAPI(
    title="IBotServe",
    description="Telegram Userbot Management Service",
    version="1.0.0",
    lifespan=lifespan
)

app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

app.include_router(api.router)


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})
