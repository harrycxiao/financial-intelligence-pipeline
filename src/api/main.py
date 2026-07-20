# src/api/main.py

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI

from src.api.ai_routes import router as ai_router
from src.api.query_routes import router as query_router
from src.api.quant_routes import router as quant_router
from src.api.store_routes import router as store_router


app = FastAPI(
    title="Financial Intelligence Pipeline API",
    version="0.1.0",
)


app.include_router(store_router)
app.include_router(query_router)
app.include_router(quant_router)
app.include_router(ai_router)


@app.get("/")
def root() -> dict:
    return {
        "message": "Financial Intelligence Pipeline API is running.",
    }