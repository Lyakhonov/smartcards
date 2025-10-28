import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()


@app.get("/", summary="Главный эндпоинт", tags=["Основные эндпоинты"])
def root():
    return "Hello world!!!"


if __name__ == "__main__":
    uvicorn.run("main:app", reload=True)
