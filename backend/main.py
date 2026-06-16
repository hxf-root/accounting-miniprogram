import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import engine, Base
from routers import auth, bills, categories, fitness, stats, settings, data

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
    uvicorn.run("main:app", host="0.0.0.0", port=8089, reload=True)
