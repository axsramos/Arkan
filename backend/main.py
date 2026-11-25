"""Aplicação HTTP local do Arkan."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from backend.routers import auth, members, content, settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Não abrir nem criar armazenamento durante a inicialização do serviço.
    yield


app = FastAPI(title="Arkan Node", version="1.0.0", lifespan=lifespan)
app.include_router(auth.router)
app.include_router(members.router)
app.include_router(content.router)
app.include_router(settings.router)

FRONTEND_DIR = Path(__file__).resolve().parents[1] / "frontend"
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.middleware("http")
async def require_local_origin_for_mutations(request: Request, call_next):
    """Recusa mudanças originadas fora da página local do aplicativo."""
    if request.method in {"POST", "PUT", "PATCH", "DELETE"} and request.url.path.startswith("/api/"):
        origin = request.headers.get("origin")
        expected = f"{request.url.scheme}://{request.headers.get('host', '')}"
        if origin != expected:
            return JSONResponse({"detail": "Origem local inválida."}, status_code=403)
    return await call_next(request)


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/favicon.ico")
def favicon():
    return RedirectResponse(url="/static/favicon.ico")

@app.get("/api/v1/health")
def health_check() -> dict[str, str]:
    return {"status": "ONLINE", "mode": "LOCAL"}
