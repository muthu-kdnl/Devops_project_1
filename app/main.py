import os
from fastapi import FastAPI, status
from fastapi.responses import JSONResponse

app = FastAPI(
    title="Core Ops API",
    version="1.0.0",
    docs_url=None,  # Disabled in production to avoid endpoint discovery
    redoc_url=None
)

APP_ENV = os.getenv("APP_ENV", "production")


@app.get("/healthz", status_code=status.HTTP_200_OK)
def healthcheck():
    return JSONResponse(
        content={
            "status": "healthy",
            "environment": APP_ENV
        }
    )


@app.get("/api/v1/info", status_code=status.HTTP_200_OK)
def info():
    return JSONResponse(
        content={
            "service": "core-ops-service",
            "runtime": "python-uvicorn",
            "containerized": True
        }
    )