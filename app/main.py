import uvicorn
from fastapi import FastAPI

from app.routers import auth, flashcards, groups

app = FastAPI(title="SmartCards Backend")

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(groups.router, prefix="/groups", tags=["groups"])
app.include_router(flashcards.router, prefix="/flashcards", tags=["flashcards"])

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
