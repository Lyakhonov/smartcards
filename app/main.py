import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import auth, flashcards, groups, admin
from app.services.init_admin import create_admin_if_not_exists
from app.services.storage import storage


# --- LIFESPAN FUNCTION (НОВЫЙ СПОСОБ) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Управляет жизненным циклом приложения.
    Код до 'yield' выполняется при старте, после 'yield' — при остановке.
    """
    # ensure admin exists
    await create_admin_if_not_exists()
    # ensure storage bucket exists
    try:
        storage.ensure_bucket()
    except Exception:
        # don't fail the startup for transient storage problems
        pass
    yield


app = FastAPI(
    title="SmartCards Backend", lifespan=lifespan  # ВАЖНО: передаем функцию lifespan
)


origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(groups.router, prefix="/groups", tags=["groups"])
app.include_router(flashcards.router, prefix="/flashcards", tags=["flashcards"])
app.include_router(admin.router, prefix="/admin", tags=["admin"])


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
