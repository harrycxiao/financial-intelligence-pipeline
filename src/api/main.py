from fastapi import FastAPI

from src.api.store_routes import router as store_router
from src.api.query_routes import router as query_router


app = FastAPI(
    title="Financial Intelligence Pipeline API",
    version="0.1.0",
)

app.include_router(store_router)
app.include_router(query_router)


@app.get("/")
def root() -> dict:
    return {"message": "Financial Intelligence Pipeline API is running."}