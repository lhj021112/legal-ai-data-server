from fastapi import FastAPI

from api.case_api import router as case_router
from core.db import Base, engine
from models import case_model


app = FastAPI(title="AI-Based Legal Case Data Server")

Base.metadata.create_all(bind=engine)

app.include_router(case_router)


@app.get("/health")
def health_check():
    return {"status": "ok"}
