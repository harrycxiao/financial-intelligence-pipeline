# src/api/main.py

from dotenv import load_dotenv

load_dotenv(override=True)

import os

openai_key = os.getenv("OPENAI_API_KEY")

print(
    "OPENAI_API_KEY loaded:",
    bool(openai_key),
    "prefix:",
    openai_key[:12] if openai_key else None,
    "suffix:",
    openai_key[-4:] if openai_key else None,
)

from fastapi.middleware.cors import CORSMiddleware

from fastapi import FastAPI

from src.api.ai_routes import router as ai_router
from src.api.query_routes import router as query_router
from src.api.quant_routes import router as quant_router
from src.api.store_routes import router as store_router


app = FastAPI(
    title="Financial Intelligence Pipeline API",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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