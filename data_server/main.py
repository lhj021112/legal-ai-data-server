from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.case_api import router as case_router
from core.config import settings
from core.db import Base, engine
from models import case_model


app = FastAPI(title="AI-Based Legal Case Data Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)

app.include_router(case_router)


@app.get("/health")
def health_check():
    return {"status": "ok"}
