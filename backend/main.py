import os
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import engine, Base
from routers import auth, bills, categories, fitness, stats, settings, data

load_dotenv()

Base.metadata.create_all(bind=engine)

app = FastAPI(title="抱布记 API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(bills.router)
app.include_router(categories.router)
app.include_router(fitness.router)
app.include_router(stats.router)
app.include_router(settings.router)
app.include_router(data.router)


@app.get("/api/health")
def health():
    return {"status": "ok", "app": "抱布记"}


if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8089"))
    uvicorn.run("main:app", host=host, port=port, reload=True)
